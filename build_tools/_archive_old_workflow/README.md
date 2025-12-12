# 🚀 RP2040:bit Build Tools

Build single UF2 files with firmware + code for easy flashing!

## ⚡ Quick Start (Recommended - Single UF2)

**Create one file with firmware + your code:**

```bash
cd build_tools
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

This creates `SolarSimulator_FULL.uf2` - just drag and drop to any RP2040:bit!

📖 **See [QUICKSTART_SINGLE_UF2.md](QUICKSTART_SINGLE_UF2.md) for complete guide**

## Two Workflows Available

### ✅ Option 1: Single Combined UF2 (RECOMMENDED)

**Perfect for:** Multiple devices, classroom setups, distribution

```bash
python3 uf2_combiner_proper.py ../SolarSimulator.py
```

- One file contains firmware + code
- Pure drag-and-drop flashing
- No IDE needed
- Uses proper littlefs filesystem

### Option 2: Two-Step (Development)

**For:** Quick code updates on configured devices

```bash
# Interactive mode
python3 quick_start.py

# OR command line
python3 build_uf2.py ../SolarSimulator.py
./flash_tool.sh ../SolarSimulator_deployment
```

## 📦 Files in This Directory

### Single UF2 Tools (RECOMMENDED)
- **uf2_combiner_proper.py** - ⭐ Creates combined UF2 (USE THIS!)
- **QUICKSTART_SINGLE_UF2.md** - Complete single UF2 guide

### Two-Step Tools (Alternative)
- **build_uf2.py** - Builds deployment packages
- **flash_tool.sh** - Automates device flashing
- **quick_start.py** - Interactive menu interface

### Support Files
- **requirements-build.txt** - Python dependencies
- **example_*.sh** - Example workflows

### Documentation (in docs/)
- **QUICKSTART.md** - Fast reference (two-step)
- **BUILD_INSTRUCTIONS.md** - Complete documentation
- **TOOLCHAIN_SUMMARY.md** - Feature overview

## 🎯 Common Tasks

### Build Single Combined UF2 (Recommended)
```bash
python3 uf2_combiner_proper.py ../SolarSimulator.py
# Creates SolarSimulator_FULL.uf2 - drag and drop to devices!
```

### Update Your Code
```bash
# Edit SolarSimulator.py, then rebuild:
python3 uf2_combiner_proper.py ../SolarSimulator.py
# Flash new UF2 to devices
```

### Custom Output Name
```bash
python3 uf2_combiner_proper.py ../SolarSimulator.py -o MyDevice.uf2
```

### Two-Step Workflow (Alternative)
```bash
# Build deployment
python3 build_uf2.py ../SolarSimulator.py

# Flash device
./flash_tool.sh ../SolarSimulator_deployment
```

## 🛠️ Setup

First time only:

```bash
pip install littlefs-python

# Or install everything:
pip install -r requirements-build.txt
```

## 📚 Documentation

- **QUICKSTART_SINGLE_UF2.md** - Single UF2 guide (START HERE!)
- **docs/QUICKSTART.md** - Two-step workflow guide
- **docs/BUILD_INSTRUCTIONS.md** - Complete reference

## 💡 Tips

1. **Single UF2 = easiest** - One file, drag and drop, done!
2. Run scripts from this directory
3. Python files in parent directory
4. Firmware cached in `.firmware_cache/` after first download

---

**For complete documentation, see docs/README_TOOLCHAIN.md**
