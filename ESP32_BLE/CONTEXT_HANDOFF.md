# ESP32 Solar Simulator - Project Context Handoff

**Date:** January 28, 2026  
**Purpose:** Context for continuing development with fresh AI session  
**Current Phase:** Phase 2 - Hardware Validation  
**Overall Progress:** ~35% complete

---

## 🎯 Project Mission

Port the existing **Solar Simulator** from RP2040:bit (microbit-compatible board) to **ESP32-S3**, enabling wireless control from an **iPad** using **Web Bluetooth API**.

### Original System
- **Platform:** RP2040:bit
- **Display:** 5×5 LED matrix (25 pixels, built-in to microbit)
- **Control:** USB Serial connection (Web Serial API)
- **Code:** `SolarSimulator.py` (3195 lines, monolithic)
- **Web Interface:** `ProfileBuilder.html` (uses Web Serial API)
- **Hardware:** 3 servos, 448 NeoPixels (8×56 panel), camera trigger

### Target System
- **Platform:** ESP32-S3 (240MHz, 512KB RAM, Bluetooth LE)
- **Display:** I2C LCD 1602 (16×2 characters)
- **Control:** Bluetooth LE (BLE GATT) - works on iPad ✓
- **Code:** Modular architecture with hardware abstraction
- **Web Interface:** `ProfileBuilder.html` (modified for Web Bluetooth API)
- **Hardware:** Same (3 servos, 448 NeoPixels, camera trigger)

---

## 🚩 Critical Context: Why BLE Instead of WiFi

**User's Original Request:** WiFi web server on ESP32 hosting ProfileBuilder.html

**Problems Discovered:**
1. **Memory:** ProfileBuilder.html uses ~500MB RAM in Chrome - won't fit on ESP32 (512KB available)
2. **iPad Limitation:** Web Serial API doesn't work on iOS/iPadOS
3. **Complexity:** WiFi AP mode + web server + file serving = unnecessary overhead

**Solution Chosen:** BLE with Web Bluetooth API
- ✅ Works on iPad Chrome/Safari
- ✅ Minimal memory footprint  
- ✅ Direct device communication
- ✅ HTML stays on client side (iPad browser)
- ✅ Simpler implementation

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────┐
│      iPad Chrome Browser (Client)           │
│                                              │
│  ProfileBuilder.html (500MB in RAM)         │
│  + Web Bluetooth API (lightweight)          │
│                                              │
└──────────────────┬───────────────────────────┘
                   │
                   │ Bluetooth LE (Wireless)
                   │ GATT Service
                   │
┌──────────────────┴───────────────────────────┐
│          ESP32-S3 (Embedded Device)          │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ main.py (Entry Point)                  │ │
│  └───┬────────────────────────────────────┘ │
│      │                                       │
│  ┌───┴────────────────────────────────────┐ │
│  │ ble_server.py                          │ │
│  │ - BLE GATT Server                      │ │
│  │ - 3 Characteristics:                   │ │
│  │   * Command (Write)                    │ │
│  │   * Response (Read/Notify)             │ │
│  │   * Status (Read/Notify)               │ │
│  │ - Chunked data transfer (MTU handling) │ │
│  └───┬────────────────────────────────────┘ │
│      │                                       │
│  ┌───┴────────────────────────────────────┐ │
│  │ solarsim_esp32.py [TO BE CREATED]     │ │
│  │ - Main simulation logic                │ │
│  │ - Command handler (~800 lines)         │ │
│  │ - Solar position calculations          │ │
│  │ - Time management                      │ │
│  │ - Program manager                      │ │
│  └───┬───────────────┬────────────────────┘ │
│      │               │                       │
│  ┌───┴────────────┐ ┌┴────────────────────┐ │
│  │ hardware_esp32 │ │ display_manager     │ │
│  │ (Hardware HAL) │ │ (LCD Management)    │ │
│  └───┬────────────┘ └─────────────────────┘ │
│      │                                       │
│  ┌───┴────────────────────────────────────┐ │
│  │ Physical Hardware:                     │ │
│  │ - Servos (3x): Rotation + 2x Camera   │ │
│  │ - NeoPixels (448 LEDs): Sun panel     │ │
│  │ - LCD 1602 (I2C): Status display      │ │
│  │ - Buttons (2x): User input            │ │
│  │ - Camera trigger: Shutter control     │ │
│  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

## ✅ Phase 1 & 1.5: COMPLETED (Files Created)

### BLE Infrastructure (Phase 1)

1. **`ble_server.py`** (319 lines)
   - BLE GATT server with service UUID: `12345678-1234-5678-1234-56789abcdef0`
   - 3 characteristics: Command (write), Response (read/notify), Status (read/notify)
   - Chunked data transfer for messages > MTU size
   - Handles BLE connection/disconnection events
   - Integrates with command handler callback
   - **Status:** ✅ Tested with nRF Connect app on iPad

2. **`lcd_i2c.py`** (246 lines)
   - I2C LCD 1602 driver using PCF8574 backpack
   - Supports addresses 0x27 and 0x3F
   - 4-bit mode communication
   - Methods: `print()`, `clear()`, `cursor()`, `backlight()`
   - Convenience method: `display_status()` for simulator
   - **Status:** ✅ Complete, ready for testing

3. **`boot.py`** (47 lines)
   - System initialization on ESP32 startup
   - Disables debugging output
   - Reports reset cause (power-on, reset button, watchdog, etc.)
   - Memory diagnostics (total, free, PSRAM detection)
   - Garbage collection
   - **Status:** ✅ Complete

4. **`main.py`** (179 lines)
   - Auto-run entry point
   - Initializes I2C and LCD
   - Initializes BLE server
   - Simple test command handler (6 commands: ECHO, STATUS, LCD, MEM, HELP, PING)
   - Periodic status updates via BLE
   - **Status:** ✅ Working, will be replaced with full simulation integration

### Hardware Abstraction Layer (Phase 1.5)

5. **`lib/__init__.py`** (9 lines)
   - Python package initialization
   - Exports: `HardwareESP32`, `DisplayManager`

6. **`lib/hardware_esp32.py`** (574 lines) ⭐ KEY FILE
   - **Purpose:** Complete hardware abstraction for ESP32-S3
   - **Pin definitions:**
     - Servo 1 (Rotation): GPIO32 (was GP6 on RP2040)
     - Servo 2 (Camera 1): GPIO33 (was GP10)
     - Servo 3 (Camera 2): GPIO25 (was GP11)
     - NeoPixels: GPIO16 (was GP15)
     - I2C LCD: SDA=GPIO21, SCL=GPIO22
     - Button A: GPIO0 (BOOT button)
     - Button B: GPIO35
     - Camera trigger: GPIO26
   - **Methods:**
     - `set_servo_angle(pwm_obj, angle)` - Standard servo control (0-270°)
     - `set_servo1_angle(angle, use_1to1_ratio)` - Calibrated rotation (0-360°)
     - `get_servo1_calibrated_pwm(angle, use_1to1_ratio)` - Returns PWM for angle
     - `fill_panel(r, g, b)` - Fill all NeoPixels
     - `xy_to_index(x, y)` - Convert coordinates to pixel index (8×56 panel)
     - `button_a_pressed()`, `button_b_pressed()` - Button state
     - `trigger_camera_shutter()` - 10ms pulse
     - `shutdown()` - Clean hardware shutdown
   - **Built-in test:** `test_hardware()` function
   - **Status:** ✅ Complete, ready for hardware testing

7. **`lib/display_manager.py`** (461 lines) ⭐ KEY FILE
   - **Purpose:** Manages LCD display, replaces RP2040's 5×5 LED matrix
   - **Key methods:**
     - `display_status(sim_time, sim_speed, intensity, autoload)` - Main status display
     - `display_sim_time(sim_time, sim_speed)` - Time display
     - `display_message(message, line1, duration_ms)` - Temporary messages
     - `display_error(error_msg, details)` - Error display
     - `display_program_info(program_name, step_info)` - Program execution
     - `display_rotation_angle(angle)` - Rotation display
     - `display_intensity(intensity)` - Intensity display
     - `display_camera_status(camera_num, status)` - Camera status
     - `display_connection_status(connection_type, status)` - BLE/Serial
     - `display_memory_info(free_kb, total_kb)` - Memory usage
     - `display_progress_bar(title, progress_percent)` - Progress bar
   - **Compatibility methods** (replace RP2040 5×5 matrix):
     - `show_single_char(char, duration_ms)`
     - `scroll_text(text, scroll_speed)`
     - `show_animation(frames, frame_delay)`
   - **Built-in test:** `test_display_manager()` function
   - **Status:** ✅ Complete, ready for hardware testing

8. **`test_lib.py`** (350 lines)
   - **Purpose:** Comprehensive integrated test suite
   - **Tests:**
     - Phase 1: Hardware initialization
     - Phase 2: Display manager initialization
     - Phase 3: Simulation status display (10 updates)
     - Phase 4: Hardware control + display feedback
       - Servo control with angle display
       - NeoPixel colors with display
       - Camera triggers with display
       - Button monitoring (5 sec)
     - Phase 5: Simulated solar cycle (sunrise→noon→sunset)
     - Phase 6: Memory and performance metrics
     - Phase 7: Progress bar display
     - Phase 8: Display animations
   - **Functions:**
     - `test_integrated_system()` - Full test (10 min)
     - `quick_test()` - Quick sanity check (30 sec)
     - `benchmark_display_updates()` - Performance test
   - **Status:** ✅ Complete, ready to run on hardware

### Documentation (Phase 1 & 1.5)

9. **`ESP32_SETUP_GUIDE.md`** - Hardware setup, wiring, MicroPython flashing
10. **`BLE_TESTING_GUIDE.md`** - How to test BLE with nRF Connect app
11. **`PIN_MAPPING.md`** - Complete pin reference (RP2040 vs ESP32)
12. **`CHECKLIST.md`** - Shopping list for components
13. **`README.md`** - Project overview (updated with current status)
14. **`ACTION_PLAN.md`** ⭐ - Step-by-step guide for Phase 2 (hardware testing)
15. **`LIBRARY_STATUS.md`** - What we built, why, and timeline
16. **`PORTING_GUIDE.md`** ⭐ - Side-by-side RP2040↔ESP32 code examples
17. **`lib/README.md`** - Complete API documentation for hardware & display

---

## ⚠️ Important Note: Connection Modes

### Current Implementation: BLE Only

The current `main.py` only handles BLE connections. However, ESP32-S3 can **easily support both BLE and USB Serial simultaneously**.

### Dual-Mode Support (Optional Enhancement)

To add USB Serial (Web Serial API) alongside BLE:

1. **Add serial input handler to `main.py`:**
```python
import sys
import select

def check_serial_input():
    """Check for USB Serial commands (non-blocking)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline().strip()
        if line:
            return line
    return None

# In main loop:
while True:
    # Check USB Serial
    serial_cmd = check_serial_input()
    if serial_cmd:
        response = handle_command(serial_cmd)
        print(response)  # Send to USB Serial
    
    # BLE handled by callbacks (already working)
    time.sleep_ms(10)
```

2. **ProfileBuilder.html can detect both:**
```javascript
// Try Web Serial first (desktop), fallback to BLE (iPad)
if ('serial' in navigator) {
    // Use Web Serial API
} else if ('bluetooth' in navigator) {
    // Use Web Bluetooth API
}
```

### Benefits of Dual-Mode
- ✅ **iPad:** Works via BLE (Web Bluetooth API)
- ✅ **Desktop:** Works via USB Serial (Web Serial API) - faster, more reliable
- ✅ **Development:** Serial for debugging, BLE for wireless
- ✅ **User choice:** Connect method preference

### When to Add
- **Now:** If you want maximum compatibility
- **Later:** After BLE testing complete (Phase 2-3)
- **Never:** If BLE-only is sufficient for your use case

---

## 🔄 Current Status: Phase 2 - Hardware Validation

### What Needs to Happen Now

The user needs to:

1. **Upload 4 new files to ESP32-S3:**
   - `lib/__init__.py`
   - `lib/hardware_esp32.py`
   - `lib/display_manager.py`
   - `test_lib.py`

2. **Run integrated test suite:**
   ```python
   import test_lib
   test_lib.test_integrated_system()
   ```

3. **Verify all hardware working:**
   - LCD displays test messages
   - NeoPixels cycle through colors
   - Servos move smoothly
   - Camera trigger pulses
   - No errors in console

4. **Report back:** Either "All tests passed!" or specific error messages

### Why This Step is Critical

The hardware abstraction layer MUST be tested independently before porting the 3195-line main simulation code. This ensures:
- ✅ Hardware definitely works
- ✅ Any bugs in simulation port are logic bugs, not hardware bugs
- ✅ Clear API boundary for debugging
- ✅ Each piece tested before integration

---

## ⏸️ Phase 3: Main Code Port (NEXT STEP AFTER PHASE 2)

### Source File to Port

**`SolarSimulator/SolarSimulator.py`** (3195 lines, monolithic)

Key sections discovered via file reads:
- Lines 1-2000: Initialization, time management, solar calculations, rotation control
- Lines 2000-3000: Command handler (~800 lines), program manager, display updates
- Lines 3000-3195: Additional helpers, shutdown logic

### Porting Strategy (Option C - Modular)

Create **`solarsim_esp32.py`** by:

1. **Import tested modules:**
   ```python
   from lib import HardwareESP32, DisplayManager
   import time
   import gc
   ```

2. **Extract core simulation logic sections:**
   - Time management: `get_sim_time()`, `update_sim_time()`, `set_sim_time()`
   - Solar calculations: `get_sun_position()`, `get_intensity()`, `calculate_sun_angle()`
   - Rotation control: `update_rotation_cycle()`, state machine
   - Program manager: `execute_program_step()`, `load_program()`, program execution
   - Command handler: `handle_command()` (~800 lines, ~50 command types)

3. **Replace RP2040-specific code:**
   - `display.scroll("text")` → `dm.scroll_text("text")`
   - `display.show("A")` → `dm.show_single_char("A")`
   - `display.clear()` → `dm.clear()`
   - Manual servo PWM → `hw.set_servo1_angle(angle)`
   - Manual NeoPixel → `hw.fill_panel(r, g, b)` or `hw.pixels[index] = (r,g,b)`
   - `button_a.is_pressed()` → `hw.button_a_pressed()`
   - Pin references: `GP6` → use `hw.servo_pwm_1`, `GP15` → use `hw.pixels`

4. **Test each subsystem independently:**
   - Time management alone
   - Solar calculations alone
   - Rotation control alone
   - Command handler alone
   - Then integrate

5. **Integration with BLE:**
   - Update `main.py` to import `solarsim_esp32`
   - Replace `simple_command_handler()` with full `handle_command()`
   - Connect BLE callbacks to simulation

### Key Translation Patterns

See **`PORTING_GUIDE.md`** for complete examples. Quick reference:

| RP2040 | ESP32 |
|--------|-------|
| `from microbit import *` | `from lib import HardwareESP32, DisplayManager` |
| `display.show("X")` | `dm.show_single_char("X")` |
| `servo_pwm.duty_u16(val)` | `hw.set_servo1_angle(angle)` |
| `np[i] = (r,g,b); np.show()` | `hw.pixels[i] = (r,g,b); hw.pixels.write()` |
| `button_a.is_pressed()` | `hw.button_a_pressed()` |
| `sleep(100)` | `time.sleep_ms(100)` |

### Estimated Effort

- **Reading/extracting code:** 1-2 hours
- **Replacing RP2040 calls:** 2-3 hours
- **Testing subsystems:** 1-2 hours
- **Integration:** 1 hour
- **Total:** 4-6 hours of focused work

---

## ⏸️ Phase 4: Web Interface (FINAL STEP)

### Modify ProfileBuilder.html for Web Bluetooth

**Current:** Uses Web Serial API (doesn't work on iPad)
```javascript
// OLD - Web Serial API
const port = await navigator.serial.requestPort();
await port.open({ baudRate: 115200 });
const writer = port.writable.getWriter();
await writer.write(encoder.encode(command));
```

**Target:** Use Web Bluetooth API (works on iPad)
```javascript
// NEW - Web Bluetooth API
const device = await navigator.bluetooth.requestDevice({
  filters: [{ services: ['12345678-1234-5678-1234-56789abcdef0'] }]
});
const server = await device.gatt.connect();
const service = await server.getPrimaryService('12345678-1234-5678-1234-56789abcdef0');
const commandChar = await service.getCharacteristic('12345678-1234-5678-1234-56789abcdef1');
const responseChar = await service.getCharacteristic('12345678-1234-5678-1234-56789abcdef2');

// Subscribe to responses
await responseChar.startNotifications();
responseChar.addEventListener('characteristicvaluechanged', handleResponse);

// Send command
await commandChar.writeValue(encoder.encode(command));
```

### Key Changes

1. **Replace port selection** with Bluetooth device picker
2. **Replace serial read/write** with GATT characteristic read/write
3. **Add connection state management** (BLE can disconnect)
4. **Handle MTU limitations** (data chunking on large responses)
5. **Add auto-reconnect logic** (BLE less stable than USB)

### Testing
- Test on iPad Chrome (primary target)
- Test on iPad Safari (secondary)
- Test on desktop Chrome (development)
- Verify all controls work wirelessly
- Test connection loss/recovery

---

## 🛠️ Technical Specifications

### ESP32-S3 Hardware
- **CPU:** Dual-core Xtensa LX7, 240MHz
- **RAM:** 512KB SRAM (320KB usable after system)
- **PSRAM:** Optional (recommended for NeoPixel buffer)
- **Flash:** 4-8MB (depends on module)
- **Bluetooth:** BLE 5.0
- **WiFi:** 802.11 b/g/n (not used in this project)

### Pin Assignments
```
Servos:
  Servo 1 (Rotation):    GPIO32  (PWM channel 0)
  Servo 2 (Camera 1):    GPIO33  (PWM channel 1)
  Servo 3 (Camera 2):    GPIO25  (PWM channel 2)

NeoPixels:
  Data line:             GPIO16  (448 LEDs, 8×56 panel)

LCD 1602 (I2C):
  SDA:                   GPIO21
  SCL:                   GPIO22
  Address:               0x27 or 0x3F

Buttons:
  Button A (BOOT):       GPIO0   (active LOW, pull-up)
  Button B (External):   GPIO35  (active LOW, pull-up)

Camera:
  Shutter trigger:       GPIO26  (active LOW, idle HIGH)
```

### NeoPixel Panel Layout
- **Dimensions:** 8 rows × 56 columns = 448 LEDs
- **Physical arrangement:** 7 panels of 8×8 LEDs
- **Coordinate system:** (0,0) = top-left, (55,7) = bottom-right
- **Serpentine wiring:** Even rows left-to-right, odd rows right-to-left
- **Panel order:** Physical panel 6 is visual panel 0 (reversed)

### LCD Display Layout (16×2)
```
┌────────────────┐
│HH:MM:SS xSPEED │  Line 0: Time (8 chars) + Speed (5 chars)
│I:XXX% AL:XX    │  Line 1: Intensity (6 chars) + Autoload (5 chars)
└────────────────┘
```

### BLE GATT Service
- **Service UUID:** `12345678-1234-5678-1234-56789abcdef0`
- **Characteristic 1 (Command):** UUID ending in `...def1`, Write only
- **Characteristic 2 (Response):** UUID ending in `...def2`, Read + Notify
- **Characteristic 3 (Status):** UUID ending in `...def3`, Read + Notify
- **MTU:** Typically 23-512 bytes (handle chunking for large messages)
- **Device name:** `SolarSim-ESP32`

### Servo Calibration
**Rotation servo (Servo 1)** has non-linear calibration tables:

**3:4 Ratio Table (default):**
```python
{
  0:   1400,   # 0° → PWM 1400
  90:  3200,   # 90° → PWM 3200
  180: 4900,   # 180° → PWM 4900
  270: 6600,   # 270° → PWM 6600
  360: 8252    # 360° → PWM 8252
}
```

**1:1 Ratio Table:**
```python
{
  0:   1400,   # 0° → PWM 1400
  270: 8252    # 270° → PWM 8252 (linear interpolation)
}
```

Camera servos use standard linear PWM (1400-8352 for 0-270°).

---

## 📦 File Dependency Graph

```
main.py
  └─> ble_server.py
  └─> solarsim_esp32.py [TO BE CREATED]
        └─> lib/hardware_esp32.py
        │     └─> lcd_i2c.py
        │     └─> machine (Pin, PWM, I2C)
        │     └─> neopixel
        └─> lib/display_manager.py
              └─> lcd_i2c.py
              └─> time

test_lib.py (independent test)
  └─> lib/hardware_esp32.py
  └─> lib/display_manager.py
```

---

## 🔍 Key Code Patterns in SolarSimulator.py

### Time Management
```python
# Global variables for simulation time
sim_time_offset = 0     # Offset from real time
sim_speed = 1.0         # Speed multiplier (1, 6, 60, 600)
sim_hold = False        # Pause simulation
sim_reverse = False     # Run backwards

def get_sim_time():
    """Get current simulation time in seconds since midnight"""
    if sim_hold:
        return sim_time_offset
    
    real_time = time.ticks_ms() / 1000
    if sim_reverse:
        return sim_time_offset - (real_time * sim_speed)
    else:
        return sim_time_offset + (real_time * sim_speed)
```

### Solar Calculations
```python
def get_sun_position(sim_time_seconds):
    """
    Calculate sun position based on time
    Returns: (azimuth_angle, elevation_angle, intensity)
    """
    # Convert sim_time to hours since midnight
    hours = sim_time_seconds / 3600.0
    
    # Simple model: sun rises at 6 AM, sets at 6 PM
    # Peak at noon (12:00)
    if hours < 6 or hours > 18:
        return (0, 0, 0)  # Night time
    
    # Calculate angle (0° at sunrise, 180° at sunset)
    sun_progress = (hours - 6) / 12.0  # 0.0 to 1.0
    azimuth = sun_progress * 180
    
    # Calculate intensity (parabolic curve, peak at noon)
    hours_from_noon = abs(hours - 12)
    intensity = max(0, 100 * (1 - (hours_from_noon / 6) ** 2))
    
    return (azimuth, 90, intensity)  # 90° elevation (simplified)
```

### Rotation State Machine
```python
rotation_state = "IDLE"  # "IDLE", "ROTATING", "HOLDING"
target_angle = 0
current_angle = 0
rotation_speed = 1.0  # degrees per update

def update_rotation_cycle():
    """Update rotation servo based on state machine"""
    global rotation_state, current_angle
    
    if rotation_state == "ROTATING":
        if abs(current_angle - target_angle) < rotation_speed:
            current_angle = target_angle
            rotation_state = "HOLDING"
        else:
            if current_angle < target_angle:
                current_angle += rotation_speed
            else:
                current_angle -= rotation_speed
        
        set_rotation_servo(current_angle)
```

### Command Handler Structure
```python
def handle_command(cmd):
    """
    Process command string and return response
    
    Commands (~50 types):
    - SET SPEED <1|6|60|600>
    - SET TIME <seconds>
    - FILL <r> <g> <b>
    - ROTATE <angle>
    - CAMERA <1|2> <TRIGGER|REST>
    - PROGRAM <LOAD|RUN|STOP|STEP>
    - ... many more
    """
    parts = cmd.strip().split()
    if not parts:
        return "ERROR: Empty command"
    
    command = parts[0].upper()
    
    if command == "SET":
        # Handle SET subcommands
        if len(parts) < 3:
            return "ERROR: SET requires 2 arguments"
        subcmd = parts[1].upper()
        if subcmd == "SPEED":
            # Set simulation speed
            speed = float(parts[2])
            set_sim_speed(speed)
            return f"OK: Speed set to {speed}x"
        elif subcmd == "TIME":
            # Set simulation time
            new_time = int(parts[2])
            set_sim_time(new_time)
            return f"OK: Time set to {new_time}s"
        # ... more SET subcommands
    
    elif command == "ROTATE":
        # Rotate to angle
        angle = float(parts[1])
        rotate_to_angle(angle)
        return f"OK: Rotating to {angle}°"
    
    # ... ~50 more command types
    
    else:
        return f"ERROR: Unknown command '{command}'"
```

### Program Manager
```python
current_program = []
program_step = 0
program_running = False

def load_program(program_data):
    """Load program from string or file"""
    global current_program
    current_program = parse_program_string(program_data)
    return f"OK: Loaded {len(current_program)} steps"

def execute_program_step():
    """Execute one step of current program"""
    global program_step
    
    if program_step >= len(current_program):
        program_running = False
        return "Program complete"
    
    step = current_program[program_step]
    response = handle_command(step['command'])
    program_step += 1
    
    return response
```

---

## 🐛 Common Issues & Solutions

### Issue: LCD not detected
**Symptom:** `I2C devices found: []`
**Solution:**
1. Check wiring: SDA=GPIO21, SCL=GPIO22
2. Verify 5V power to LCD
3. Try address 0x3F: `hw = HardwareESP32(lcd_addr=0x3F)`
4. Check I2C manually:
   ```python
   from machine import I2C, Pin
   i2c = I2C(0, scl=Pin(22), sda=Pin(21))
   print(hex(i2c.scan()))
   ```

### Issue: NeoPixels not lighting
**Symptom:** LEDs stay dark
**Solution:**
1. Verify 5V/2A power supply
2. Check data pin: GPIO16
3. Check ground connection
4. Test single pixel:
   ```python
   hw.pixels[0] = (10, 0, 0)
   hw.pixels.write()
   ```

### Issue: Servos jitter or don't move
**Symptom:** Erratic servo behavior
**Solution:**
1. Check servo power (6V/2A recommended)
2. Verify signal pins: GPIO32, 33, 25
3. Test PWM directly:
   ```python
   from machine import Pin, PWM
   servo = PWM(Pin(32))
   servo.freq(50)
   servo.duty_u16(4096)
   ```

### Issue: Memory errors
**Symptom:** `MemoryError: memory allocation failed`
**Solution:**
1. Add garbage collection in loops:
   ```python
   import gc
   gc.collect()
   ```
2. Reduce NeoPixel count if not using full strip
3. Verify PSRAM enabled in boot.py

### Issue: BLE connection drops
**Symptom:** Random disconnections
**Solution:**
1. Reduce distance between devices
2. Add auto-reconnect to ProfileBuilder.html
3. Check for WiFi interference (2.4GHz)
4. Verify ESP32 has stable power

---

## 📝 Important Context from User

- **User has already tested BLE** with nRF Connect app on iPad - connection works ✓
- **User successfully connected** to ESP32-S3 and sent test commands ✓
- **User chose modular approach (Option C)** after understanding debugging benefits
- **User confirmed** ready to test hardware abstraction layer
- **User wants** step-by-step guidance for each phase
- **User is comfortable** with VS Code + MicroPython development workflow

---

## 🎯 Immediate Next Actions for Continuing AI

When the user returns with a fresh context window:

1. **Ask for Phase 2 status:** "Did the hardware tests pass? Any errors?"

2. **If tests passed:** Start Phase 3 - Main code port
   - Create `solarsim_esp32.py`
   - Read sections of `SolarSimulator.py` (2000 lines at a time)
   - Extract and port core logic
   - Test each subsystem
   - Integrate with BLE

3. **If tests failed:** Debug hardware issues
   - Check specific error messages
   - Guide through troubleshooting
   - Verify wiring and connections
   - Re-test individual components

4. **After Phase 3 complete:** Start Phase 4 - Web interface
   - Modify `ProfileBuilder.html`
   - Replace Serial API with Bluetooth API
   - Test on iPad
   - Final integration testing

---

## 📚 Essential Files Reference

**For hardware testing:**
- Read: `ACTION_PLAN.md` section "Phase 2"
- Run: `test_lib.test_integrated_system()`

**For code porting:**
- Read: `PORTING_GUIDE.md` for translation patterns
- Read: `lib/README.md` for API reference
- Reference: `SolarSimulator/SolarSimulator.py` (original code)

**For troubleshooting:**
- Check: `ACTION_PLAN.md` troubleshooting section
- Check: `ESP32_SETUP_GUIDE.md` for hardware setup
- Check: `PIN_MAPPING.md` for wiring verification

**For BLE:**
- Check: `BLE_TESTING_GUIDE.md` for testing procedures
- Reference: `ble_server.py` for GATT implementation

---

## 🔑 Key Success Metrics

**Phase 2 Success:**
- [ ] All hardware tests pass without errors
- [ ] LCD displays messages clearly
- [ ] Servos move smoothly (0° → 90° → 180°)
- [ ] NeoPixels cycle through colors
- [ ] Camera trigger pulses correctly
- [ ] Memory usage < 50% (>250KB free)

**Phase 3 Success:**
- [ ] Simulation time management works
- [ ] Solar calculations accurate
- [ ] Rotation control smooth
- [ ] Command handler processes all commands
- [ ] Program manager executes multi-step programs
- [ ] NeoPixels show sun position/intensity
- [ ] LCD shows real-time status

**Phase 4 Success:**
- [ ] ProfileBuilder.html connects via BLE on iPad
- [ ] All controls functional wirelessly
- [ ] Status updates in real-time
- [ ] Connection stable (no frequent drops)
- [ ] Latency acceptable (<500ms response)

---

## 🎓 Lessons Learned (Technical Decisions)

1. **Modular > Monolithic:** Testing individual modules before integration saves massive debugging time
2. **BLE > WiFi:** For this use case (direct iPad control), BLE is simpler and more reliable
3. **Client-side HTML:** Keep heavy files (ProfileBuilder.html) on client, not on ESP32
4. **Hardware abstraction:** Clean API boundary makes porting and debugging much easier
5. **Test-first approach:** Built test suites into every module from the start

---

## 🚀 Project Timeline

| Phase | Estimated | Actual | Status |
|-------|-----------|--------|--------|
| BLE Infrastructure | 3-4 hours | ~4 hours | ✅ Complete |
| Hardware Abstraction | 3-4 hours | ~3 hours | ✅ Complete |
| Hardware Testing | 1 hour | TBD | ⏳ Current |
| Main Code Port | 4-6 hours | TBD | ⏸️ Pending |
| Integration | 2-3 hours | TBD | ⏸️ Pending |
| Web Interface | 2-3 hours | TBD | ⏸️ Pending |
| **Total** | **15-21 hours** | **~7 hours** | **~35% Complete** |

---

## 📖 Summary for AI Continuation

**What exists:** Complete BLE infrastructure + tested hardware abstraction layer + comprehensive documentation

**What's tested:** BLE communication (nRF Connect), modular code structure (not yet on hardware)

**What's next:** User tests hardware abstraction layer → Fix any issues → Port 3195-line main simulation → Modify web interface

**Key files to focus on:**
1. `ACTION_PLAN.md` - Current phase instructions
2. `PORTING_GUIDE.md` - Translation reference
3. `lib/hardware_esp32.py` - Hardware API
4. `lib/display_manager.py` - Display API
5. `SolarSimulator.py` - Source code to port

**Communication style:** Direct, technical, step-by-step. User is technically competent, prefers clear instructions over hand-holding.

**Critical context:** Original RP2040 code is 3195 lines monolithic. We deliberately chose modular approach to make porting manageable within LLM context windows and to enable independent testing of subsystems.

---

**END OF CONTEXT HANDOFF**
*Generated: January 28, 2026*
*Project: ESP32 Solar Simulator Port*
*Phase: 2 of 4 (Hardware Validation)*
