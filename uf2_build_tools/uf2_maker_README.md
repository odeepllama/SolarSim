# SolarSimulator - RP2040:bit Project

Solar simulation system for phototropism experiments on RP2040:bit hardware.

## 🚀 Quick Start

**Build one UF2 file with firmware + your code baked in:**

```bash
cd build_tools
pip install littlefs-python  # First time only
./build_single_uf2.sh
```

Select your Python file from the menu, and it creates a combined UF2 ready to flash!

### Flash to Devices

1. Hold **BOOTSEL** button while connecting USB
2. Drag and drop the `_combined.uf2` file onto RPI-RP2 drive
3. Done! Device reboots and runs your code

**No IDE needed! No serial connection! Pure drag-and-drop!**

## 🎯 Usage

### Interactive Mode (Easiest)
```bash
cd build_tools
./build_single_uf2.sh
# Select file from menu
```

### Direct Mode (Fast)
```bash
cd build_tools
./build_single_uf2.sh ../SolarSimulator.py
```

### Python Script Directly
```bash
cd build_tools
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

## 📚 Documentation

- **[build_tools/QUICKSTART_SINGLE_UF2.md](build_tools/QUICKSTART_SINGLE_UF2.md)** - Complete guide
- **[build_tools/SINGLE_UF2_SUMMARY.md](build_tools/SINGLE_UF2_SUMMARY.md)** - Detailed reference & troubleshooting

## 📁 What You Get

After building:
```
SolarSimulator/
├── SolarSimulator.py              ← Your code
├── SolarSimulator_combined.uf2    ← Flash this! (1.2MB)
└── build_tools/
    ├── build_single_uf2.sh        ← Easy builder
    ├── uf2_combiner_proper.py     ← Main builder script
    ├── .firmware_cache/           ← Cached firmware (660KB)
    ├── QUICKSTART_SINGLE_UF2.md   ← Quick guide
    └── SINGLE_UF2_SUMMARY.md      ← Complete reference
```

## 🎯 Common Workflows

### Build for Your Devices
```bash
cd build_tools
./build_single_uf2.sh
# Select SolarSimulator.py from menu
```

### Update Code & Rebuild
```bash
# 1. Edit SolarSimulator.py
# 2. Rebuild
cd build_tools
./build_single_uf2.sh
# 3. Flash new UF2 to all devices
```

### Flash Multiple Devices
```bash
# Build once, then for each device:
# 1. Hold BOOTSEL, connect USB
# 2. Drag SolarSimulator_combined.uf2 to device
# 3. Repeat for next device
```

## 🛠️ Hardware

- **Board:** RP2040:bit (Raspberry Pi Pico compatible)
- **Firmware:** MicroPython v1.27.0 (included in UF2)
- **Components:** 3 servos, NeoPixel panel, 5×5 LED matrix
- **Documentation:** See `Docs/` folder

## 📝 Development Cycle

1. Edit `SolarSimulator.py`
2. Run `./build_tools/build_single_uf2.sh`
3. Drag and drop UF2 to device(s)
4. Test and repeat

## 💡 What's Inside the UF2?

Your combined UF2 file contains:
- **MicroPython firmware** (660KB) - cached locally after first download
- **Your Python code** (155KB) - embedded as `/main.py` in littlefs filesystem
- **Total:** 1.2MB single file - drag, drop, done!

---

**For detailed documentation, see: [build_tools/QUICKSTART_SINGLE_UF2.md](build_tools/QUICKSTART_SINGLE_UF2.md)**
