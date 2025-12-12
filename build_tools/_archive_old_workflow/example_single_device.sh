#!/bin/bash
# Example: Building and flashing SolarSimulator.py to a single device

set -e

echo "=========================================="
echo "Example 1: Build and Flash Single Device"
echo "=========================================="
echo ""

# Step 1: Build
echo "Step 1: Building deployment package..."
python3 build_uf2.py ../SolarSimulator.py

echo ""
echo "Step 2: Ready to flash!"
echo ""
echo "Now connect your RP2040:bit device:"
echo "  1. Hold BOOTSEL button"
echo "  2. Connect USB"
echo "  3. Release BOOTSEL"
echo ""
read -p "Press Enter when device is connected..."

# Step 2: Flash
./flash_tool.sh ../SolarSimulator_deployment

echo ""
echo "=========================================="
echo "Flashing Complete!"
echo "=========================================="
