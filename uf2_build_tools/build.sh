#!/bin/bash
# Builder wrapper that sets up venv and installs deps
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Ensuring requirements are installed..."
pip install -q littlefs-python

SRC_DIR=${1:-"../RP2040"}
OUTPUT_FILE=${2:-"../RP2040/SolarSimulator_Combined.uf2"}

echo "Building UF2 using source directory: $SRC_DIR"
python uf2_builder.py "$SRC_DIR" -o "$OUTPUT_FILE" --fs-size 1441792 --fs-offset 0x100A0000
