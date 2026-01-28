# ESP32-S3 Pin Mapping for Solar Simulator

## 📍 Complete Pin Assignment

```
ESP32-S3 Module Pinout
=======================

                    ┌─────────────────┐
                    │   ESP32-S3      │
                    │                 │
         GND ──────┤ GND         3V3 ├───── 3.3V Out
                   │                 │
  [Servo 1] ──────┤ GPIO32      5V  ├───── 5V Out
  [Servo 2] ──────┤ GPIO33     GND  ├───── GND
  [Servo 3] ──────┤ GPIO25     GPIO ├───── 
[NeoPixel] ──────┤ GPIO16   GPIO21 ├───── [LCD SDA]
                   │         GPIO22 ├───── [LCD SCL]
[Cam Shut] ──────┤ GPIO26          │
 [Button B] ──────┤ GPIO35          │
                   │    [BOOT]       │
 [Button A] ──────┤ GPIO0           │
                   │                 │
                   └─────────────────┘
                         USB-C
```

## 🔌 Connection Details

### Servos (PWM Output)
| Function | GPIO | RP2040 | Notes |
|----------|------|--------|-------|
| Platform Rotation | **GPIO32** | GP6 | Servo 1 - 0-270° rotation |
| Primary Camera | **GPIO33** | GP10 | Servo 2 - Camera trigger |
| Secondary Camera | **GPIO25** | GP11 | Servo 3 - Second camera/video |

**Wiring**:
```
Servo Signal → GPIO
Servo VCC → 5V (external power if multiple servos)
Servo GND → GND (common ground!)
```

### NeoPixel LED Panel
| Function | GPIO | RP2040 | Notes |
|----------|------|--------|-------|
| Data Line | **GPIO16** | GP15 | 448 LEDs (8×56 panel) |

**Wiring**:
```
NeoPixel DI (Data In) → GPIO16
NeoPixel 5V → 5V (needs high current!)
NeoPixel GND → GND
```

⚠️ **Power Warning**: 448 LEDs can draw 25-30A at full brightness!
- Use external 5V power supply for LEDs
- Keep ESP32 on separate USB power
- **Always connect grounds together**

### I2C LCD Display (New!)
| Function | GPIO | Standard | Notes |
|----------|------|----------|-------|
| SDA (Data) | **GPIO21** | I2C Default | I2C data line |
| SCL (Clock) | **GPIO22** | I2C Default | I2C clock line |

**Wiring**:
```
LCD VCC → 5V
LCD GND → GND
LCD SDA → GPIO21
LCD SCL → GPIO22
```

**I2C Address**: Usually 0x27 or 0x3F (check with i2c.scan())

### Buttons
| Function | GPIO | RP2040 | Notes |
|----------|------|--------|-------|
| Button A | **GPIO0** | GP0 | Built-in BOOT button |
| Button B | **GPIO35** | GP1 | External button (optional) |

**Wiring** (Button B):
```
One side → GPIO35
Other side → GND
(Internal pull-up enabled in code)
```

### Camera Shutter Trigger (Optional)
| Function | GPIO | RP2040 | Notes |
|----------|------|--------|-------|
| BT Trigger | **GPIO26** | GP14 | Active LOW, idle HIGH |

**Wiring**:
```
Signal → Camera remote input
GND → Camera remote ground
```

---

## 🔧 Power Distribution

### Option 1: USB-C Only (Light Load)
```
USB-C (5V 1A)
    │
    ├─→ ESP32-S3 (200-300mA)
    ├─→ LCD Display (20-50mA)
    ├─→ Servos idle (10mA each)
    └─→ NeoPixels dim/off
    
Total: <500mA ✅ Safe
```

### Option 2: External Power (Full Load)
```
USB-C (5V 1A)              External PSU (5V 3-5A)
    │                              │
    └─→ ESP32-S3                  ├─→ NeoPixels (up to 30A!)
        LCD                        └─→ Servos (up to 1A each)
        
        GND ←──────────────────────→ GND (COMMON GROUND!)
```

⚠️ **Critical**: Always connect grounds together when using multiple power supplies!

---

## 📊 Comparison: RP2040:bit vs ESP32-S3

| Feature | RP2040:bit Pin | ESP32-S3 Pin | Change |
|---------|---------------|--------------|--------|
| **Servo 1** | GP6 (Pin 3) | GPIO32 | Changed |
| **Servo 2** | GP10 (Pin 13) | GPIO33 | Changed |
| **Servo 3** | GP11 (Pin 15) | GPIO25 | Changed |
| **NeoPixels** | GP15 (Pin 7) | GPIO16 | Changed |
| **LCD SDA** | ❌ None | GPIO21 | **New!** |
| **LCD SCL** | ❌ None | GPIO22 | **New!** |
| **Button A** | GP0 (P0) | GPIO0 | Same concept |
| **Button B** | GP1 (P1) | GPIO35 | Changed |
| **Camera Trig** | GP14 (Pin 6) | GPIO26 | Changed |
| **LED Matrix** | GP2-25 | ❌ Removed | **Replaced by LCD** |

---

## 🧪 Testing Each Pin

### Test Servo (GPIO32)
```python
from machine import Pin, PWM
import time

servo = PWM(Pin(32), freq=50)
servo.duty_u16(4915)  # 90 degrees
time.sleep(1)
servo.duty_u16(1400)  # 0 degrees
```

### Test NeoPixel (GPIO16)
```python
from machine import Pin
import neopixel

np = neopixel.NeoPixel(Pin(16), 8)  # Test with 8 LEDs
np[0] = (10, 0, 0)  # Red
np.write()
```

### Test LCD (GPIO21/22)
```python
from machine import I2C, Pin
from lcd_i2c import LCD1602

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
lcd = LCD1602(i2c, 0x27)
lcd.print("Test OK!", 0, 0)
```

### Test Button (GPIO0)
```python
from machine import Pin

btn = Pin(0, Pin.IN, Pin.PULL_UP)
print("Button state:", btn.value())  # 0 when pressed
```

---

## ⚡ GPIO Capabilities

### Safe Pins for Any Use
- GPIO32, 33, 25, 26, 16, 21, 22, 35 ✅

### Special Pins (Avoid or use carefully)
- GPIO0: Boot mode selector (OK for button)
- GPIO19, 20: USB (don't use)
- GPIO43, 44: Flash (don't use)

### Maximum Ratings
- GPIO current: 40mA per pin (max)
- Total GPIO current: 200mA (max)
- Input voltage: 0-3.3V (⚠️ NOT 5V tolerant!)

**Level Shifter Needed For**:
- 5V signals to ESP32 inputs
- (Most sensors/modules are 3.3V compatible)

---

## 🎨 Color Coding Suggestion for Wiring

| Color | Use For | Example |
|-------|---------|---------|
| **Red** | 5V Power | Servo VCC, NeoPixel 5V |
| **Black** | Ground | All GND connections |
| **Yellow** | PWM Signals | Servo signal wires |
| **Green** | I2C SDA | LCD data |
| **Blue** | I2C SCL | LCD clock |
| **White** | Data Signals | NeoPixel DI |
| **Orange** | Other Signals | Camera trigger, buttons |

---

## 🔍 I2C Bus Scan

To find devices on I2C bus:
```python
from machine import I2C, Pin

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
devices = i2c.scan()

if devices:
    print("I2C devices found:")
    for device in devices:
        print(f"  - 0x{device:02x} ({device})")
else:
    print("No I2C devices found")
```

**Expected Output**:
```
I2C devices found:
  - 0x27 (39)      ← LCD display
```

---

## 📐 Physical Layout Recommendation

```
┌─────────────────────────────────────┐
│                                     │
│  [ESP32-S3 Module]                 │
│       │   │   │                     │
│      USB  │   │                     │
│           │   │                     │
│         GPIO  I2C                   │
│           │   │                     │
│           │   └─────→ [LCD Display]│
│           │                         │
│           ├─────→ [Servo 1]        │
│           ├─────→ [Servo 2]        │
│           ├─────→ [Servo 3]        │
│           └─────→ [NeoPixels]      │
│                                     │
└─────────────────────────────────────┘
```

**Tips**:
- Keep I2C wires short (<30cm) and twisted
- Keep servo wires away from I2C to reduce noise
- Use a breadboard for initial testing
- Label all connections!

---

## ✅ Pre-Flight Checklist

Before powering on:
- [ ] Double-check 5V not connected to GPIO inputs
- [ ] Verify common ground between all power supplies
- [ ] Check no short circuits with multimeter
- [ ] Verify I2C wiring (SDA ↔ GPIO21, SCL ↔ GPIO22)
- [ ] Ensure servo signal wires to correct GPIOs
- [ ] NeoPixel data to GPIO16

**Then**: Power on USB-C first, then external power (if used)

---

**Ready for wiring!** Refer to SETUP_GUIDE.md for testing procedures.
