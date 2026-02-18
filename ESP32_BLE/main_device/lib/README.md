"""
ESP32-S3 Solar Simulator Hardware Library
==========================================

This library provides hardware abstraction and display management for the
ESP32-S3 Solar Simulator, making it easy to port code from the RP2040:bit
platform.

## Library Components

### 1. hardware_esp32.py
Hardware abstraction layer that manages:
- **Servo motors** (3x) - Platform rotation and camera triggers
- **NeoPixel panel** (448 LEDs) - Sun simulation display
- **I2C LCD 1602** (16x2 chars) - Status display
- **Buttons** (2x) - User input
- **Camera trigger** - Shutter control pin

### 2. display_manager.py
Display management that replaces RP2040's 5x5 LED matrix:
- Status displays (sim time, speed, intensity, autoload)
- Messages and errors
- Progress bars and animations
- Scrolling text
- Connection status

## Quick Start

### Basic Usage

```python
from lib import HardwareESP32, DisplayManager

# Initialize hardware
hw = HardwareESP32(neopixel_count=448)

# Initialize display manager
dm = DisplayManager(hw.lcd)

# Display welcome message
dm.display_welcome()

# Control servos
hw.set_servo1_angle(90)  # Rotate table to 90°
hw.set_servo_angle(hw.servo_pwm_2, 45)  # Camera servo to 45°

# Control NeoPixels
hw.fill_panel(50, 25, 0)  # Orange glow

# Update status display
dm.display_status(
    sim_time=43200,    # Noon (12:00)
    sim_speed=60.0,    # 60x speed
    intensity=75,      # 75% brightness
    autoload=True      # Autoload enabled
)

# Cleanup on exit
hw.shutdown()
dm.clear()
```

### Testing

```python
# Test hardware only
from lib.hardware_esp32 import test_hardware
test_hardware()

# Test display manager only
from lib.display_manager import test_display_manager
test_display_manager()

# Test integrated system
import test_lib
test_lib.test_integrated_system()

# Quick sanity check
test_lib.quick_test()

# Performance benchmark
test_lib.benchmark_display_updates()
```

## Hardware Class API

### Initialization

```python
hw = HardwareESP32(
    neopixel_count=448,  # Number of LEDs
    lcd_addr=0x27        # I2C address (0x27 or 0x3F)
)
```

### Servo Control

```python
# Standard servo control (0-270°)
hw.set_servo_angle(hw.servo_pwm_1, angle)
hw.set_servo_angle(hw.servo_pwm_2, angle)
hw.set_servo_angle(hw.servo_pwm_3, angle)

# Calibrated rotation table control (0-360°)
hw.set_servo1_angle(angle, use_1to1_ratio=False)

# Get calibrated PWM value
pwm = hw.get_servo1_calibrated_pwm(angle, use_1to1_ratio=False)
```

### NeoPixel Control

```python
# Fill entire panel
hw.fill_panel(r, g, b)  # r, g, b = 0-255

# Convert coordinates to pixel index
index = hw.xy_to_index(x, y)  # x: 0-55, y: 0-7

# Direct pixel access
hw.pixels[index] = (r, g, b)
hw.pixels.write()

# Delta update buffer
hw.panel_buffer[index]  # Get cached color
```

### Button Input

```python
if hw.button_a_pressed():
    print("Button A pressed!")

if hw.button_b_pressed():
    print("Button B pressed!")
```

### Camera Control

```python
# Trigger camera shutter (10ms pulse)
hw.trigger_camera_shutter()
```

### Cleanup

```python
hw.shutdown()  # Turn off LEDs, return servos to rest, clear LCD
```

## Display Manager API

### Initialization

```python
dm = DisplayManager(lcd)  # Pass LCD1602 instance or None
```

### Status Display

```python
# Full status display (replaces 5x5 matrix)
dm.display_status(
    sim_time=43200,    # Seconds since midnight
    sim_speed=60.0,    # Speed multiplier
    intensity=75,      # 0-100%
    autoload=True      # Boolean
)

# Simple time display
dm.display_sim_time(43200, sim_speed=60.0)
```

### Messages

```python
# Temporary message
dm.display_message("Hello World", "Line 2", duration_ms=2000)

# Error message
dm.display_error("Error name", "details")

# Clear message and return to previous mode
dm.clear_message()
```

### Specialized Displays

```python
# Program execution info
dm.display_program_info("Program Name", "Step 3/10")

# Rotation angle
dm.display_rotation_angle(90.5)

# Light intensity
dm.display_intensity(75)

# Camera status
dm.display_camera_status(camera_num=1, status="Ready")

# Servo position
dm.display_servo_position("Table", angle=90.0)

# Connection status
dm.display_connection_status("BLE", "Connected")

# Memory info
dm.display_memory_info(free_kb=256, total_kb=512)

# Progress bar
dm.display_progress_bar("Loading", progress_percent=75)
```

### Compatibility Methods (Replace RP2040 5x5 Matrix)

```python
# Show single character
dm.show_single_char('A', duration_ms=1000)

# Scroll text
dm.scroll_text("Hello World", scroll_speed=300)

# Show animation frames
frames = [
    ("Frame 1", "Line 2"),
    ("Frame 2", "Line 2"),
]
dm.show_animation(frames, frame_delay=200)
```

### Display Control

```python
# Clear display
dm.clear()

# Set update throttle interval
dm.set_update_interval(200)  # ms between updates
```

## Pin Mapping

Defined in `hardware_esp32.py`:

```python
# Servos
SERVO_1_PIN = 32      # Platform rotation (was GP6)
SERVO_2_PIN = 33      # Camera 1 trigger (was GP10)
SERVO_3_PIN = 25      # Camera 2 trigger (was GP11)

# NeoPixels
NEOPIXEL_PIN = 16     # LED panel data (was GP15)

# I2C (LCD)
I2C_SDA_PIN = 21      # I2C data
I2C_SCL_PIN = 22      # I2C clock

# Buttons
BUTTON_A_PIN = 0      # BOOT button (was GP0)
BUTTON_B_PIN = 35     # External (was GP1)

# Camera
CAMERA_SHUTTER_PIN = 26  # Trigger (was GP14)
```

## Porting from RP2040

### Display Replacements

| RP2040 (5x5 Matrix) | ESP32 (LCD 1602) |
|---------------------|------------------|
| `display.show(Image(...))` | `dm.show_single_char(char)` |
| `display.scroll(text)` | `dm.scroll_text(text)` |
| `display.clear()` | `dm.clear()` |
| Custom matrix patterns | `dm.display_message(line0, line1)` |

### Pin Changes

Replace RP2040 GPIO pins:
- `machine.Pin(6)` → `SERVO_1_PIN` (32)
- `machine.Pin(10)` → `SERVO_2_PIN` (33)
- `machine.Pin(11)` → `SERVO_3_PIN` (25)
- `machine.Pin(15)` → `NEOPIXEL_PIN` (16)

### Button Input

Replace:
```python
# RP2040
button_a.is_pressed()

# ESP32
hw.button_a_pressed()
```

## File Structure

```
ESP32_BLE/
├── lib/
│   ├── __init__.py          # Package initialization
│   ├── hardware_esp32.py    # Hardware abstraction (574 lines)
│   └── display_manager.py   # Display management (461 lines)
├── test_lib.py              # Integrated test suite (350 lines)
├── ble_server.py            # BLE communication
├── lcd_i2c.py               # LCD driver
├── boot.py                  # System initialization
└── main.py                  # Entry point
```

## Memory Usage

Approximate RAM usage:
- `HardwareESP32` object: ~1-2 KB
- `DisplayManager` object: ~500 bytes
- NeoPixel buffer (448 LEDs): ~1.3 KB
- Total overhead: ~3-4 KB

Leaves ~250+ KB free for simulation code on ESP32-S3 with 512KB RAM.

## Error Handling

Both classes handle errors gracefully:
- LCD not found → `lcd_available = False`, no-op on display calls
- Servo control errors → Print warning, return `False`
- I2C errors → Print error, continue without LCD

Check availability:
```python
if hw.lcd_available:
    # LCD is working
    pass

if dm.lcd_available:
    # Display manager can actually display
    pass
```

## Performance Notes

1. **Display Updates**: Throttled to 200ms by default to avoid I2C bus saturation
   - Change with `dm.set_update_interval(ms)`
   - Force immediate update with `force=True` parameter

2. **NeoPixel Updates**: Fast, but `pixels.write()` blocks for ~1ms per 100 LEDs
   - Use delta updates via `panel_buffer` to minimize writes

3. **Servo Control**: Non-blocking, ~1ms per PWM update

## Troubleshooting

### LCD not found
```python
# Check I2C devices
from machine import I2C, Pin
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
print(i2c.scan())  # Should see [39] or [63] (0x27 or 0x3F)
```

### NeoPixels not working
- Check power supply (448 LEDs need 5V/2A+)
- Verify GPIO16 connection
- Test with single LED: `hw.pixels[0] = (10, 0, 0); hw.pixels.write()`

### Servo jitter
- Check servo power supply (6V/2A recommended)
- Verify PWM frequency: `hw.servo_pwm_1.freq()` should be 50

## Next Steps

1. **Run Tests**: Upload files and run `test_lib.py`
2. **Integrate**: Import `HardwareESP32` and `DisplayManager` in main code
3. **Port Code**: Replace RP2040-specific calls with library methods
4. **Test**: Verify each subsystem works before full integration

## License

Part of the Solar Simulator project. See main project LICENSE.

## Support

See main project documentation:
- `ESP32_SETUP_GUIDE.md` - Hardware setup
- `BLE_TESTING_GUIDE.md` - BLE testing
- `PIN_MAPPING.md` - Complete pin reference
"""
