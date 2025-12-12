#!/bin/bash
# Automated flashing tool for RP2040:bit devices
# This script automates the process of flashing multiple devices

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR=""
DEVICE_PORT=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

detect_port() {
    # Try to auto-detect the RP2040 device port
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -n 1)
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        PORT=$(ls /dev/ttyACM* 2>/dev/null | head -n 1)
    else
        # Assume Windows Git Bash or similar
        PORT=$(ls /dev/ttyS* 2>/dev/null | head -n 1)
    fi
    
    if [ -z "$PORT" ]; then
        return 1
    fi
    
    echo "$PORT"
    return 0
}

wait_for_bootloader() {
    print_info "Waiting for device in bootloader mode (RPI-RP2 drive)..."
    print_info "Please:"
    print_info "  1. Hold down the BOOTSEL button on your RP2040:bit"
    print_info "  2. Connect USB cable (while holding BOOTSEL)"
    print_info "  3. Release BOOTSEL"
    echo ""
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        MOUNT_POINT="/Volumes/RPI-RP2"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        MOUNT_POINT="/media/$USER/RPI-RP2"
        if [ ! -d "$MOUNT_POINT" ]; then
            MOUNT_POINT="/media/RPI-RP2"
        fi
    else
        # Windows - check multiple possible drive letters
        MOUNT_POINT=""
        for drive in D E F G H I J K L M N O P Q R S T U V W X Y Z; do
            if [ -d "/${drive}/RPI-RP2" ] || [ -d "/${drive}:" ]; then
                MOUNT_POINT="/${drive}:"
                break
            fi
        done
    fi
    
    # Wait for mount point
    for i in {1..60}; do
        if [ -d "$MOUNT_POINT" ]; then
            print_success "Device detected at: $MOUNT_POINT"
            echo "$MOUNT_POINT"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo ""
    print_error "Timeout waiting for bootloader"
    return 1
}

flash_firmware() {
    local firmware_file="$1"
    local mount_point="$2"
    
    print_info "Copying firmware to device..."
    cp "$firmware_file" "$mount_point/"
    
    print_success "Firmware copied. Device will reboot automatically..."
    
    # Wait for device to reboot and remount
    sleep 3
}

upload_code() {
    local code_file="$1"
    local port="$2"
    
    print_info "Uploading code to device via $port..."
    
    # Try mpremote first, fallback to ampy
    if command -v mpremote &> /dev/null; then
        mpremote connect "$port" fs cp "$code_file" :main.py
        print_success "Code uploaded using mpremote"
    elif command -v ampy &> /dev/null; then
        ampy --port "$port" put "$code_file" /main.py
        print_success "Code uploaded using ampy"
    else
        print_error "Neither mpremote nor ampy found!"
        print_info "Install with: pip install mpremote adafruit-ampy"
        return 1
    fi
    
    return 0
}

reset_device() {
    local port="$1"
    
    print_info "Resetting device..."
    
    if command -v mpremote &> /dev/null; then
        mpremote connect "$port" reset
    else
        print_info "Please press the reset button on your device"
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [DEPLOYMENT_DIR]

Automated flashing tool for RP2040:bit devices.

OPTIONS:
    -h, --help          Show this help message
    -p, --port PORT     Specify device port (auto-detect if not provided)
    -f, --firmware-only Flash firmware only, skip code upload
    -c, --code-only     Upload code only, skip firmware
    -m, --multiple      Flash multiple devices (interactive)

EXAMPLES:
    # Build and flash in one go
    python build_uf2.py && $0 SolarSimulator_deployment

    # Flash with auto-detection
    $0 SolarSimulator_deployment

    # Flash multiple devices
    $0 -m SolarSimulator_deployment

    # Update code only (no firmware reflash)
    $0 -c SolarSimulator_deployment

EOF
}

flash_device() {
    local deployment_dir="$1"
    local firmware_only="${2:-false}"
    local code_only="${3:-false}"
    
    # Find firmware and code files
    local firmware_file=$(find "$deployment_dir" -name "*firmware.uf2" -o -name "1_*.uf2" | head -n 1)
    local code_file=$(find "$deployment_dir" -name "*_code.py" -o -name "2_*.py" | head -n 1)
    
    if [ -z "$firmware_file" ]; then
        print_error "Firmware file not found in $deployment_dir"
        return 1
    fi
    
    if [ -z "$code_file" ]; then
        print_error "Code file not found in $deployment_dir"
        return 1
    fi
    
    print_info "Firmware: $(basename "$firmware_file")"
    print_info "Code: $(basename "$code_file")"
    echo ""
    
    # Step 1: Flash firmware (unless code-only mode)
    if [ "$code_only" = false ]; then
        local mount_point=$(wait_for_bootloader)
        if [ $? -ne 0 ]; then
            return 1
        fi
        
        flash_firmware "$firmware_file" "$mount_point"
        
        # Wait for device to reboot and become available
        print_info "Waiting for device to reboot..."
        sleep 5
    fi
    
    # Step 2: Upload code (unless firmware-only mode)
    if [ "$firmware_only" = false ]; then
        # Detect port
        local port=$(detect_port)
        if [ -z "$port" ]; then
            print_error "Could not detect device port"
            print_info "Please specify port with -p option"
            return 1
        fi
        
        print_info "Detected port: $port"
        
        upload_code "$code_file" "$port"
        reset_device "$port"
    fi
    
    print_success "Device flashed successfully!"
    return 0
}

main() {
    local firmware_only=false
    local code_only=false
    local multiple=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -p|--port)
                DEVICE_PORT="$2"
                shift 2
                ;;
            -f|--firmware-only)
                firmware_only=true
                shift
                ;;
            -c|--code-only)
                code_only=true
                shift
                ;;
            -m|--multiple)
                multiple=true
                shift
                ;;
            *)
                DEPLOYMENT_DIR="$1"
                shift
                ;;
        esac
    done
    
    # Check if deployment directory specified
    if [ -z "$DEPLOYMENT_DIR" ]; then
        # Try to find a deployment directory in parent directory
        DEPLOYMENT_DIR=$(find "$SCRIPT_DIR/.." -maxdepth 1 -type d -name "*_deployment" | head -n 1)
        
        if [ -z "$DEPLOYMENT_DIR" ]; then
            print_error "No deployment directory found"
            print_info "Run: python3 build_uf2.py first"
            show_usage
            exit 1
        fi
        
        print_info "Using deployment directory: $DEPLOYMENT_DIR"
    fi
    
    # Validate deployment directory
    if [ ! -d "$DEPLOYMENT_DIR" ]; then
        print_error "Deployment directory not found: $DEPLOYMENT_DIR"
        exit 1
    fi
    
    print_header "RP2040:bit Flash Tool"
    
    # Flash device(s)
    if [ "$multiple" = true ]; then
        print_info "Multiple device flashing mode"
        device_count=0
        
        while true; do
            device_count=$((device_count + 1))
            print_header "Flashing Device #$device_count"
            
            if ! flash_device "$DEPLOYMENT_DIR" "$firmware_only" "$code_only"; then
                print_error "Failed to flash device #$device_count"
                read -p "Continue with next device? (y/n) " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    break
                fi
            fi
            
            echo ""
            read -p "Flash another device? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        done
        
        print_success "Flashed $device_count device(s)"
    else
        flash_device "$DEPLOYMENT_DIR" "$firmware_only" "$code_only"
    fi
}

main "$@"
