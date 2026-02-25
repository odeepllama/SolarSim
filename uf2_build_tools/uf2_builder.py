#!/usr/bin/env python3
import struct
import os
import argparse

try:
    import littlefs
except ImportError:
    print("Error: littlefs-python is not installed. Please run 'pip install littlefs-python'")
    exit(1)

# Constants for UF2
UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
FAMILY_ID_RP2040 = 0xe48bff56
BLOCK_PAYLOAD_SIZE = 256

def pack_into_uf2(data, starting_addr, initial_block_no=0):
    blocks = []
    num_blocks = (len(data) + BLOCK_PAYLOAD_SIZE - 1) // BLOCK_PAYLOAD_SIZE
    for i in range(num_blocks):
        chunk = data[i * BLOCK_PAYLOAD_SIZE : (i + 1) * BLOCK_PAYLOAD_SIZE]
        if len(chunk) < BLOCK_PAYLOAD_SIZE:
            chunk += b'\x00' * (BLOCK_PAYLOAD_SIZE - len(chunk))
        
        flags = 0x00002000 # has family ID
        header = struct.pack('<IIIIIIII',
            UF2_MAGIC_START0,
            UF2_MAGIC_START1,
            flags,
            starting_addr + i * BLOCK_PAYLOAD_SIZE,
            BLOCK_PAYLOAD_SIZE,
            initial_block_no + i,
            initial_block_no + num_blocks,
            FAMILY_ID_RP2040
        )
        padded_chunk = chunk + b'\x00' * (476 - len(chunk))
        footer = struct.pack('<I', UF2_MAGIC_END)
        blocks.append(header + padded_chunk + footer)
    return blocks

def read_uf2_blocks(filepath):
    blocks = []
    with open(filepath, 'rb') as f:
        while True:
            block = f.read(512)
            if not block or len(block) < 512:
                break
            blocks.append(block)
    return blocks

def main():
    parser = argparse.ArgumentParser(description="Build combined MicroPython + App UF2 for RP2040")
    parser.add_argument('src_dir', help="Directory containing files to pack (.py, .mpy, etc)")
    parser.add_argument('--firmware', help="Base MicroPython UF2 file (auto-detected if present in src_dir)")
    parser.add_argument('-o', '--output', help="Output UF2 filepath", default="SolarSimulator_Combined.uf2")
    parser.add_argument('--fs-size', type=int, help="Size of LittleFS partition (default 1MB)", default=1024 * 1024)
    parser.add_argument('--fs-offset', type=lambda x: int(x, 0), help="Start address of FS in flash", default=0x10100000)
    args = parser.parse_args()

    # Find the firmware
    base_uf2 = args.firmware
    if not base_uf2:
        # Search in src_dir
        for f in os.listdir(args.src_dir):
            if f.endswith('.uf2') and f != os.path.basename(args.output):
                base_uf2 = os.path.join(args.src_dir, f)
                break
    
    if not base_uf2 or not os.path.exists(base_uf2):
        print(f"Error: Could not find base firmware UF2 to bundle with in {args.src_dir}.")
        return

    # Initialize LittleFS conforming to MicroPython RP2040 parameters
    print(f"Initializing LittleFS (size={args.fs_size} bytes, block_size=4096)...")
    fs = littlefs.LittleFS(
        block_size=4096,
        block_count=args.fs_size // 4096,
        name_max=32,
        read_size=32,
        prog_size=32,
        lookahead_size=32
    )

    # Walk directory and add files
    files_added = 0
    for root, _, files in os.walk(args.src_dir):
        for file in files:
            # Skip UF2 files or build scripts
            if file.endswith('.uf2') or file.startswith('.'):
                continue
            
            filepath = os.path.join(root, file)
            # determine FS path
            relpath = os.path.relpath(filepath, args.src_dir)
            # Change relative path separators to slash
            fspath = '/' + relpath.replace(os.sep, '/')
            
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # create directories if necessary
            dirname = os.path.dirname(fspath)
            if dirname and dirname != '/':
                try:
                    fs.makedirs(dirname, exist_ok=True)
                except FileExistsError:
                    pass
            
            with fs.open(fspath, 'wb') as f:
                f.write(content)
            
            files_added += 1
            print(f" ✓ Added {fspath} ({len(content)} bytes)")
    
    fs_data = fs.context.buffer
    print(f"Generated LittleFS image of {len(fs_data)} bytes containing {files_added} files.")

    # Read base firmware
    fw_blocks = read_uf2_blocks(base_uf2)
    print(f"Loaded {len(fw_blocks)} firmware blocks from {os.path.basename(base_uf2)}")

    # Pack fs into UF2 blocks
    fs_blocks = pack_into_uf2(fs_data, args.fs_offset, initial_block_no=len(fw_blocks))
    
    all_blocks = fw_blocks + fs_blocks
    total_blocks = len(all_blocks)
    
    final_data = bytearray()
    for i, block in enumerate(all_blocks):
        # We need to parse and write back block_no and total_blocks
        header = bytearray(block[:32])
        struct.pack_into('<I', header, 20, i)
        struct.pack_into('<I', header, 24, total_blocks)
        final_data.extend(header)
        final_data.extend(block[32:])

    out_path = args.output
    
    with open(out_path, 'wb') as f:
        f.write(final_data)
    
    print(f"Successfully generated {out_path} with {total_blocks} total blocks.")

if __name__ == '__main__':
    main()
