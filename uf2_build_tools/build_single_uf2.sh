#!/bin/bash
# Build a combined UF2 (MicroPython firmware + code files) for RP2040:bit
#
# Usage:
#   ./build_single_uf2.sh                  # Interactive — packs ../RP2040/ by default
#   ./build_single_uf2.sh ../RP2040/       # Pack all files in a directory
#   ./build_single_uf2.sh file1 file2      # Pack specific files

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Single UF2 Builder for RP2040:bit        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo

# Get script directory (handles spaces in path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RP2040_DIR="$(dirname "$SCRIPT_DIR")/RP2040"

# ── Ensure virtual environment and dependencies ──────────────────────────

VENV_DIR="$SCRIPT_DIR/.venv"

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${CYAN}Setting up Python virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to create virtual environment.${NC}"
            exit 1
        fi
    fi

    # Activate
    source "$VENV_DIR/bin/activate"

    # Check for littlefs-python
    if ! python3 -c "import littlefs" 2>/dev/null; then
        echo -e "${CYAN}Installing littlefs-python...${NC}"
        pip install --quiet littlefs-python
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install littlefs-python.${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ littlefs-python installed${NC}"
    fi
}

setup_venv

# ── Determine what to build ──────────────────────────────────────────────

if [ $# -gt 0 ]; then
    # Arguments provided — pass them directly to the builder
    echo -e "${GREEN}Building combined UF2...${NC}"
    python3 "$SCRIPT_DIR/uf2_builder.py" --verify "$@"
else
    # No arguments — interactive mode
    if [ -d "$RP2040_DIR" ]; then
        echo -e "${CYAN}RP2040 directory found: ${RP2040_DIR}${NC}"
        echo
        echo -e "${GREEN}Files to pack:${NC}"

        # List non-UF2 files in RP2040/
        FILE_COUNT=0
        for file in "$RP2040_DIR"/*; do
            [ -f "$file" ] || continue
            BASENAME=$(basename "$file")
            EXT="${BASENAME##*.}"
            # Skip .uf2 firmware files
            if [ "$EXT" = "uf2" ]; then
                continue
            fi
            if [[ "$OSTYPE" == "darwin"* ]]; then
                SIZE=$(stat -f%z "$file" | awk '{printf "%.1fK", $1/1024}')
            else
                SIZE=$(stat -c%s "$file" | awk '{printf "%.1fK", $1/1024}')
            fi
            printf "  ${CYAN}•${NC} %-35s (%s)\n" "$BASENAME" "$SIZE"
            FILE_COUNT=$((FILE_COUNT + 1))
        done

        if [ $FILE_COUNT -eq 0 ]; then
            echo -e "  ${YELLOW}No files found (excluding .uf2 firmware)${NC}"
            exit 1
        fi

        echo
        read -p "Build UF2 with these files? (Y/n): " CONFIRM
        echo

        if [ "$CONFIRM" = "n" ] || [ "$CONFIRM" = "N" ]; then
            echo "Cancelled."
            exit 0
        fi

        echo -e "${GREEN}Building combined UF2...${NC}"
        python3 "$SCRIPT_DIR/uf2_builder.py" --verify "$RP2040_DIR"
    else
        echo -e "${YELLOW}RP2040 directory not found at: ${RP2040_DIR}${NC}"
        echo
        echo -e "${YELLOW}Usage:${NC}"
        echo "  ./build_single_uf2.sh <directory>       # Pack all files in directory"
        echo "  ./build_single_uf2.sh <file1> <file2>   # Pack specific files"
        echo
        exit 1
    fi
fi

# ── Result ────────────────────────────────────────────────────────────────

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            BUILD SUCCESS!                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}To flash your RP2040:bit devices:${NC}"
    echo "1. Hold BOOTSEL button while connecting USB"
    echo "2. Drag and drop the .uf2 file onto RPI-RP2 drive"
    echo "3. Device reboots and runs your code!"
    echo
else
    echo
    echo -e "${RED}Build failed. Check error messages above.${NC}"
    exit 1
fi
