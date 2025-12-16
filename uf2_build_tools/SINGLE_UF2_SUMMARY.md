# 🎉 Single UF2 Toolchain - READY TO USE!

## What You Have Now

✅ **Complete single-UF2 build system**
- Creates one file with firmware + your code baked in
- Pure drag-and-drop flashing to multiple devices
- No IDE, no serial connection, no complexity!

## The Magic File

**`SolarSimulator_FULL.uf2`** (1.1 MB)

This file contains:
- MicroPython v1.27.0 firmware
- Your SolarSimulator.py code (158KB)
- Proper littlefs filesystem with main.py

## How To Use

### First Time Setup

```bash
cd uf2_build_tools
pip install littlefs-python
```

### Build Combined UF2

```bash
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

Output: `SolarSimulator_FULL.uf2` in parent directory

### Flash to Devices

For each RP2040:bit:

1. **Hold BOOTSEL** button
2. **Plug in USB** (keep holding)
3. **Release BOOTSEL** → RPI-RP2 drive appears
4. **Drag & drop** `SolarSimulator_FULL.uf2` onto drive
5. **Done!** Device reboots and runs your code

### Update Your Code

1. Edit `SolarSimulator.py`
2. Rebuild: `python3 uf2_builder.py ../SolarSimulator.py`
3. Flash new UF2 to all devices

That's it!

## What Gets Created

```
SolarSimulator/
├── SolarSimulator.py              ← Your code
├── SolarSimulator_FULL.uf2        ← ⭐ FLASH THIS FILE! ⭐
└── uf2_build_tools/
    ├── uf2_builder.py             ← The builder
    ├── QUICKSTART_SINGLE_UF2.md   ← Full guide
    └── .firmware_cache/           ← Downloaded firmware (cached)
```

## How It Works

The tool:

1. **Downloads** MicroPython firmware (once, then cached)
2. **Creates** a littlefs filesystem image
3. **Adds** your code as `/main.py` in the filesystem
4. **Combines** firmware + filesystem into single UF2
5. **Outputs** ready-to-flash file

When you flash the UF2:
- Firmware installs to RP2040
- Filesystem with main.py installs to flash
- MicroPython boots and automatically runs main.py
- Your code runs!

## Technical Details

- **Firmware:** MicroPython v1.27.0 (2024-12-09)
- **Firmware blocks:** 1,320 (675KB)
- **Filesystem:** LittleFS, 256KB at offset 0x00100000
- **Filesystem blocks:** 1,024
- **Total UF2:** 2,344 blocks (1.1MB)
- **Your code location:** `/main.py` on device

## Advantages Over Two-Step

### Before (Two-Step):
```
For each device:
1. Hold BOOTSEL, connect USB
2. Drag firmware.uf2
3. Wait for reboot
4. Connect serial cable
5. Run: mpremote cp code.py :main.py
6. Disconnect serial
7. Reboot device
Time: ~3-5 minutes per device
```

### Now (Single UF2):
```
For each device:
1. Hold BOOTSEL, connect USB
2. Drag SolarSimulator_FULL.uf2
3. Done!
Time: ~30 seconds per device
```

**Time saved for 10 devices: ~40 minutes!**

## Files You Can Ignore

The following are for the old two-step workflow:

- `build_uf2.py` - Old builder (keeps firmware & code separate)
- `flash_tool.sh` - Old serial upload script
- `quick_start.py` - Old interactive menu
- `SolarSimulator_combined.uf2` - Test file (use `_FULL.uf2` instead)

Keep them around if you need the two-step workflow for development.

## Troubleshooting

### Code doesn't run after flashing

Connect via serial and check:
```python
>>> import os
>>> os.listdir('/')
['main.py', 'boot.py']  # main.py should be there!

>>> import main  # Try running it
```

If main.py is missing, the filesystem wasn't written correctly. Try:
1. Rebuild the UF2
2. Re-flash the device
3. Check the device has enough flash (needs 1MB+)

### Build fails: "littlefs-python not installed"

```bash
pip install littlefs-python
```

### Build fails: "Python file not found"

Make sure you're running from `uf2_build_tools/` directory:
```bash
cd uf2_build_tools
python3 uf2_builder.py ../SolarSimulator.py
```

### Want to verify UF2 contents?

The UF2 contains:
- Blocks 0-1319: MicroPython firmware
- Blocks 1320-2343: Filesystem with your code

You can't easily view it without tools, but trust that it's there!

## Next Steps

1. ✅ Build your UF2: `python3 uf2_builder.py ../SolarSimulator.py`
2. ✅ Test on one device first
3. ✅ Once confirmed working, flash all devices!

## Distribution

To share with others:
1. Give them `SolarSimulator_FULL.uf2`
2. Give them flashing instructions (see above)
3. Done!

No need to share your Python source code if you don't want to.
Everything is baked into the UF2!

## Support

See detailed guides:
- [QUICKSTART_SINGLE_UF2.md](QUICKSTART_SINGLE_UF2.md) - Complete guide
- [README.md](README.md) - Tools overview

---

**You're all set! Happy flashing! 🚀**
