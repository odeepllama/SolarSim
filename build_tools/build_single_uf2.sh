#!/bin/bash
# Simple wrapper script for building combined UF2

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Single UF2 Builder for RP2040:bit      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if Python file provided
if [ -z "$1" ]; then
    # Interactive mode - show available Python files
    PARENT_DIRNAME=$(basename "$PARENT_DIR")
    echo -e "${CYAN}Python files in ${PARENT_DIRNAME}/:${NC}"
    echo
    
    # Find all .py files in parent directory (using array properly for spaces)
    FILES=()
    while IFS= read -r -d '' file; do
        FILES+=("$file")
    done < <(find "$PARENT_DIR" -maxdepth 1 -name "*.py" -type f -print0 | sort -z)
    
    if [ ${#FILES[@]} -eq 0 ]; then
        echo -e "${YELLOW}No Python files found in parent directory.${NC}"
        echo
        echo -e "${YELLOW}Usage:${NC}"
        echo "  ./build_single_uf2.sh <python_file> [output_name.uf2]"
        echo
        exit 1
    fi
    
    # Display menu
    echo -e "${GREEN}Available Python files:${NC}"
    echo
    for i in "${!FILES[@]}"; do
        FILE="${FILES[$i]}"
        BASENAME=$(basename "$FILE")
        # Use stat for file size to handle spaces properly
        if [[ "$OSTYPE" == "darwin"* ]]; then
            SIZE=$(stat -f%z "$FILE" | awk '{printf "%.1fK", $1/1024}')
        else
            SIZE=$(stat -c%s "$FILE" | awk '{printf "%.1fK", $1/1024}')
        fi
        printf "  ${CYAN}%2d)${NC} %-40s (%s)\n" $((i+1)) "$BASENAME" "$SIZE"
    done
    echo
    echo -e "  ${CYAN} 0)${NC} Cancel"
    echo
    
    # Get user selection
    read -p "Select file to build (0-${#FILES[@]}): " SELECTION
    echo
    
    if [ -z "$SELECTION" ] || [ "$SELECTION" -eq 0 ]; then
        echo "Cancelled."
        exit 0
    fi
    
    if [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt ${#FILES[@]} ]; then
        echo -e "${YELLOW}Invalid selection.${NC}"
        exit 1
    fi
    
    PYTHON_FILE="${FILES[$((SELECTION-1))]}"
    OUTPUT_FILE=""
else
    PYTHON_FILE="$1"
    OUTPUT_FILE="$2"
fi

# Check if file exists
if [ ! -f "$PYTHON_FILE" ]; then
    echo -e "${YELLOW}Error:${NC} Python file not found: $PYTHON_FILE"
    exit 1
fi

# Build command
if [ -z "$OUTPUT_FILE" ]; then
    echo -e "${GREEN}Building combined UF2...${NC}"
    python3 "$SCRIPT_DIR/uf2_combiner_proper.py" "$PYTHON_FILE"
else
    echo -e "${GREEN}Building combined UF2: $OUTPUT_FILE${NC}"
    python3 "$SCRIPT_DIR/uf2_combiner_proper.py" "$PYTHON_FILE" -o "$OUTPUT_FILE"
fi

# Check if build succeeded
if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            BUILD SUCCESS!                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}To flash your RP2040:bit devices:${NC}"
    echo "1. Hold BOOTSEL button while connecting USB"
    echo "2. Drag and drop the .uf2 file onto RPI-RP2 drive"
    echo "3. Device reboots and runs your code!"
    echo
else
    echo
    echo -e "${YELLOW}Build failed. Check error messages above.${NC}"
    exit 1
fi
