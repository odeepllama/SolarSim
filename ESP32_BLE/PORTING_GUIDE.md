# Quick Reference: RP2040 → ESP32 Code Translation

This guide shows side-by-side code translations for porting from RP2040:bit to ESP32-S3.

---

## Initialization

### RP2040
```python
from microbit import display, button_a, button_b, pin15
import machine
import neopixel

# Servo setup
servo_pin = machine.Pin(6)
servo_pwm = machine.PWM(servo_pin)
servo_pwm.freq(50)

# NeoPixels
np = neopixel.NeoPixel(pin15, 448)

# Display (5x5 LED matrix)
display.clear()
```

### ESP32
```python
from lib import HardwareESP32, DisplayManager

# All hardware initialized in one call
hw = HardwareESP32(neopixel_count=448)
dm = DisplayManager(hw.lcd)

# That's it! Servos, NeoPixels, LCD all ready
```

---

## Display

### RP2040 (5x5 LED Matrix)
```python
# Show text
display.scroll("Hello")

# Show single character
display.show("A")

# Show image
display.show(Image.HEART)

# Clear
display.clear()

# Custom pattern
display.show(Image("90009:09090:00900:09090:90009"))
```

### ESP32 (16x2 LCD)
```python
# Scroll text
dm.scroll_text("Hello", scroll_speed=300)

# Show single character
dm.show_single_char("A", duration_ms=1000)

# Show message (replaces images)
dm.display_message("Status OK", "Ready!")

# Clear
dm.clear()

# Status display (replaces custom patterns)
dm.display_status(
    sim_time=43200,
    sim_speed=60.0,
    intensity=75,
    autoload=True
)
# LCD shows: "12:00:00 x60"
#            "I: 75% AL:ON"
```

---

## Servos

### RP2040
```python
# Initialize servo
servo_pin = machine.Pin(6)
servo_pwm = machine.PWM(servo_pin)
servo_pwm.freq(50)

# Set position (manual PWM calculation)
def set_servo_angle(pwm, angle):
    duty_range = MAX_DUTY - MIN_DUTY
    duty = MIN_DUTY + (angle / 270) * duty_range
    pwm.duty_u16(int(duty))

set_servo_angle(servo_pwm, 90)
```

### ESP32
```python
# Servo already initialized by HardwareESP32

# Set rotation table angle (0-360°)
hw.set_servo1_angle(90)

# Set camera servo angle (0-270°)
hw.set_servo_angle(hw.servo_pwm_2, 45)
hw.set_servo_angle(hw.servo_pwm_3, 90)

# Using calibration tables (optional)
hw.set_servo1_angle(180, use_1to1_ratio=False)
```

---

## NeoPixels

### RP2040
```python
from microbit import pin15
import neopixel

np = neopixel.NeoPixel(pin15, 448)

# Set single pixel
np[0] = (255, 0, 0)
np.show()

# Fill all
for i in range(len(np)):
    np[i] = (0, 255, 0)
np.show()

# Clear
np.clear()
```

### ESP32
```python
# NeoPixels already initialized by HardwareESP32

# Set single pixel
hw.pixels[0] = (255, 0, 0)
hw.pixels.write()

# Fill all
hw.fill_panel(0, 255, 0)

# Clear
hw.fill_panel(0, 0, 0)

# Convert coordinates to index (for 8×56 panel)
index = hw.xy_to_index(x, y)
hw.pixels[index] = (r, g, b)
hw.pixels.write()
```

---

## Buttons

### RP2040
```python
from microbit import button_a, button_b

if button_a.is_pressed():
    print("Button A pressed")

if button_b.is_pressed():
    print("Button B pressed")
```

### ESP32
```python
# Buttons already initialized by HardwareESP32

if hw.button_a_pressed():
    print("Button A pressed")

if hw.button_b_pressed():
    print("Button B pressed")
```

---

## Camera Trigger

### RP2040
```python
from microbit import pin14

# Initialize
camera_pin = pin14
camera_pin.write_digital(1)  # Idle HIGH

# Trigger
camera_pin.write_digital(0)  # Active LOW
sleep(10)
camera_pin.write_digital(1)  # Back to HIGH
```

### ESP32
```python
# Camera trigger already initialized by HardwareESP32

# Trigger (10ms pulse automatically handled)
hw.trigger_camera_shutter()
```

---

## Pin Mapping

| Function | RP2040:bit | ESP32-S3 | Notes |
|----------|------------|----------|-------|
| Servo 1 (Rotation) | GP6 | GPIO32 | Platform rotation |
| Servo 2 (Camera 1) | GP10 | GPIO33 | Camera trigger |
| Servo 3 (Camera 2) | GP11 | GPIO25 | Camera trigger |
| NeoPixels | GP15 | GPIO16 | LED panel data |
| Camera Shutter | GP14 | GPIO26 | Active LOW trigger |
| Button A | GP0 | GPIO0 | BOOT button |
| Button B | GP1 | GPIO35 | External button |
| Display | 5×5 Matrix (GP0-9) | I2C LCD (GPIO21/22) | SDA=21, SCL=22 |

---

## Common Patterns

### Pattern 1: Status Update Loop

#### RP2040
```python
while True:
    # Update simulation
    sim_time = update_simulation()
    
    # Show on 5x5 matrix (limited info)
    hours = int(sim_time / 3600)
    display.show(str(hours))
    
    # Control hardware
    servo_pwm.duty_u16(calculate_pwm(sim_time))
    
    sleep(100)
```

#### ESP32
```python
while True:
    # Update simulation
    sim_time = update_simulation()
    
    # Show full status on LCD
    dm.display_status(
        sim_time=sim_time,
        sim_speed=get_speed(),
        intensity=get_intensity(),
        autoload=autoload_enabled
    )
    
    # Control hardware (same method names)
    hw.set_servo1_angle(calculate_angle(sim_time))
    
    sleep(100)
```

### Pattern 2: Error Handling

#### RP2040
```python
try:
    # Some operation
    result = do_something()
except Exception as e:
    # Limited display space
    display.show(Image.SAD)
    print(f"Error: {e}")
```

#### ESP32
```python
try:
    # Some operation
    result = do_something()
except Exception as e:
    # Full error message on LCD
    dm.display_error("Operation", "Failed!")
    print(f"Error: {e}")
```

### Pattern 3: Animation

#### RP2040
```python
# Limited to 5x5 patterns
images = [Image.ARROW_N, Image.ARROW_E, Image.ARROW_S, Image.ARROW_W]
for img in images:
    display.show(img)
    sleep(200)
```

#### ESP32
```python
# Full 16-character lines
frames = [
    ("   North   ", "Direction"),
    ("   East    ", "Direction"),
    ("   South   ", "Direction"),
    ("   West    ", "Direction"),
]
dm.show_animation(frames, frame_delay=200)
```

### Pattern 4: Progress Indication

#### RP2040
```python
# Show dots for progress (limited space)
for i in range(5):
    display.set_pixel(i, 2, 9)
    sleep(500)
```

#### ESP32
```python
# Full width progress bar
for progress in range(0, 101, 10):
    dm.display_progress_bar("Loading", progress)
    sleep(500)
# Shows: "Loading"
#        "################" (when 100%)
```

---

## Complete Example: Solar Simulation Cycle

### RP2040
```python
from microbit import display, pin15
import machine
import neopixel

# Setup
servo = machine.PWM(machine.Pin(6))
servo.freq(50)
np = neopixel.NeoPixel(pin15, 448)

def solar_cycle():
    for hour in range(6, 19):  # 6 AM to 6 PM
        sim_time = hour * 3600
        
        # Calculate sun position (0-180°)
        angle = (hour - 6) * 180 / 12
        
        # Calculate intensity (parabolic curve)
        intensity = int(100 * (1 - ((hour - 12) / 6) ** 2))
        
        # Update hardware
        servo.duty_u16(angle_to_pwm(angle))
        
        # Set panel color
        rgb_val = int(255 * intensity / 100)
        for i in range(len(np)):
            np[i] = (rgb_val, rgb_val, rgb_val // 2)
        np.show()
        
        # Show hour on display (only 1 digit visible)
        display.show(str(hour))
        
        sleep(1000)

solar_cycle()
```

### ESP32
```python
from lib import HardwareESP32, DisplayManager
import time

# Setup (much simpler!)
hw = HardwareESP32()
dm = DisplayManager(hw.lcd)

def solar_cycle():
    for hour in range(6, 19):  # 6 AM to 6 PM
        sim_time = hour * 3600
        
        # Calculate sun position (0-180°)
        angle = (hour - 6) * 180 / 12
        
        # Calculate intensity (parabolic curve)
        intensity = int(100 * (1 - ((hour - 12) / 6) ** 2))
        
        # Update hardware (same logic, cleaner API)
        hw.set_servo1_angle(angle)
        
        # Set panel color
        rgb_val = int(50 * intensity / 100)  # Scaled for safety
        hw.fill_panel(rgb_val, rgb_val, rgb_val // 2)
        
        # Show full status on LCD
        dm.display_status(
            sim_time=sim_time,
            sim_speed=60.0,
            intensity=intensity,
            autoload=True
        )
        # LCD shows: "06:00:00 x60"  ← Full time!
        #            "I: 50% AL:ON"   ← Full status!
        
        time.sleep(1)

solar_cycle()
```

---

## Import Replacements

### Remove These (RP2040)
```python
from microbit import *
from microbit import display, button_a, button_b, pin0, pin15
import machine  # For GPIO/PWM only, not I2C
```

### Add These (ESP32)
```python
from lib import HardwareESP32, DisplayManager
import time  # Use time instead of sleep
import gc    # For memory management
```

---

## Gotchas and Tips

### Timing
- RP2040: `sleep(ms)` in milliseconds
- ESP32: `time.sleep(seconds)` or `time.sleep_ms(ms)`

### PWM Duty Cycle
- RP2040: `duty_u16(0-65535)` for 16-bit PWM
- ESP32: Same! `duty_u16(0-65535)` also 16-bit

### Memory Management
```python
# Add this periodically in long-running loops
import gc
gc.collect()  # Free unused memory

# Check free memory
print(f"Free: {gc.mem_free() // 1024}KB")
```

### I2C Bus
- RP2040: Built-in to microbit module
- ESP32: Use `machine.I2C(0, scl=Pin(22), sda=Pin(21))`
  - But `HardwareESP32` already handles this!

### NeoPixel Updates
```python
# Both platforms: write() or show() after changes
hw.pixels[0] = (255, 0, 0)
hw.pixels.write()  # ESP32

np[0] = (255, 0, 0)
np.show()  # RP2040
```

---

## Summary: Key Differences

| Feature | RP2040 | ESP32 |
|---------|--------|-------|
| **Display** | 5×5 LED Matrix (25 pixels) | 16×2 LCD (32 chars) |
| **Usable Info** | 1 character/image | Full sentences |
| **Setup Code** | Manual pin/PWM setup | One `HardwareESP32()` call |
| **Pin Names** | `GP0`, `GP6`, `pin15` | `GPIO0`, `GPIO32`, `GPIO16` |
| **Sleep** | `sleep(ms)` | `time.sleep_ms(ms)` |
| **Servo Control** | Manual PWM calculation | `hw.set_servo1_angle(90)` |
| **NeoPixel Write** | `np.show()` | `hw.pixels.write()` |
| **Button Check** | `button_a.is_pressed()` | `hw.button_a_pressed()` |

---

## Migration Checklist

When porting a function from RP2040 to ESP32:

- [ ] Replace `display.*` calls with `dm.*` calls
- [ ] Replace manual servo PWM with `hw.set_servo*_angle()`
- [ ] Replace `pin15` NeoPixel with `hw.pixels`
- [ ] Replace `button_a.is_pressed()` with `hw.button_a_pressed()`
- [ ] Replace `sleep(ms)` with `time.sleep_ms(ms)`
- [ ] Update pin numbers (GP → GPIO, check PIN_MAPPING.md)
- [ ] Add `gc.collect()` in long loops
- [ ] Test each function independently before integration

---

**Next:** Use this guide when porting `SolarSimulator.py` → `solarsim_esp32.py`
