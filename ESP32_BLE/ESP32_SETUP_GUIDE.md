# ESP32-S3 Solar Simulator Setup Guide

## 🛠️ Hardware Requirements

### Required Components
- **ESP32-S3** module (preferably with PSRAM: ESP32-S3-WROOM-1-N16R8)
- **1602 I2C LCD** (16x2 character display with PCF8574 I2C backpack)
- **3x Servos** (same as RP2040 version)
- **NeoPixel LED Panel** (8x56 = 448 LEDs)
- **USB-C cable** for programming and power
- **External 5V power supply** for servos (if needed)
- **Jumper wires** for connections

### Optional Components
- Camera shutter trigger (if using BT camera remote)
- Buttons (2x for manual control)

---

## 📍 Pin Mapping: RP2040 → ESP32-S3

| Function | RP2040:bit | ESP32-S3 | Notes |
|----------|------------|----------|-------|
| **Servo 1** (Rotation) | GP6 | GPIO32 | Platform rotation |
| **Servo 2** (Camera 1) | GP10 | GPIO33 | Primary camera trigger |
| **Servo 3** (Camera 2) | GP11 | GPIO25 | Secondary camera |
| **NeoPixels** | GP15 | GPIO16 | 448 LED panel |
| **I2C SDA** | N/A | GPIO21 | LCD display |
| **I2C SCL** | N/A | GPIO22 | LCD display |
| **Button A** | GP0 | GPIO0 | Boot button (built-in) |
| **Button B** | GP1 | GPIO35 | Optional |
| **Camera Shutter** | GP14 | GPIO26 | BT trigger (optional) |

---

## 🔧 Software Setup

### Step 1: Install MicroPython on ESP32-S3

1. **Download ESP32-S3 MicroPython firmware**:
   - Visit: https://micropython.org/download/ESP32_GENERIC_S3/
   - Download latest stable `.bin` file

2. **Install esptool** (if not already installed):
   ```bash
   pip install esptool
   ```

3. **Erase flash** (ESP32 in bootloader mode):
   ```bash
   esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash
   ```
   
   > **Note**: Replace `/dev/ttyUSB0` with your port:
   > - macOS: `/dev/cu.usbserial-*` or `/dev/cu.usbmodem*`
   > - Windows: `COM3`, `COM4`, etc.
   > - Linux: `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.

4. **Flash MicroPython firmware**:
   ```bash
   esptool.py --chip esp32s3 --port /dev/ttyUSB0 write_flash -z 0 ESP32_GENERIC_S3-XXXXXXXX-vX.XX.X.bin
   ```

5. **Test REPL connection**:
   ```bash
   # Using screen (macOS/Linux)
   screen /dev/ttyUSB0 115200
   
   # Or using Thonny (recommended)
   # Open Thonny → Tools → Options → Interpreter
   # Select "MicroPython (ESP32)" and your port
   ```

### Step 2: Upload Project Files

Upload these files to ESP32-S3 using Thonny, ampy, or rshell:

```
/ (root)
├── boot.py                    # Runs on boot (optional)
├── main.py                    # Auto-runs after boot
├── ble_server.py             # BLE GATT server
├── lcd_i2c.py                # LCD display driver
└── solarsim_esp32.py         # Main simulation code (to be created)
```

**Using Thonny**:
1. Open file in Thonny
2. File → Save As → MicroPython device
3. Enter filename
4. Click OK

**Using ampy** (command line):
```bash
pip install adafruit-ampy
ampy --port /dev/ttyUSB0 put ble_server.py
ampy --port /dev/ttyUSB0 put lcd_i2c.py
```

---

## 🧪 Testing Components

### Test 1: BLE Server (Standalone)

1. Upload `ble_server.py` to ESP32
2. Run in REPL:
   ```python
   import ble_server
   # Server will start advertising as "SolarSim-TEST"
   ```

3. **Test with nRF Connect app** (iPad/iPhone):
   - Download "nRF Connect" from App Store (free)
   - Open app → Scan
   - Find "SolarSim-TEST" → Connect
   - Expand service: `12345678-1234-5678-1234-56789abcdef0`
   - Find Command characteristic (UUID ending in ...def1)
   - Write text: `SET SPEED 6` (select "Text" encoding)
   - Check Response characteristic (UUID ending in ...def2)
   - Should see: `Echo: SET SPEED 6`

### Test 2: I2C LCD Display

1. **Wire up LCD**:
   ```
   LCD → ESP32-S3
   VCC → 5V
   GND → GND
   SDA → GPIO21
   SCL → GPIO22
   ```

2. Upload `lcd_i2c.py` to ESP32

3. Run test in REPL:
   ```python
   from machine import I2C, Pin
   from lcd_i2c import LCD1602
   
   # Initialize I2C
   i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
   
   # Scan for devices
   print(i2c.scan())  # Should show [39] (0x27) or [63] (0x3F)
   
   # Initialize LCD
   lcd = LCD1602(i2c, addr=0x27)  # Try 0x3F if 0x27 doesn't work
   
   # Test display
   lcd.clear()
   lcd.print("Hello ESP32!", 0, 0)
   lcd.print("BLE Ready!", 0, 1)
   ```

### Test 3: NeoPixel Control

```python
from machine import Pin
import neopixel

# Initialize NeoPixel
np_pin = Pin(16, Pin.OUT)
pixels = neopixel.NeoPixel(np_pin, 448)

# Test - fill with blue
pixels.fill((0, 0, 50))
pixels.write()

# Clear
pixels.fill((0, 0, 0))
pixels.write()
```

### Test 4: Servo Control

```python
from machine import Pin, PWM

# Initialize servo (rotation platform)
servo_pin = Pin(32)
servo_pwm = PWM(servo_pin, freq=50, duty=0)

# Test positions
def set_angle(pwm, angle):
    # Map 0-270° to duty cycle
    duty = int(1400 + (angle / 270) * (8352 - 1400))
    pwm.duty_u16(duty)

# Test sweep
for angle in range(0, 271, 10):
    set_angle(servo_pwm, angle)
    time.sleep_ms(100)

# Return to 0
set_angle(servo_pwm, 0)
```

---

## 🚀 Running Full Solar Simulator

### Quick Start

1. Ensure all hardware is connected
2. Power on ESP32-S3
3. Wait for BLE advertising (~2 seconds)
4. Connect with nRF Connect or modified ProfileBuilder.html
5. Send commands just like USB serial version

### Checking Status

In REPL, after boot:
```python
# Check BLE status
print(ble.is_connected())

# Check LCD
lcd.clear()
lcd.print("Status Check", 0, 0)

# Check current simulation time
print(f"Sim time: {get_sim_time()}")
```

---

## 📱 Connecting from iPad

### Using nRF Connect (Testing)

1. Open nRF Connect app
2. Scan for devices
3. Connect to "SolarSim-ESP32"
4. Navigate to services
5. Find Solar Simulator service
6. Use Command characteristic to send commands

### Using ProfileBuilder.html (Production)

> **Note**: ProfileBuilder.html needs to be modified for Web Bluetooth API
> This will be done in Option B

Expected workflow:
1. Open ProfileBuilder.html in Chrome on iPad
2. Click "Connect to Device"
3. Select Bluetooth connection
4. Choose "SolarSim-ESP32" from list
5. Use all controls normally

---

## 🐛 Troubleshooting

### BLE not advertising
- Check `ble._ble.active()` returns `True`
- Try `ble._advertise()` manually
- Restart ESP32

### LCD not detected
- Check wiring (SDA/SCL correct?)
- Try alternate I2C address: `0x3F` instead of `0x27`
- Check I2C scan: `i2c.scan()`
- Verify 5V power to LCD

### NeoPixels not working
- Check power supply (448 LEDs need significant current)
- Verify GPIO16 connection
- Try smaller test: `neopixel.NeoPixel(Pin(16), 8)` (just 8 LEDs)

### Servos not responding
- Verify PWM pins: GPIO32, 33, 25
- Check external power supply if using
- Ensure common ground between ESP32 and servo power

### Can't connect from iPad
- Make sure Bluetooth is ON
- Try clearing Bluetooth cache (forget device, reconnect)
- Check ESP32 is advertising: LED should blink
- Try nRF Connect app first to verify BLE works

### Memory errors
- ESP32-S3 has limited RAM
- Enable PSRAM if you have PSRAM variant
- Monitor memory: `import gc; print(gc.mem_free())`
- Call `gc.collect()` periodically

---

## 📊 Expected Performance

| Feature | RP2040 | ESP32-S3 | Notes |
|---------|--------|----------|-------|
| **CPU** | 133 MHz | 240 MHz | ✅ Faster |
| **RAM** | 264 KB | 512 KB | ✅ More memory |
| **Flash** | 2 MB | 8-16 MB | ✅ More storage |
| **BLE** | ❌ No | ✅ Yes | Major advantage |
| **Matrix Display** | ✅ Built-in | ❌ External LCD | Different |
| **WiFi** | ❌ No | ✅ Yes | Future option |

---

## 📝 Next Steps

1. ✅ Test BLE server with nRF Connect
2. ✅ Test LCD display
3. ✅ Test all hardware components
4. ⏳ Port main SolarSimulator.py code
5. ⏳ Integrate BLE + LCD + Simulation
6. ⏳ Modify ProfileBuilder.html for Web Bluetooth

---

## 💡 Tips

- **Power Management**: ESP32 uses more power than RP2040. Consider heat dissipation.
- **PSRAM**: If available, enable for better performance with large buffers
- **Debugging**: Use `print()` statements - they appear in REPL over USB
- **Wireless Debugging**: BLE can serve as remote console too!
- **OTA Updates**: Consider implementing over-the-air updates later

---

## 📚 References

- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- [MicroPython ESP32 Docs](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [Web Bluetooth API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API)
- [nRF Connect App](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile)

---

**Need help?** Check the troubleshooting section or add debug prints to trace execution flow.
