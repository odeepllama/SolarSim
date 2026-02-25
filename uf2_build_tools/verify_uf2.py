#!/usr/bin/env python3
import struct
import sys

# Verify a UF2 file
def verify(filepath):
    valid_blocks = 0
    with open(filepath, 'rb') as f:
        while True:
            block = f.read(512)
            if not block or len(block) < 512:
                break
            
            magic0, magic1, flags, target_addr, payload_size, block_no, num_blocks, family_id = struct.unpack('<IIIIIIII', block[:32])
            magic_end, = struct.unpack('<I', block[508:])
            
            if magic0 != 0x0A324655 or magic1 != 0x9E5D5157 or magic_end != 0x0AB16F30:
                print(f"Bad magic at block {valid_blocks}: {hex(magic0)}, {hex(magic1)}, {hex(magic_end)}")
                break
                
            valid_blocks += 1
            if valid_blocks == 1:
                print(f"First block target_addr: {hex(target_addr)}, num_blocks: {num_blocks}")

    print(f"Verified {valid_blocks} blocks. Total size {valid_blocks*512} bytes.")
    
if __name__ == '__main__':
    verify(sys.argv[1])
