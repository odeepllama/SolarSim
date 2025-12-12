# Quick Start Guide - Single UF2 Workflow

## What You Get

A **single .uf2 file** containing:
- MicroPython firmware (v1.27.0)
- Your Python code baked in as `main.py`
- Proper littlefs filesystem

## One-Command Build

```bash
cd build_tools
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

This creates `SolarSimulator_FULL.uf2` in your project folder.

## Flash to Multiple Devices

For each RP2040:bit device:

1. **Hold BOOTSEL button** while connecting USB
2. **Drag and drop** `SolarSimulator_FULL.uf2` onto the RPI-RP2 drive
3. **Done!** Device reboots and runs your code automatically

No IDE needed! No serial connection! Pure drag-and-drop!

## Update Your Code

When you modify SolarSimulator.py:

```bash
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

Then flash the new .uf2 to all your devices.

## Options

```bash
# Custom output name
python3 uf2_combiner_proper.py ../SolarSimulator.py -o MyCustom.uf2

# Use different Python file
python3 uf2_combiner_proper.py ../AnotherScript.py

# Just download firmware (useful for caching)
python3 uf2_combiner_proper.py --download-only
```

## What's Inside

The tool:
1. Downloads MicroPython firmware (cached after first run)
2. Creates a littlefs filesystem with your code as `main.py`
3. Combines firmware + filesystem into one UF2 file
4. Ready to flash!

## File Locations

```
SolarSimulator/
├── SolarSimulator.py              ← Your code
├── SolarSimulator_FULL.uf2        ← Flash this!
└── build_tools/
    ├── uf2_combiner_proper.py     ← The builder
    └── .firmware_cache/           ← Downloaded firmware
```

## Troubleshooting

**Device doesn't run code after flashing?**
- Connect via serial (screen, Thonny, etc.)
- Check if main.py exists: `import os; os.listdir('/')`
- Try running manually: `import main`

**Build fails?**
- Check you have littlefs-python: `pip install littlefs-python`
- Check SolarSimulator.py exists
- Check you're in build_tools/ directory

**Want to use the old two-step method?**
- Use `build_uf2.py` instead (firmware + serial upload)
- Useful if combined UF2 doesn't work on your device

## Why This Is Better

**Before:**
1. Flash firmware.uf2
2. Connect serial cable
3. Upload code.py via mpremote/ampy
4. Repeat for each device

**Now:**
1. Drag and drop one .uf2 file
2. Done!

Perfect for classroom setups or flashing many devices!
