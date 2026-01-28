# Solar Simulator ESP32-S3 BLE Version

Migration of Solar Simulator from RP2040:bit to ESP32-S3 with Bluetooth Low Energy control.

## 🎯 Project Goals

- ✅ Replace RP2040 5x5 matrix with I2C 1602 LCD display
- ✅ Add Bluetooth Low Energy (BLE) for wireless control from iPad
- ✅ Maintain full compatibility with ProfileBuilder.html interface
- ✅ Support both USB Serial (wired) and BLE (wireless) connections
- ✅ Improve performance with faster CPU and more memory

## 📁 Project Structure

```
ESP32_BLE/
├── README.md                    # This file
├── ACTION_PLAN.md              # 👈 START HERE - What to do next
├── ESP32_SETUP_GUIDE.md        # Detailed setup instructions
├── LIBRARY_STATUS.md           # What we built & why it works
├── PORTING_GUIDE.md            # RP2040→ESP32 code translation
├── BLE_TESTING_GUIDE.md        # BLE testing procedures
├── PIN_MAPPING.md              # Complete pin reference
├── CHECKLIST.md                # Shopping list
│
├── lib/                        # 🆕 Hardware abstraction layer
│   ├── __init__.py            # Package initialization
│   ├── hardware_esp32.py      # Hardware control (servos, NeoPixels, etc.)
│   ├── display_manager.py     # LCD display management
│   └── README.md              # Complete API documentation
│
├── ble_server.py               # BLE GATT server implementation
├── lcd_i2c.py                  # I2C LCD 1602 driver
├── boot.py                     # System initialization
├── main.py                     # Entry point (auto-runs on boot)
├── test_lib.py                 # 🆕 Comprehensive test suite
└── solarsim_esp32.py          # Main simulation (to be created next)
```

## 🚀 Quick Start

### Step 1: Read the Action Plan
**👉 Start with [ACTION_PLAN.md](ACTION_PLAN.md)** - Complete step-by-step guide

### Step 2: Hardware Setup
- Get ESP32-S3 module (with PSRAM recommended)
- Get 1602 I2C LCD display  
- Get servos, NeoPixel panel, buttons
- Wire per [PIN_MAPPING.md](PIN_MAPPING.md)

### Step 3: Flash MicroPython
1. Download MicroPython firmware for ESP32-S3
2. Flash using esptool: `esptool.py --port /dev/tty.xxx erase_flash`
3. Flash firmware: `esptool.py --port /dev/tty.xxx write_flash -z 0x0 firmware.bin`

### Step 4: Upload Files
Using VS Code + MicroPython extension:
```
Upload to ESP32:
- lib/__init__.py
- lib/hardware_esp32.py
- lib/display_manager.py
- ble_server.py
- lcd_i2c.py
- boot.py
- main.py
- test_lib.py
```

### Step 5: Run Tests
Connect to serial console and run:
```python
# Full integrated test
import test_lib
test_lib.test_integrated_system()

# Or quick sanity check
test_lib.quick_test()
```

**Expected:** All hardware tests pass, LCD displays messages, servos move, LEDs light up.

### Step 6: Use the Library
```python
from lib import HardwareESP32, DisplayManager

# Initialize
hw = HardwareESP32()
dm = DisplayManager(hw.lcd)

# Control hardware
hw.set_servo1_angle(90)
hw.fill_panel(50, 25, 0)
dm.display_status(43200, 60.0, 75, True)
```

See [lib/README.md](lib/README.md) for complete API documentation.

## 🔌 Connection Methods

### Method 1: USB Serial (Wired)
- Connect ESP32 via USB-C
- Use current ProfileBuilder.html (Web Serial API)
- Same as RP2040 experience

### Method 2: Bluetooth LE (Wireless)
- Pair with ESP32 via BLE
- Use modified ProfileBuilder.html (Web Bluetooth API)
- Works on iPad Chrome/Safari ✅

## 📊 BLE Service Architecture

**Service UUID**: `12345678-1234-5678-1234-56789abcdef0`

### Characteristics:

1. **Command** (Write) - `...def1`
   - Receive commands from browser
   - Format: Text strings (same as serial)
   - Examples: `SET SPEED 6`, `FILL 30 30 30`

2. **Response** (Read/Notify) - `...def2`
   - Send command responses back
   - Format: Text strings
   - Automatically sent after command processing

3. **Status** (Read/Notify) - `...def3`
   - Periodic status updates
   - Format: JSON objects
   - Updated every 1-5 seconds

## 🎮 LCD Display Layout

```
┌────────────────┐
│12:34    HOLD   │  Line 1: Time & Speed
│I:1.00   AL:ON  │  Line 2: Intensity & Auto-load
└────────────────┘
```

### Display Elements:
- **Time**: HH:MM simulation time
- **Speed**: 1X, 6X, 60X, 600X, or HOLD
- **Intensity**: 0.00-9.99 (brightness scale)
- **Auto-load**: AL:ON or AL:OF

## 🛠️ Development Status

### ✅ Phase 1: BLE Infrastructure (COMPLETE)
- [x] BLE GATT server with chunked data transfer
- [x] LCD I2C driver
- [x] Boot configuration
- [x] System diagnostics
- [x] Test command handler
- [x] BLE hardware testing with nRF Connect ✓

### ✅ Phase 1.5: Hardware Abstraction (COMPLETE)
- [x] Hardware abstraction layer (`lib/hardware_esp32.py`)
- [x] Display manager (`lib/display_manager.py`)
- [x] Comprehensive test suite (`test_lib.py`)
- [x] Complete API documentation
- [x] RP2040→ESP32 porting guide

### ⏳ Phase 2: Hardware Validation (CURRENT)
- [ ] Upload library files to ESP32
- [ ] Run integrated test suite
- [ ] Verify all hardware subsystems
- [ ] Confirm LCD, servos, NeoPixels working
- [ ] See **ACTION_PLAN.md** for detailed steps 👈

### ⏸️ Phase 3: Main Code Port (NEXT)
- [ ] Port simulation logic from SolarSimulator.py (3195 lines)
- [ ] Create `solarsim_esp32.py` using hardware abstraction
- [ ] Port time management, solar calculations
- [ ] Port rotation control, NeoPixel updates
- [ ] Port command handler, program manager
- [ ] Integration testing

### ⏸️ Phase 4: Web Interface (FINAL)
- [ ] Modify ProfileBuilder.html for Web Bluetooth
- [ ] Replace Serial API with Bluetooth API
- [ ] Test from iPad Chrome
- [ ] Full end-to-end testing

### 📋 Todo
- [ ] ProfileBuilder.html Web Bluetooth support
- [ ] OTA update capability
- [ ] Battery operation optimization

## 🔧 Key Differences from RP2040 Version

| Feature | RP2040:bit | ESP32-S3 |
|---------|------------|----------|
| Display | 5x5 LED matrix | 16x2 LCD |
| Connection | USB Serial | USB + BLE |
| WiFi | No | Yes (future) |
| CPU Speed | 133 MHz | 240 MHz |
| RAM | 264 KB | 512 KB + PSRAM |
| iPad Control | No | Yes ✅ |

## 📱 Testing with nRF Connect App

1. Install nRF Connect (free, App Store)
2. Scan for "SolarSim-ESP32"
3. Connect to device
4. Expand Solar Simulator service
5. Write to Command characteristic
6. Read Response characteristic

### Example Commands:
```
SET SPEED 6
SET TIME 1200
SET INTENSITY 0.5
FILL 50 50 50
STATUS
```

## 🐛 Common Issues & Solutions

### Issue: BLE not visible
**Solution**: Check `ble._ble.active()`, restart ESP32

### Issue: LCD blank
**Solution**: Adjust contrast pot on I2C backpack, check address (0x27 or 0x3F)

### Issue: Memory errors
**Solution**: Enable PSRAM, call `gc.collect()` more frequently

### Issue: Can't upload files
**Solution**: Put ESP32 in safe mode, hold BOOT button during upload

## 📚 Documentation

- **Setup Guide**: `ESP32_SETUP_GUIDE.md` - Complete hardware and software setup
- **Original Code**: `../SolarSimulator.py` - RP2040 reference implementation
- **Web Interface**: `../ProfileBuilder.html` - Browser control interface

## 🔗 Related Files

- `../SolarSimulator.py` - Original RP2040 implementation
- `../ProfileBuilder.html` - Web control interface (to be modified)
- `../Docs/README.md` - Project overview

## 💡 Tips

- Keep both USB and BLE connections active for debugging
- LCD provides instant feedback without browser connection
- Use nRF Connect for testing before modifying HTML
- Monitor memory with `gc.mem_free()` during development

## 🎓 Learning Resources

- [MicroPython ESP32](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [Web Bluetooth API](https://web.dev/bluetooth/)
- [BLE GATT Tutorial](https://learn.adafruit.com/introduction-to-bluetooth-low-energy/gatt)

---

**Status**: Phase 1 Complete - Ready for hardware testing when ESP32 arrives!

**Next**: Create `solarsim_esp32.py` with integrated BLE and LCD support
