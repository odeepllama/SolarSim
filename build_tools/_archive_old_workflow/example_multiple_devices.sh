#!/bin/bash
# Example: Building once and flashing multiple identical devices

set -e

echo "=================================================="
echo "Example 2: Build Once, Flash Multiple Devices"
echo "=================================================="
echo ""

# Step 1: Build
echo "Step 1: Building deployment package..."
python3 build_uf2.py ../SolarSimulator.py -o ../ProductionRun_v1.0

echo ""
echo "Deployment package created: ProductionRun_v1.0_deployment/"
echo ""

# Step 2: Test on one device
echo "Step 2: Test on one device first"
echo ""
echo "Connect your first RP2040:bit device:"
echo "  1. Hold BOOTSEL button"
echo "  2. Connect USB"
echo "  3. Release BOOTSEL"
echo ""
read -p "Press Enter when device is connected..."

./flash_tool.sh ../ProductionRun_v1.0_deployment

echo ""
echo "Test device flashed. Verify it works before continuing."
read -p "Press Enter when ready to flash remaining devices..."

# Step 3: Flash multiple
echo ""
echo "Step 3: Flashing multiple devices"
echo "Follow prompts to connect each device..."
./flash_tool.sh -m ../ProductionRun_v1.0_deployment

echo ""
echo "=================================================="
echo "All Devices Flashed!"
echo "=================================================="
