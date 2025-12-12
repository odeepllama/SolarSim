# RP2040:bit Build Toolchain

This toolchain helps you convert your Python files into deployable packages for the RP2040:bit board. It automates the process of creating firmware and code packages that can be flashed to multiple devices.

## 🎯 Quick Start

```bash
# 1. Install dependencies (one time only)
pip install -r requirements-build.txt

# 2. Build a deployment package
python build_uf2.py SolarSimulator.py

# 3. Flash to device (automatic)
./flash_tool.sh SolarSimulator_deployment
```

## 📋 Prerequisites

- **Python 3.7+** installed on your system
- **USB access** to connect RP2040:bit devices
- **Internet connection** for first-time firmware download (cached afterward)

### Optional Tools
- **Thonny IDE** - Easiest for beginners ([Download](https://thonny.org))
- **mpremote** or **ampy** - Command-line tools (auto-installed with requirements)

## 🔧 Installation

### 1. Install Build Tools

```bash
cd SolarSimulator
pip install -r requirements-build.txt
```

This installs:
- `mpremote` - Official MicroPython remote control tool
- `adafruit-ampy` - Alternative file upload tool
- `pyserial` - Serial communication library

### 2. Make Scripts Executable (macOS/Linux)

```bash
chmod +x build_uf2.py
chmod +x flash_tool.sh
```

## 📦 Building Deployment Packages

### Basic Build

Build the current `SolarSimulator.py`:

```bash
python build_uf2.py
```

This creates a folder: `SolarSimulator_deployment/` containing:
- `1_flash_firmware.uf2` - MicroPython firmware
- `2_upload_code.py` - Your Python code
- `README.txt` - Detailed instructions

### Build Any Python File

```bash
python build_uf2.py MyCustomFile.py
```

### Custom Output Name

```bash
python build_uf2.py SolarSimulator.py -o MyExperiment
```

### Specify MicroPython Version

```bash
python build_uf2.py --micropython-version v1.22.0
```

## 🔌 Flashing Devices

### Automatic Flashing (Recommended)

The `flash_tool.sh` script automates the entire process:

```bash
./flash_tool.sh SolarSimulator_deployment
```

### Flash Multiple Devices

Perfect for setting up multiple identical units:

```bash
./flash_tool.sh -m SolarSimulator_deployment
```

The script will:
1. Flash the first device
2. Ask if you want to flash another
3. Repeat until you're done

### Update Code Only (Skip Firmware)

When you only changed the Python code:

```bash
./flash_tool.sh -c SolarSimulator_deployment
```

This is much faster as it skips firmware flashing.

### Flash Firmware Only

```bash
./flash_tool.sh -f SolarSimulator_deployment
```

### Specify Port Manually

```bash
./flash_tool.sh -p /dev/cu.usbmodem14201 SolarSimulator_deployment
```

## 🛠️ Manual Flashing

If you prefer manual control or the script doesn't work:

### Step 1: Flash Firmware

1. Hold **BOOTSEL** button on RP2040:bit
2. Connect USB cable (while holding BOOTSEL)
3. Release BOOTSEL - device appears as `RPI-RP2` drive
4. Drag `1_flash_firmware.uf2` to the `RPI-RP2` drive
5. Device reboots automatically

### Step 2: Upload Code

**Option A - Using Thonny (Easiest):**
1. Open Thonny IDE
2. Go to Tools → Options → Interpreter
3. Select "MicroPython (Raspberry Pi Pico)"
4. Open `2_upload_code.py`
5. Click Save → Raspberry Pi Pico
6. Save as `main.py`

**Option B - Using mpremote:**
```bash
mpremote fs cp 2_upload_code.py :main.py
mpremote reset
```

**Option C - Using ampy:**
```bash
# Find your port first (see below)
ampy --port /dev/cu.usbmodem14201 put 2_upload_code.py /main.py
```

## 🔍 Finding Your Device Port

### macOS
```bash
ls /dev/cu.usbmodem*
```

### Linux
```bash
ls /dev/ttyACM*
```

### Windows
Check Device Manager under "Ports (COM & LPT)" or:
```bash
mode
```

## 📁 File Structure

After building, you'll have:

```
SolarSimulator_deployment/
├── 1_flash_firmware.uf2    # MicroPython firmware (~1.4 MB)
├── 2_upload_code.py         # Your code (will become main.py)
└── README.txt               # Detailed flashing instructions
```

## 🔄 Updating Your Code

### Quick Update Workflow

1. Edit your Python file (e.g., `SolarSimulator.py`)
2. Rebuild: `python build_uf2.py`
3. Flash code only: `./flash_tool.sh -c SolarSimulator_deployment`

This skips firmware flashing and just updates the code - much faster!

### Version Management

Keep deployment folders organized:

```bash
python build_uf2.py -o SolarSim_v1.0
python build_uf2.py -o SolarSim_v1.1
python build_uf2.py -o SolarSim_v2.0
```

## 🎓 Advanced Usage

### Batch Processing

Flash multiple devices with a single command:

```bash
# Build once
python build_uf2.py

# Flash multiple devices interactively
./flash_tool.sh -m SolarSimulator_deployment
```

### Custom Build Scripts

Create your own build script for specific configurations:

```python
import subprocess
import sys

files_to_build = [
    "SolarSimulator.py",
    "SolarSimulator_20251211.py",
    "SolarSimulator_20251130.py"
]

for file in files_to_build:
    print(f"\n{'='*60}")
    print(f"Building {file}...")
    print('='*60)
    
    result = subprocess.run([
        sys.executable,
        "build_uf2.py",
        file,
        "-o",
        file.replace(".py", "_deployment")
    ])
    
    if result.returncode != 0:
        print(f"Failed to build {file}")
        break
```

### Working with Different MicroPython Versions

The toolchain caches firmware downloads in `~/.rp2040_uf2_cache/`. To use a different version:

```bash
# Clear cache if needed
rm -rf ~/.rp2040_uf2_cache/

# Build with specific version
python build_uf2.py --micropython-version v1.21.0
```

## 🐛 Troubleshooting

### "Device not found" or Port Detection Issues

**macOS/Linux:**
```bash
# Check if device is connected
ls /dev/cu.* | grep usb
ls /dev/tty* | grep ACM

# Check permissions (Linux)
sudo chmod 666 /dev/ttyACM0
```

**Windows:**
- Install the [RP2040 driver](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#resetting-flash-memory)
- Check Device Manager for COM port number

### Firmware Download Fails

The script tries to download from `micropython.org`. If it fails:

1. Check your internet connection
2. Download manually from [MicroPython Downloads](https://micropython.org/download/RPI_PICO/)
3. Place in `~/.rp2040_uf2_cache/` as `micropython-vX.XX.X.uf2`

### "Permission Denied" on Scripts

```bash
chmod +x build_uf2.py flash_tool.sh
```

### Code Upload Fails

1. Make sure firmware is flashed first
2. Try different tool: `mpremote` or `ampy`
3. Check serial port permissions
4. Try reconnecting the device

### Device Doesn't Boot Code

Make sure the file is named `main.py` on the device. Check with:

```bash
mpremote fs ls
# Should show: main.py
```

## 📚 Additional Resources

- [RP2040:bit Documentation](https://spotpear.com/index/study/detail/id/943.html)
- [MicroPython Documentation](https://docs.micropython.org/)
- [RP2040 Getting Started](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
- [Thonny IDE Guide](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico)

## 💡 Tips & Best Practices

1. **Keep firmware cached** - The first build downloads ~1.4MB, subsequent builds are instant
2. **Use version tags** - Name your deployments: `SolarSim_v1.0_deployment`
3. **Test on one device first** - Before flashing multiple devices
4. **Label your devices** - Number them when flashing multiple units
5. **Keep backups** - Save deployment folders for each version
6. **Code-only updates** - Use `-c` flag to skip firmware and save time

## 🤝 Workflow for Multiple Devices

Recommended workflow for setting up multiple identical RP2040:bit devices:

```bash
# 1. Build once
python build_uf2.py -o ProductionRun_v1.0

# 2. Test on one device
./flash_tool.sh ProductionRun_v1.0_deployment

# 3. Verify it works
# Connect serial and check output

# 4. Flash remaining devices
./flash_tool.sh -m ProductionRun_v1.0_deployment

# 5. Label each device as you flash it
```

## 📞 Support

If you encounter issues:

1. Check this documentation
2. Review the generated `README.txt` in deployment folders
3. Verify device is properly connected (LED should be on)
4. Try manual flashing steps to isolate the issue

---

**Version:** 1.0  
**Last Updated:** December 2024  
**Compatible with:** MicroPython v1.20.0+, RP2040:bit boards
