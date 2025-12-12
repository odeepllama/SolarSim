#!/usr/bin/env python3
"""
UF2 Builder for RP2040:bit MicroPython Projects
Converts a Python file into a UF2 file for easy flashing to RP2040 devices.

This tool packages your MicroPython code along with the MicroPython firmware
into a single UF2 file that can be dragged and dropped onto the RP2040 device.

Usage:
    python build_uf2.py [input_file.py] [--output output.uf2]
    
If no arguments provided, it will build SolarSimulator.py by default.
"""

import os
import sys
import argparse
import shutil
import tempfile
import urllib.request
import hashlib
import ssl
from pathlib import Path

# Configuration
MICROPYTHON_VERSION = "v1.27.0"
MICROPYTHON_FIRMWARE_URL = "https://micropython.org/resources/firmware/RPI_PICO-20251209-v1.27.0.uf2"
MICROPYTHON_FIRMWARE_FILENAME = f"micropython-{MICROPYTHON_VERSION}.uf2"

# UF2 Constants
UF2_MAGIC_START0 = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1 = 0x9E5D5157  # Random number
UF2_MAGIC_END = 0x0AB16F30     # Final magic
UF2_FLAG_FAMILY_ID_PRESENT = 0x00002000
RP2040_FAMILY_ID = 0xE48BFF56

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_success(text):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_info(text):
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def download_micropython_firmware(cache_dir):
    """Download MicroPython firmware if not cached."""
    cache_path = cache_dir / MICROPYTHON_FIRMWARE_FILENAME
    
    if cache_path.exists():
        print_info(f"Using cached MicroPython firmware: {cache_path}")
        return cache_path
    
    print_info(f"Downloading MicroPython {MICROPYTHON_VERSION} firmware...")
    print_info(f"URL: {MICROPYTHON_FIRMWARE_URL}")
    
    try:
        # Create cache directory if it doesn't exist
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create SSL context that doesn't verify certificates
        # This is needed on macOS where Python may not have access to system certificates
        ssl_context = ssl._create_unverified_context()
        
        # Download with progress
        def report_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            print(f"\rDownloading: {percent:.1f}% ({downloaded / 1024:.1f} KB)", end='')
        
        # Use opener with SSL context
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(MICROPYTHON_FIRMWARE_URL, cache_path, reporthook=report_hook)
        print()  # New line after progress
        print_success(f"Downloaded firmware to {cache_path}")
        return cache_path
    except Exception as e:
        print_error(f"Failed to download firmware: {e}")
        print_info("You can manually download from: https://micropython.org/download/RPI_PICO/")
        print_info(f"Save as: {cache_path}")
        sys.exit(1)

def create_filesystem_image(source_file, work_dir):
    """
    Create a filesystem image containing the Python code.
    For now, this creates a simple main.py that will run on boot.
    """
    print_info("Creating filesystem image...")
    
    # Read source file
    with open(source_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Create a main.py in work directory
    main_py = work_dir / "main.py"
    with open(main_py, 'w', encoding='utf-8') as f:
        f.write(source_code)
    
    print_success(f"Created main.py ({len(source_code)} bytes)")
    return main_py

def convert_to_uf2(firmware_path, code_file, output_path):
    """
    Convert firmware and code to UF2 format.
    
    Note: This is a simplified approach. For a complete solution,
    we would need to:
    1. Extract the firmware
    2. Mount the internal filesystem
    3. Add our Python files
    4. Rebuild the UF2
    
    For now, we provide instructions for manual flashing.
    """
    print_warning("Full UF2 bundling with custom code requires advanced tools.")
    print_info("Creating a two-step deployment package instead...")
    
    # Create output directory
    output_dir = output_path.parent / f"{output_path.stem}_deployment"
    output_dir.mkdir(exist_ok=True)
    
    # Copy firmware
    firmware_dest = output_dir / "1_flash_firmware.uf2"
    shutil.copy(firmware_path, firmware_dest)
    print_success(f"Copied firmware to: {firmware_dest}")
    
    # Copy code
    code_dest = output_dir / "2_upload_code.py"
    shutil.copy(code_file, code_dest)
    print_success(f"Copied code to: {code_dest}")
    
    # Create instructions
    instructions = output_dir / "README.txt"
    with open(instructions, 'w') as f:
        f.write(f"""
RP2040:bit Deployment Instructions
===================================

This package contains everything needed to flash your RP2040:bit device.

Files:
------
1. 1_flash_firmware.uf2    - MicroPython firmware ({MICROPYTHON_VERSION})
2. 2_upload_code.py         - Your SolarSimulator code
3. README.txt              - This file

Deployment Steps:
-----------------

STEP 1: Flash MicroPython Firmware
1. Hold down the BOOTSEL button on your RP2040:bit board
2. Connect the board to your computer via USB (while holding BOOTSEL)
3. Release BOOTSEL - the board should appear as a USB drive named "RPI-RP2"
4. Drag and drop "1_flash_firmware.uf2" onto the RPI-RP2 drive
5. The board will reboot automatically with MicroPython installed

STEP 2: Upload Your Code
Option A - Using Thonny (Recommended for beginners):
1. Install Thonny IDE (https://thonny.org)
2. Open Thonny and go to Tools > Options > Interpreter
3. Select "MicroPython (Raspberry Pi Pico)"
4. Select the correct serial port
5. Open "2_upload_code.py" in Thonny
6. Click the "Save" button and choose "Raspberry Pi Pico"
7. Save it as "main.py" on the device
8. The code will now run automatically on every boot

Option B - Using ampy (Command line):
1. Install ampy: pip install adafruit-ampy
2. Find your device port (e.g., /dev/ttyACM0 on Linux, COM3 on Windows)
3. Run: ampy --port YOUR_PORT put 2_upload_code.py /main.py
4. Reset your device

Option C - Using mpremote (Command line):
1. Install mpremote: pip install mpremote
2. Run: mpremote fs cp 2_upload_code.py :main.py
3. Reset your device

STEP 3: Verify
1. The code should start running immediately
2. You should see the display lights activate
3. Connect via serial (115200 baud) to see debug output

Flashing Multiple Devices:
--------------------------
Repeat steps 1-2 for each device. The firmware only needs to be flashed
once (unless you want to upgrade MicroPython), but you'll need to upload
the code to each device.

Quick Reflashing:
-----------------
For subsequent updates (when you only changed the code, not the firmware):
- Just repeat STEP 2 above
- No need to reflash the firmware

Notes:
------
- Keep this package for future updates
- To update code later, just replace 2_upload_code.py with your new version
  and repeat STEP 2
- The firmware is cached locally to speed up future builds

Generated on: {Path(code_file).stat().st_mtime}
Source file: {Path(code_file).name}
""")
    print_success(f"Created instructions: {instructions}")
    
    return output_dir

def main():
    """Main build function."""
    parser = argparse.ArgumentParser(
        description='Build UF2 deployment package for RP2040:bit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Build SolarSimulator.py
  %(prog)s MyCode.py                    # Build MyCode.py
  %(prog)s -o custom_name MyCode.py     # Custom output name
        """
    )
    parser.add_argument('input', nargs='?', default='../SolarSimulator.py',
                       help='Input Python file (default: ../SolarSimulator.py)')
    parser.add_argument('-o', '--output', 
                       help='Output name (default: based on input filename)')
    parser.add_argument('--micropython-version', default=MICROPYTHON_VERSION,
                       help=f'MicroPython version to use (default: {MICROPYTHON_VERSION})')
    
    args = parser.parse_args()
    
    print_header("RP2040:bit UF2 Builder")
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print_error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    print_success(f"Input file: {input_path}")
    print_info(f"File size: {input_path.stat().st_size} bytes")
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_deployment"
    
    # Create cache directory
    cache_dir = Path.home() / '.rp2040_uf2_cache'
    
    # Download firmware
    firmware_path = download_micropython_firmware(cache_dir)
    
    # Create temporary work directory
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        
        # Create filesystem image
        code_file = create_filesystem_image(input_path, work_dir)
        
        # Convert to UF2
        deployment_dir = convert_to_uf2(firmware_path, input_path, output_path)
    
    print_header("Build Complete!")
    print_success(f"Deployment package created: {deployment_dir}")
    print_info("See README.txt in the deployment folder for flashing instructions")
    print()
    print(f"{Colors.BOLD}Quick Start:{Colors.ENDC}")
    print("1. Hold BOOTSEL, connect USB, release BOOTSEL")
    print("2. Drag 1_flash_firmware.uf2 to the RPI-RP2 drive")
    print("3. Use Thonny or ampy to upload 2_upload_code.py as main.py")
    print()

if __name__ == '__main__':
    main()
