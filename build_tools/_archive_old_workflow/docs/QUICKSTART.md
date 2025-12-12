# 🚀 Quick Start Guide - RP2040:bit Build Toolchain

Get your Python code running on RP2040:bit devices in 3 easy steps!

## ⚡ Fastest Method (Interactive)

```bash
python quick_start.py
```

This launches an interactive menu that guides you through:
- Building deployment packages
- Flashing devices
- Updating code
- Multi-device setup

## 📦 Command Line Method

### 1. Install Tools (One-time setup)

```bash
pip install -r requirements-build.txt
```

### 2. Build Package

```bash
python build_uf2.py SolarSimulator.py
```

Creates folder: `SolarSimulator_deployment/`

### 3. Flash Device

```bash
./flash_tool.sh SolarSimulator_deployment
```

Follow the prompts to connect your device!

## 🎯 Common Tasks

### Build Current SolarSimulator.py
```bash
python build_uf2.py
```

### Flash Multiple Devices
```bash
./flash_tool.sh -m SolarSimulator_deployment
```

### Update Code Only (Skip Firmware)
```bash
./flash_tool.sh -c SolarSimulator_deployment
```

## 🛠️ Hardware Connection

1. **Hold BOOTSEL** button on RP2040:bit board
2. **Connect USB** cable (while holding BOOTSEL)
3. **Release BOOTSEL** - device appears as "RPI-RP2" drive
4. Script will automatically flash firmware and code

## 📚 Full Documentation

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for:
- Detailed setup instructions
- Troubleshooting guide
- Advanced usage
- Multiple device workflows

## 🆘 Quick Help

**Can't find device?**
- Make sure you held BOOTSEL when connecting USB
- Try a different USB cable or port
- Check `ls /dev/cu.usbmodem*` (macOS) or `ls /dev/ttyACM*` (Linux)

**Build failed?**
- Install dependencies: `pip install -r requirements-build.txt`
- Check internet connection (first run downloads firmware)

**Flash failed?**
- Verify device is in bootloader mode (RPI-RP2 drive visible)
- Try manual steps in deployment folder README.txt

## 📁 What Gets Created?

```
SolarSimulator_deployment/
├── 1_flash_firmware.uf2    ← Drag to RPI-RP2 drive
├── 2_upload_code.py         ← Your Python code  
└── README.txt               ← Detailed instructions
```

## 💡 Pro Tips

- Use `quick_start.py` for easiest experience
- Build once, flash many devices with `-m` flag
- Keep deployment folders for version tracking
- Update code only with `-c` for faster iterations

---

**Need Help?** Check BUILD_INSTRUCTIONS.md or run `python quick_start.py` and select "Help"
