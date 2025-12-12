#!/bin/bash
# Example: Quick code update workflow (when you only changed Python code)

set -e

echo "============================================"
echo "Example 3: Quick Code Update"
echo "============================================"
echo ""
echo "Use this when you've only changed Python code"
echo "and don't need to reflash the firmware."
echo ""

# Step 1: Rebuild
echo "Step 1: Rebuilding with updated code..."
python3 build_uf2.py ../SolarSimulator.py

echo ""
echo "Step 2: Ready to update code!"
echo ""
echo "Connect your RP2040:bit device via USB"
echo "(No need to hold BOOTSEL for code-only update)"
echo ""
read -p "Press Enter when device is connected..."

# Step 2: Update code only (much faster)
./flash_tool.sh -c ../SolarSimulator_deployment

echo ""
echo "============================================"
echo "Code Updated!"
echo "============================================"
echo ""
echo "This was much faster because we skipped"
echo "firmware flashing!"
