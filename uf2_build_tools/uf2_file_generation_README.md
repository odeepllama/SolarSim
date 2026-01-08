# SolarSimulator UF2 File Generation Guide

## 🚀 Direct Single-File Workflow (Recommended)

Generate a single UF2 file containing both MicroPython firmware and your code, ready to flash to any RP2040:bit device.

### One-Command Build

```bash
cd uf2_build_tools
./build_single_uf2.sh
```

- Select your Python file (e.g., SolarSimulator.py) from the menu.
- The script creates a UF2 file in the root SolarSimulator directory (e.g., solsim_YYYYMMDD_HHMM.uf2).

### Flash to Device

1. Hold **BOOTSEL** button while connecting USB
2. Drag and drop the UF2 file onto the RPI-RP2 drive
3. Device reboots and runs your code automatically

No IDE or serial connection needed—just drag and drop!

---

## 🖥️ Interactive Mode (Optional)

If you prefer, you can run the script and select your file interactively:

```bash
cd uf2_build_tools
./build_single_uf2.sh
# Select file from menu
```

---

## 📝 What You Get

After building:
```
SolarSimulator/
├── SolarSimulator.py              ← Your code
├── solsim_YYYYMMDD_HHMM.uf2      ← Flash this! (1.2MB)
└── uf2_build_tools/
    ├── build_single_uf2.sh        ← Easy builder script
    ├── uf2_builder.py             ← Main builder
    └── .firmware_cache/           ← Cached firmware
```

---

## 💡 How It Works

- Downloads MicroPython firmware (cached after first run)
- Creates a littlefs filesystem with your code as main.py
- Combines firmware + filesystem into one UF2 file
- Output UF2 is ready to flash

---

## 👍 Why Use This Workflow?

- One UF2 file for firmware + code
- Fast, reliable, and easy for classrooms or multiple devices
- No manual serial uploads or IDE required

---

**You're all set! Happy flashing!**
