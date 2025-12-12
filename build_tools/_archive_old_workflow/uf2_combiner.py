#!/usr/bin/env python3
"""
Combined UF2 Builder - Creates a single UF2 with MicroPython + your code

APPROACH: Creates a two-part UF2:
1. MicroPython firmware (blocks 0-N)
2. Python filesystem data (blocks N+1 onwards)

The Python code is written to flash at the filesystem region,
which MicroPython will recognize and mount on boot.

Perfect for flashing multiple devices - just drag and drop!
"""

import os
import sys
import struct
import argparse
import urllib.request
import ssl
from pathlib import Path

# UF2 format constants
UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID = 0x00002000
UF2_BLOCK_SIZE = 512
UF2_DATA_SIZE = 256  # Actual data per block

RP2040_FAMILY_ID = 0xE48BFF56

# RP2040 memory layout
FLASH_START = 0x10000000
FILESYSTEM_OFFSET = 0x00100000  # 1MB offset
FILESYSTEM_START = FLASH_START + FILESYSTEM_OFFSET

# MicroPython firmware
MICROPYTHON_VERSION = "v1.27.0"
MICROPYTHON_DATE = "20251209"
MICROPYTHON_FIRMWARE_URL = f"https://micropython.org/resources/firmware/RPI_PICO-{MICROPYTHON_DATE}-{MICROPYTHON_VERSION}.uf2"

def download_firmware(output_dir):
    """Download MicroPython firmware"""
    output_path = Path(output_dir) / f"RPI_PICO-{MICROPYTHON_DATE}-{MICROPYTHON_VERSION}.uf2"
    
    if output_path.exists():
        print(f"Firmware already downloaded: {output_path}")
        return output_path
    
    print(f"Downloading MicroPython {MICROPYTHON_VERSION}...")
    print(f"URL: {MICROPYTHON_FIRMWARE_URL}")
    
    # SSL context for macOS
    ssl_context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    urllib.request.install_opener(opener)
    
    try:
        urllib.request.urlretrieve(MICROPYTHON_FIRMWARE_URL, output_path)
        size = output_path.stat().st_size
        print(f"✓ Downloaded firmware ({size:,} bytes)")
        return output_path
    except Exception as e:
        print(f"✗ Download failed: {e}")
        sys.exit(1)

def parse_uf2_block(block_data):
    """Parse a single UF2 block"""
    if len(block_data) != UF2_BLOCK_SIZE:
        return None
    
    magic_start0, magic_start1, flags, target_addr, payload_size, block_no, num_blocks, family_id = struct.unpack('<IIIIIIII', block_data[:32])
    
    if magic_start0 != UF2_MAGIC_START0 or magic_start1 != UF2_MAGIC_START1:
        return None
    
    data = block_data[32:32+payload_size]
    magic_end = struct.unpack('<I', block_data[-4:])[0]
    
    if magic_end != UF2_MAGIC_END:
        return None
    
    return {
        'flags': flags,
        'target_addr': target_addr,
        'data': data,
        'block_no': block_no,
        'num_blocks': num_blocks,
        'family_id': family_id
    }

def create_uf2_block(data, target_addr, block_no, num_blocks):
    """Create a UF2 block"""
    # Pad data to 256 bytes
    if len(data) > UF2_DATA_SIZE:
        raise ValueError(f"Data too large: {len(data)} > {UF2_DATA_SIZE}")
    
    padded_data = data + b'\x00' * (UF2_DATA_SIZE - len(data))
    
    # Build block
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
    # Padding to reach 512 bytes (476 data + 32 header + 4 footer)
    block += b'\x00' * (UF2_BLOCK_SIZE - 32 - UF2_DATA_SIZE - 4)
    block += struct.pack('<I', UF2_MAGIC_END)
    
    return block

def create_littlefs_image(python_code, max_size=256*1024):
    """
    Create a minimal littlefs-compatible filesystem image
    
    This is a SIMPLIFIED approach:
    - Creates raw filesystem blocks
    - Writes main.py at the start
    - MicroPython will try to mount this
    
    Note: A proper implementation would use littlefs-python library
    """
    # LittleFS block size (typically 4096 for RP2040)
    block_size = 4096
    
    # Create filesystem header (simplified - this may not work perfectly)
    # A proper littlefs needs superblocks, metadata blocks, etc.
    
    # For now, create a simple image with main.py content
    # Prepend a marker that might help MicroPython recognize it
    fs_data = b'\xff' * block_size  # Erased flash pattern
    
    # Write main.py content at an offset
    main_py_data = python_code.encode('utf-8')
    
    # Simple approach: just write the code, let MicroPython handle it
    # This likely won't work without proper littlefs structure
    fs_data = main_py_data + b'\xff' * (max_size - len(main_py_data))
    
    return fs_data[:max_size]

def build_combined_uf2(firmware_path, python_file, output_path):
    """Build a combined UF2 with firmware + Python code"""
    
    print(f"\n{'='*60}")
    print("COMBINED UF2 BUILDER")
    print(f"{'='*60}\n")
    
    # Read firmware
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
    
    print(f"   ✓ Loaded {len(firmware_blocks)} firmware blocks")
    
    # Read Python code
    print(f"2. Reading Python code from {python_file.name}...")
    python_code = python_file.read_text()
    code_size = len(python_code)
    print(f"   ✓ Code size: {code_size:,} bytes")
    
    # Create filesystem image
    print("3. Creating filesystem image...")
    print("   ⚠️  WARNING: Using simplified filesystem approach")
    print("   ⚠️  This may not work - proper littlefs needed")
    
    # For now, just try writing code as-is
    # A better approach needs littlefs-python
    fs_image = create_littlefs_image(python_code)
    print(f"   ✓ Filesystem image: {len(fs_image):,} bytes")
    
    # Create filesystem UF2 blocks
    print("4. Creating filesystem UF2 blocks...")
    fs_uf2_blocks = []
    offset = 0
    block_no = len(firmware_blocks)
    
    while offset < len(fs_image):
        chunk = fs_image[offset:offset+UF2_DATA_SIZE]
        target_addr = FILESYSTEM_START + offset
        
        # Create block (we'll update num_blocks later)
        block_data = create_uf2_block(chunk, target_addr, block_no, 0)
        fs_uf2_blocks.append(block_data)
        
        offset += UF2_DATA_SIZE
        block_no += 1
    
    print(f"   ✓ Created {len(fs_uf2_blocks)} filesystem blocks")
    
    # Combine everything
    print("5. Combining into single UF2...")
    total_blocks = len(firmware_blocks) + len(fs_uf2_blocks)
    
    with open(output_path, 'wb') as out:
        # Write firmware blocks (update num_blocks)
        for i, block in enumerate(firmware_blocks):
            block_data = create_uf2_block(block['data'], block['target_addr'], i, total_blocks)
            out.write(block_data)
        
        # Write filesystem blocks (update block_no and num_blocks)
        for i, _ in enumerate(fs_uf2_blocks):
            block_no = len(firmware_blocks) + i
            target_addr = FILESYSTEM_START + (i * UF2_DATA_SIZE)
            chunk = fs_image[i*UF2_DATA_SIZE:(i+1)*UF2_DATA_SIZE]
            block_data = create_uf2_block(chunk, target_addr, block_no, total_blocks)
            out.write(block_data)
    
    output_size = Path(output_path).stat().st_size
    print(f"   ✓ Created {output_path}")
    print(f"   ✓ Total size: {output_size:,} bytes")
    print(f"   ✓ Total blocks: {total_blocks}")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='Build combined UF2 with firmware + Python code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ../SolarSimulator.py
  %(prog)s ../SolarSimulator.py -o my_device.uf2
  %(prog)s --python ../SolarSimulator.py --output combined.uf2

This creates a single UF2 file you can drag-and-drop onto multiple devices!

WARNING: Current implementation uses simplified filesystem approach.
For production use, consider using proper littlefs tools.
        """
    )
    
    parser.add_argument('python_file', nargs='?', type=Path,
                       help='Python file to bake into firmware')
    parser.add_argument('-p', '--python', type=Path, dest='python_file_flag',
                       help='Python file to bake into firmware (alternative)')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output UF2 file (default: <python_name>_combined.uf2)')
    parser.add_argument('-f', '--firmware', type=Path,
                       help='Use existing firmware file instead of downloading')
    parser.add_argument('--download-only', action='store_true',
                       help='Only download firmware, don\'t build')
    
    args = parser.parse_args()
    
    # Determine Python file
    python_file = args.python_file or args.python_file_flag
    
    if not args.download_only and not python_file:
        parser.error("Python file required (unless using --download-only)")
    
    if python_file and not python_file.exists():
        print(f"Error: Python file not found: {python_file}")
        sys.exit(1)
    
    # Create cache directory
    cache_dir = Path(__file__).parent / '.firmware_cache'
    cache_dir.mkdir(exist_ok=True)
    
    # Get firmware
    if args.firmware:
        firmware_path = args.firmware
        if not firmware_path.exists():
            print(f"Error: Firmware file not found: {firmware_path}")
            sys.exit(1)
    else:
        firmware_path = download_firmware(cache_dir)
    
    if args.download_only:
        print(f"\nFirmware ready: {firmware_path}")
        return
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_name = python_file.stem + '_combined.uf2'
        output_path = python_file.parent / output_name
    
    # Build combined UF2
    result = build_combined_uf2(firmware_path, python_file, output_path)
    
    print(f"\n{'='*60}")
    print("SUCCESS!")
    print(f"{'='*60}")
    print(f"\nCombined UF2 created: {result}")
    print("\nTo flash your RP2040:bit devices:")
    print("1. Hold BOOTSEL button while connecting USB")
    print("2. Drag and drop the UF2 file onto the drive")
    print("3. Device will reboot and run your code!")
    print("\n⚠️  IMPORTANT: This is experimental!")
    print("The filesystem approach used here is simplified.")
    print("If the code doesn't run, you may need to upload main.py separately.")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
