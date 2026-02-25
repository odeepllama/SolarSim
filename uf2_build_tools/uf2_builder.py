#!/usr/bin/env python3
"""
Combined UF2 Builder with proper LittleFS support

Creates a single UF2 file containing:
- MicroPython firmware
- Your files (.mpy, .py, .txt, etc.) in a proper LittleFS filesystem

Perfect for flashing multiple devices — just drag and drop!

Usage:
  # Pack all non-firmware files from a directory:
  python3 uf2_builder.py ../RP2040/

  # Pack specific files:
  python3 uf2_builder.py main.mpy main_app.mpy

  # Specify firmware explicitly:
  python3 uf2_builder.py ../RP2040/ -f firmware.uf2
"""

import os
import sys
import struct
import argparse
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime

try:
    import littlefs
except ImportError:
    print("Error: littlefs-python not installed")
    print("Install with: pip install littlefs-python")
    print("Or run: ./build_single_uf2.sh (it will install automatically)")
    sys.exit(1)

# ─── UF2 format constants ────────────────────────────────────────────────────
UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END    = 0x0AB16F30
UF2_FLAG_FAMILY_ID = 0x00002000
UF2_BLOCK_SIZE   = 512
UF2_DATA_SIZE    = 256   # Actual data per UF2 block

RP2040_FAMILY_ID = 0xE48BFF56

# ─── RP2040 Memory Layout ────────────────────────────────────────────────────
FLASH_START       = 0x10000000
FILESYSTEM_OFFSET = 0x00100000   # 1MB offset (standard MicroPython RPI_PICO build)
FILESYSTEM_START  = FLASH_START + FILESYSTEM_OFFSET
FILESYSTEM_SIZE   = 256 * 1024   # 256KB for filesystem (256 × 4096-byte blocks)

# ─── LittleFS parameters (MUST match MicroPython v1.20+ on RP2040) ────────
LFS_BLOCK_SIZE    = 4096
LFS_NAME_MAX      = 32
LFS_READ_SIZE     = 32
LFS_PROG_SIZE     = 32
LFS_LOOKAHEAD_SIZE= 32

# ─── MicroPython firmware ─────────────────────────────────────────────────────
MICROPYTHON_VERSION = "v1.27.0"
MICROPYTHON_DATE    = "20251209"
MICROPYTHON_FIRMWARE_URL = (
    f"https://micropython.org/resources/firmware/"
    f"RPI_PICO-{MICROPYTHON_DATE}-{MICROPYTHON_VERSION}.uf2"
)


def download_firmware(output_dir):
    """Download MicroPython firmware if not already cached."""
    output_path = Path(output_dir) / f"RPI_PICO-{MICROPYTHON_DATE}-{MICROPYTHON_VERSION}.uf2"

    if output_path.exists():
        print(f"   Firmware already cached: {output_path.name}")
        return output_path

    print(f"   Downloading MicroPython {MICROPYTHON_VERSION}...")

    # SSL context for macOS
    ssl_context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    urllib.request.install_opener(opener)

    try:
        urllib.request.urlretrieve(MICROPYTHON_FIRMWARE_URL, output_path)
        size = output_path.stat().st_size
        print(f"   ✓ Downloaded firmware ({size:,} bytes)")
        return output_path
    except Exception as e:
        print(f"   ✗ Download failed: {e}")
        sys.exit(1)


def create_uf2_block(data, target_addr, block_no, num_blocks):
    """Create a single UF2 block."""
    if len(data) > UF2_DATA_SIZE:
        raise ValueError(f"Data too large: {len(data)} > {UF2_DATA_SIZE}")

    padded_data = data + b'\x00' * (UF2_DATA_SIZE - len(data))

    block = struct.pack('<IIIIIIII',
        UF2_MAGIC_START0,
        UF2_MAGIC_START1,
        UF2_FLAG_FAMILY_ID,
        target_addr,
        UF2_DATA_SIZE,
        block_no,
        num_blocks,
        RP2040_FAMILY_ID
    )
    block += padded_data
    block += b'\x00' * (UF2_BLOCK_SIZE - 32 - UF2_DATA_SIZE - 4)
    block += struct.pack('<I', UF2_MAGIC_END)

    return block


def parse_uf2_block(block_data):
    """Parse a single UF2 block, returns dict or None."""
    if len(block_data) != UF2_BLOCK_SIZE:
        return None

    (magic_start0, magic_start1, flags, target_addr,
     payload_size, block_no, num_blocks, family_id) = struct.unpack(
        '<IIIIIIII', block_data[:32]
    )

    if magic_start0 != UF2_MAGIC_START0 or magic_start1 != UF2_MAGIC_START1:
        return None

    data = block_data[32:32 + payload_size]

    return {
        'flags':       flags,
        'target_addr': target_addr,
        'data':        data,
        'block_no':    block_no,
        'num_blocks':  num_blocks,
        'family_id':   family_id,
    }


def create_littlefs_image(file_list, image_size=FILESYSTEM_SIZE):
    """
    Create a LittleFS filesystem image containing multiple files.

    Args:
        file_list: list of (device_name, file_bytes) tuples
                   e.g. [("main.mpy", b"..."), ("profile.txt", b"...")]
        image_size: total filesystem image size in bytes

    Returns:
        bytes: the raw filesystem image
    """
    block_count = image_size // LFS_BLOCK_SIZE

    print(f"   LittleFS config: block_size={LFS_BLOCK_SIZE}, blocks={block_count}, "
          f"name_max={LFS_NAME_MAX}")
    print(f"   read_size={LFS_READ_SIZE}, prog_size={LFS_PROG_SIZE}, "
          f"lookahead_size={LFS_LOOKAHEAD_SIZE}")

    # Create filesystem with parameters that EXACTLY match MicroPython's internal config
    fs = littlefs.LittleFS(
        block_size=LFS_BLOCK_SIZE,
        block_count=block_count,
        name_max=LFS_NAME_MAX,
        read_size=LFS_READ_SIZE,
        prog_size=LFS_PROG_SIZE,
        lookahead_size=LFS_LOOKAHEAD_SIZE,
    )

    # Write each file into the filesystem
    for device_name, file_bytes in file_list:
        # Validate filename length
        if len(device_name) > LFS_NAME_MAX:
            print(f"   ✗ ERROR: filename '{device_name}' exceeds {LFS_NAME_MAX} chars!")
            sys.exit(1)

        path = f"/{device_name}"
        with fs.open(path, 'wb') as f:
            f.write(file_bytes)
        print(f"   ✓ Added {device_name} ({len(file_bytes):,} bytes)")

    # Validate by reading back
    print("   Verifying filesystem contents...")
    for entry in fs.listdir("/"):
        info = fs.stat(f"/{entry}")
        print(f"     /{entry}  ({info.size:,} bytes)")

    return fs.context.buffer


def build_combined_uf2(firmware_path, file_list, output_path, fs_offset=FILESYSTEM_OFFSET,
                       fs_size=FILESYSTEM_SIZE):
    """Build a combined UF2 with firmware + LittleFS filesystem."""

    print(f"\n{'='*60}")
    print("COMBINED UF2 BUILDER (with LittleFS)")
    print(f"{'='*60}\n")

    # ── Step 1: Read firmware ─────────────────────────────────────────────
    print("1. Reading firmware...")
    firmware_blocks = []
    with open(firmware_path, 'rb') as f:
        while True:
            block_data = f.read(UF2_BLOCK_SIZE)
            if len(block_data) != UF2_BLOCK_SIZE:
                break
            block = parse_uf2_block(block_data)
            if block:
                firmware_blocks.append(block)

    print(f"   ✓ Loaded {len(firmware_blocks)} firmware blocks from {firmware_path.name}")

    # ── Step 2: Print file summary ────────────────────────────────────────
    print(f"2. Files to pack ({len(file_list)} files):")
    total_code_size = 0
    for name, data in file_list:
        print(f"   • {name} ({len(data):,} bytes)")
        total_code_size += len(data)
    print(f"   Total code: {total_code_size:,} bytes")

    if total_code_size > fs_size:
        print(f"   ✗ ERROR: Total code ({total_code_size:,}) exceeds filesystem size ({fs_size:,})!")
        sys.exit(1)

    # ── Step 3: Create LittleFS image ─────────────────────────────────────
    print("3. Creating LittleFS filesystem...")
    fs_image = create_littlefs_image(file_list, image_size=fs_size)
    print(f"   ✓ Filesystem image: {len(fs_image):,} bytes")

    # ── Step 4: Create filesystem UF2 blocks ──────────────────────────────
    print("4. Creating filesystem UF2 blocks...")
    fs_start = FLASH_START + fs_offset
    fs_uf2_blocks = []
    offset = 0

    while offset < len(fs_image):
        chunk = fs_image[offset:offset + UF2_DATA_SIZE]
        if len(chunk) < UF2_DATA_SIZE:
            chunk += b'\xff' * (UF2_DATA_SIZE - len(chunk))
        fs_uf2_blocks.append(chunk)
        offset += UF2_DATA_SIZE

    print(f"   ✓ Created {len(fs_uf2_blocks)} filesystem blocks "
          f"(@ 0x{fs_start:08X}–0x{fs_start + len(fs_image):08X})")

    # ── Step 5: Combine into single UF2 ──────────────────────────────────
    print("5. Combining into single UF2...")
    total_blocks = len(firmware_blocks) + len(fs_uf2_blocks)

    with open(output_path, 'wb') as out:
        # Write firmware blocks (re-numbered)
        for i, block in enumerate(firmware_blocks):
            block_data = create_uf2_block(
                block['data'], block['target_addr'], i, total_blocks
            )
            out.write(block_data)

        # Write filesystem blocks
        for i, chunk in enumerate(fs_uf2_blocks):
            block_no = len(firmware_blocks) + i
            target_addr = fs_start + (i * UF2_DATA_SIZE)
            block_data = create_uf2_block(chunk, target_addr, block_no, total_blocks)
            out.write(block_data)

    output_size = Path(output_path).stat().st_size
    print(f"   ✓ Created {output_path}")
    print(f"   ✓ Total size: {output_size:,} bytes ({output_size / 1024:.1f} KB)")
    print(f"   ✓ Total blocks: {total_blocks} "
          f"({len(firmware_blocks)} firmware + {len(fs_uf2_blocks)} filesystem)")

    return output_path


def verify_uf2(uf2_path):
    """Read back and validate a UF2 file."""
    print(f"\nVerifying {uf2_path.name}...")

    firmware_blocks = 0
    fs_blocks = 0
    total_blocks = 0
    expected_total = None

    with open(uf2_path, 'rb') as f:
        while True:
            block_data = f.read(UF2_BLOCK_SIZE)
            if len(block_data) != UF2_BLOCK_SIZE:
                break
            block = parse_uf2_block(block_data)
            if block is None:
                print(f"  ✗ Invalid block at position {total_blocks}")
                return False

            if expected_total is None:
                expected_total = block['num_blocks']

            if block['num_blocks'] != expected_total:
                print(f"  ✗ Inconsistent block count at block {total_blocks}")
                return False

            if block['block_no'] != total_blocks:
                print(f"  ✗ Block numbering gap at block {total_blocks}")
                return False

            if block['target_addr'] >= FILESYSTEM_START:
                fs_blocks += 1
            else:
                firmware_blocks += 1

            total_blocks += 1

    if total_blocks != expected_total:
        print(f"  ✗ Expected {expected_total} blocks, found {total_blocks}")
        return False

    print(f"  ✓ {total_blocks} blocks verified OK")
    print(f"    Firmware:   {firmware_blocks} blocks")
    print(f"    Filesystem: {fs_blocks} blocks")
    return True


def collect_files(paths, source_dir=None):
    """
    Collect files from paths argument.

    If a path is a directory, include all non-UF2 files from it.
    If a path is a file, include it directly.

    Returns: list of (device_filename, bytes) tuples
    """
    SKIP_EXTENSIONS = {'.uf2'}
    file_list = []
    seen_names = set()

    for p in paths:
        p = Path(p)
        if p.is_dir():
            # Pack all non-firmware files from directory
            for child in sorted(p.iterdir()):
                if child.is_file() and child.suffix.lower() not in SKIP_EXTENSIONS:
                    name = child.name
                    if name in seen_names:
                        print(f"  ⚠️  Duplicate filename '{name}', skipping {child}")
                        continue
                    seen_names.add(name)
                    file_list.append((name, child.read_bytes()))
        elif p.is_file():
            name = p.name
            if name in seen_names:
                print(f"  ⚠️  Duplicate filename '{name}', skipping {p}")
                continue
            seen_names.add(name)
            file_list.append((name, p.read_bytes()))
        else:
            print(f"  ✗ Not found: {p}")
            sys.exit(1)

    return file_list


def find_firmware_in_dir(directory):
    """Look for a MicroPython firmware .uf2 in the given directory."""
    directory = Path(directory)
    uf2_files = list(directory.glob("*.uf2"))
    # Filter to likely firmware files (not flash_nuke, not combined outputs)
    firmware_candidates = [f for f in uf2_files if 'nuke' not in f.name.lower()]

    if len(firmware_candidates) == 1:
        return firmware_candidates[0]
    elif len(firmware_candidates) > 1:
        # Prefer files with known naming pattern
        for f in firmware_candidates:
            if 'RPI_PICO' in f.name or 'PICO' in f.name:
                return f
        return firmware_candidates[0]
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Build combined UF2 with firmware + code files (using proper LittleFS)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s ../RP2040/                     # Pack all files from RP2040/ directory
  %(prog)s main.mpy main_app.mpy          # Pack specific files
  %(prog)s ../RP2040/ -o my_device.uf2    # Specify output name
  %(prog)s ../RP2040/ --verify            # Build and verify

This creates a single UF2 file you can drag-and-drop onto devices!
Your files will be in a proper LittleFS filesystem.
        """
    )

    parser.add_argument('paths', nargs='*', type=Path,
                       help='Files or directories to pack into the filesystem')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output UF2 file (default: auto-generated with timestamp)')
    parser.add_argument('-f', '--firmware', type=Path,
                       help='Firmware UF2 file (default: auto-detect or download)')
    parser.add_argument('--fs-offset', type=lambda x: int(x, 0), default=FILESYSTEM_OFFSET,
                       help=f'Filesystem offset in flash (default: 0x{FILESYSTEM_OFFSET:X})')
    parser.add_argument('--fs-size', type=lambda x: int(x, 0), default=FILESYSTEM_SIZE,
                       help=f'Filesystem size (default: {FILESYSTEM_SIZE // 1024}KB)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify the generated UF2 after building')
    parser.add_argument('--download-only', action='store_true',
                       help='Only download firmware, don\'t build')

    args = parser.parse_args()

    # Create cache directory
    cache_dir = Path(__file__).parent / '.firmware_cache'
    cache_dir.mkdir(exist_ok=True)

    # ── Download-only mode ────────────────────────────────────────────────
    if args.download_only:
        firmware_path = download_firmware(cache_dir)
        print(f"\nFirmware ready: {firmware_path}")
        return

    # ── Require paths ─────────────────────────────────────────────────────
    if not args.paths:
        parser.error("At least one file or directory required (unless using --download-only)")

    # ── Collect files to pack ─────────────────────────────────────────────
    file_list = collect_files(args.paths)

    if not file_list:
        print("✗ No files to pack!")
        sys.exit(1)

    # ── Find firmware ─────────────────────────────────────────────────────
    firmware_path = args.firmware

    if firmware_path is None:
        # Try to find firmware in provided directories
        for p in args.paths:
            if Path(p).is_dir():
                found = find_firmware_in_dir(p)
                if found:
                    firmware_path = found
                    print(f"Auto-detected firmware: {found.name}")
                    break

    if firmware_path is None:
        # Check the firmware cache
        cached = find_firmware_in_dir(cache_dir)
        if cached:
            firmware_path = cached
            print(f"Using cached firmware: {cached.name}")

    if firmware_path is None:
        # Download it
        firmware_path = download_firmware(cache_dir)

    if not firmware_path.exists():
        print(f"✗ Firmware not found: {firmware_path}")
        sys.exit(1)

    # ── Determine output path ─────────────────────────────────────────────
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_name = f"SolarSimulator_{timestamp}.uf2"
        # Put output in the first directory arg, or next to the first file
        first_path = Path(args.paths[0])
        if first_path.is_dir():
            output_path = first_path / output_name
        else:
            output_path = first_path.parent / output_name

    # ── Build! ────────────────────────────────────────────────────────────
    result = build_combined_uf2(
        firmware_path, file_list, output_path,
        fs_offset=args.fs_offset,
        fs_size=args.fs_size,
    )

    # ── Verify ────────────────────────────────────────────────────────────
    if args.verify:
        if not verify_uf2(Path(result)):
            sys.exit(1)

    # ── Done! ─────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUCCESS!")
    print(f"{'='*60}")
    print(f"\nCombined UF2: {result}")
    print("\nTo flash your RP2040:bit devices:")
    print("1. Hold BOOTSEL button while connecting USB")
    print("2. Drag and drop the UF2 file onto the RPI-RP2 drive")
    print("3. Device will reboot and run automatically!")
    print(f"\n✓ LittleFS filesystem (name_max={LFS_NAME_MAX}, "
          f"block_size={LFS_BLOCK_SIZE})")
    print(f"✓ {len(file_list)} file(s) packed")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
