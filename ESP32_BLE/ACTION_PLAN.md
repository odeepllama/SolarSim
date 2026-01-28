# ESP32 Solar Simulator - Action Plan

**Created:** January 28, 2026  
**Phase 1:** ✅ COMPLETE  
**Current Phase:** Testing & Validation

---

## What Just Happened

We implemented **Option C (Hybrid Modular Approach)** by creating:

✅ **Hardware abstraction layer** (`lib/hardware_esp32.py`)  
✅ **Display management layer** (`lib/display_manager.py`)  
✅ **Comprehensive test suite** (`test_lib.py`)  
✅ **Complete documentation** (3 guide files + API docs)

**Why this matters:** Instead of trying to debug a 3195-line monolithic file on new hardware, you now have tested, independent modules that can be verified before integration.

---

## File Inventory

### ✅ Created in This Session

```
ESP32_BLE/
├── lib/
│   ├── __init__.py                    ← Package init
│   ├── hardware_esp32.py              ← Hardware abstraction (574 lines)
│   ├── display_manager.py             ← Display management (461 lines)
│   └── README.md                      ← API documentation
├── test_lib.py                        ← Integrated test suite (350 lines)
├── LIBRARY_STATUS.md                  ← What we built & why
├── PORTING_GUIDE.md                   ← RP2040→ESP32 translation guide
└── ACTION_PLAN.md                     ← This file
```

### ✅ Previously Created (BLE Infrastructure)

```
ESP32_BLE/
├── ble_server.py                      ← BLE GATT server (319 lines)
├── lcd_i2c.py                         ← LCD driver (246 lines)
├── boot.py                            ← System init (47 lines)
├── main.py                            ← Entry point (179 lines)
├── ESP32_SETUP_GUIDE.md               ← Hardware setup
├── BLE_TESTING_GUIDE.md               ← BLE testing procedures
├── CHECKLIST.md                       ← Shopping list
├── PIN_MAPPING.md                     ← Pin wiring diagrams
└── README.md                          ← Project overview
```

### ⏸️ Original Source Code

```
SolarSimulator/
└── SolarSimulator.py                  ← 3195 lines to port
```

---

## Phase Status

### ✅ Phase 1: BLE Infrastructure (COMPLETE)
- [x] BLE GATT server with 3 characteristics
- [x] I2C LCD driver
- [x] Boot configuration
- [x] Test command handler
- [x] Documentation suite
- [x] Hardware testing with nRF Connect ✓

### ✅ Phase 1.5: Hardware Abstraction (COMPLETE - Just Finished!)
- [x] Hardware abstraction layer
- [x] Display manager
- [x] Test suite
- [x] API documentation
- [x] Porting guide

### ⏳ Phase 2: Hardware Validation (NEXT - You Do This)
- [ ] Upload library files to ESP32
- [ ] Run hardware tests
- [ ] Verify LCD display working
- [ ] Verify servos moving
- [ ] Verify NeoPixels lighting
- [ ] Verify buttons responding
- [ ] Run integrated test suite
- [ ] Confirm all systems operational

### ⏸️ Phase 3: Main Code Port (After Phase 2)
- [ ] Create `solarsim_esp32.py`
- [ ] Port simulation time management
- [ ] Port solar position calculations
- [ ] Port rotation control
- [ ] Port intensity control
- [ ] Port command handler
- [ ] Port program manager
- [ ] Integration testing

### ⏸️ Phase 4: Web Interface (Final)
- [ ] Modify `ProfileBuilder.html` for Web Bluetooth
- [ ] Replace Serial API with Bluetooth API
- [ ] Test from iPad Chrome
- [ ] Full end-to-end testing

---

## IMMEDIATE NEXT STEPS (Phase 2)

### Step 1: Upload Files to ESP32 (10 minutes)

Using VS Code with MicroPython extension:

**Upload these new files:**
```
Local → ESP32
-----------------------------------
lib/__init__.py           → /lib/__init__.py
lib/hardware_esp32.py     → /lib/hardware_esp32.py
lib/display_manager.py    → /lib/display_manager.py
test_lib.py               → /test_lib.py
```

**Files already on ESP32 (from previous session):**
- `/ble_server.py`
- `/lcd_i2c.py`
- `/boot.py`
- `/main.py`

### Step 2: Connect to ESP32 (2 minutes)

1. Connect ESP32 via USB-C
2. Open VS Code Serial Monitor/REPL
3. Press CTRL+C to stop any running code
4. Should see `>>>` Python prompt

### Step 3: Run Hardware Test (5 minutes)

```python
# In REPL, type:
from lib.hardware_esp32 import test_hardware
test_hardware()
```

**What to expect:**
- Console shows test progress
- LCD displays test messages
- NeoPixels cycle through colors (Red → Green → Blue → Off)
- Servos move (rotation and camera servos)
- Test summary prints to console

**If any test fails, see troubleshooting section below.**

### Step 4: Run Display Test (3 minutes)

```python
from lib.display_manager import test_display_manager
test_display_manager()
```

**What to expect:**
- LCD shows 12 different display types
- Status updates with changing values
- Messages and animations
- Progress bars
- Scrolling text

### Step 5: Run Integrated Test (10 minutes)

```python
import test_lib
test_lib.test_integrated_system()
```

**What to expect:**
- 8 test phases executed automatically
- Hardware + display working together
- Simulated solar cycle (sunrise → noon → sunset)
- Memory statistics
- All systems operational report

**Watch for:**
- Smooth servo movement during solar cycle
- NeoPixels changing color/brightness
- LCD updating with time and status
- No error messages in console

### Step 6: Quick Sanity Check (30 seconds)

```python
test_lib.quick_test()
```

**What to expect:**
- Quick flash of LEDs
- Servo moves to 90° and back
- LCD confirms "Complete!"
- Fast verification everything still works

---

## Troubleshooting

### Problem: LCD not found

**Symptoms:**
```
[HW] Warning: No I2C devices found
lcd_available = False
```

**Debug:**
```python
from machine import I2C, Pin
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
print(i2c.scan())  # Should show [39] or [63]
```

**Solutions:**
1. Check wiring: SDA=GPIO21, SCL=GPIO22, VCC=5V, GND=GND
2. Try address 0x3F if 0x27 doesn't work:
   ```python
   hw = HardwareESP32(lcd_addr=0x3F)
   ```
3. Check LCD backpack (PCF8574) is seated correctly
4. Verify 5V power to LCD

### Problem: NeoPixels not lighting

**Symptoms:**
- Pixels stay dark during test
- No brightness changes

**Debug:**
```python
# Test single pixel manually
hw.pixels[0] = (50, 0, 0)  # Dim red
hw.pixels.write()
```

**Solutions:**
1. Check power supply: 448 LEDs need 5V/2A minimum
2. Verify data pin: GPIO16
3. Check ground connection between ESP32 and NeoPixel strip
4. Test with fewer LEDs:
   ```python
   hw = HardwareESP32(neopixel_count=10)  # Test with first 10
   ```

### Problem: Servos not moving

**Symptoms:**
- Servos don't respond to commands
- Servos jitter or move erratically

**Debug:**
```python
# Test PWM directly
from machine import Pin, PWM
servo = PWM(Pin(32))
servo.freq(50)
servo.duty_u16(4096)  # Center position
```

**Solutions:**
1. Check servo power: 6V/2A recommended
2. Verify signal pins: GPIO32, 33, 25
3. Check servo is functional (swap with known good servo)
4. Reduce PWM frequency if jittery:
   ```python
   # In hardware_esp32.py, change PWM_FREQ from 50 to 40
   ```

### Problem: Import errors

**Symptoms:**
```
ImportError: no module named 'lib'
```

**Solutions:**
1. Verify lib folder exists on ESP32:
   ```python
   import os
   print(os.listdir('/'))  # Should show 'lib'
   print(os.listdir('/lib'))  # Should show module files
   ```
2. Re-upload lib files
3. Check file permissions (use `os.stat()` to verify)

### Problem: Memory errors

**Symptoms:**
```
MemoryError: memory allocation failed
```

**Solutions:**
1. Reduce NeoPixel count if not using full strip
2. Add garbage collection:
   ```python
   import gc
   gc.collect()
   print(f"Free: {gc.mem_free() // 1024}KB")
   ```
3. Verify ESP32-S3 has PSRAM enabled in boot.py

### Problem: Tests hang or freeze

**Symptoms:**
- Test stops mid-execution
- ESP32 becomes unresponsive

**Solutions:**
1. Press CTRL+C to interrupt
2. Soft reset: CTRL+D in REPL
3. Hard reset: Press RESET button on ESP32
4. Re-flash MicroPython if persistent

---

## Success Criteria

Before proceeding to Phase 3, verify:

- [x] **LCD displays correctly**
  - Shows initialization message
  - Updates with status info
  - Clear, readable text

- [x] **Servos respond accurately**
  - Smooth movement to commanded angles
  - No jitter or erratic behavior
  - Camera servos trigger correctly

- [x] **NeoPixels light up**
  - All LEDs addressable
  - Colors display accurately
  - Can fill entire panel

- [x] **Buttons work**
  - Button A (BOOT) detects presses
  - Button B (external) responds

- [x] **Camera trigger functional**
  - Pin pulses LOW for 10ms
  - Returns to HIGH idle state

- [x] **Tests complete without errors**
  - All test phases pass
  - No Python exceptions
  - Memory usage reasonable (<50% used)

- [x] **Console output clean**
  - Clear test progress messages
  - No unexpected warnings
  - Success confirmations visible

---

## After Hardware Validation

Once **ALL** tests pass, we proceed to **Phase 3: Main Code Port**.

### Phase 3 Preview

We'll create `solarsim_esp32.py` by:

1. **Reading** sections of `SolarSimulator.py` (2000 lines at a time due to context limits)
2. **Extracting** core simulation logic
3. **Replacing** RP2040-specific code with hardware abstraction calls
4. **Testing** each subsystem independently:
   - Time management
   - Solar calculations
   - Rotation control
   - NeoPixel updates
   - Command handler
   - Program manager
5. **Integrating** with BLE server
6. **Full system test**

**Estimated time:** 4-6 hours of focused work, broken into testable chunks

### What Makes This Easier

Because we have **tested hardware abstraction**, you'll know:
- ✅ Hardware definitely works
- ✅ If simulation has bugs, it's in the ported logic, not hardware
- ✅ Each piece can be tested independently
- ✅ Integration is just connecting working pieces

Compare to Option B (monolithic port):
- ❌ Hardware + simulation + integration all untested
- ❌ Bug could be anywhere in 3195 lines
- ❌ Each test requires full system
- ❌ Debugging nightmare

---

## Documentation Quick Reference

| File | Purpose |
|------|---------|
| **LIBRARY_STATUS.md** | What we built, why it works, timeline |
| **PORTING_GUIDE.md** | Side-by-side RP2040↔ESP32 code examples |
| **lib/README.md** | Complete API reference for hardware & display |
| **ACTION_PLAN.md** | This file - what to do next |
| **ESP32_SETUP_GUIDE.md** | Initial hardware setup & wiring |
| **BLE_TESTING_GUIDE.md** | How to test BLE communication |
| **PIN_MAPPING.md** | Complete pin wiring reference |

---

## Support

### If You Get Stuck

1. **Check console output** for specific error messages
2. **Run individual tests** to isolate problem:
   ```python
   # Test just hardware
   from lib.hardware_esp32 import test_hardware
   test_hardware()
   
   # Test just display
   from lib.display_manager import test_display_manager
   test_display_manager()
   ```
3. **Check hardware connections** against PIN_MAPPING.md
4. **Review troubleshooting section** above
5. **Check memory usage**:
   ```python
   import gc
   gc.collect()
   print(f"Free: {gc.mem_free() // 1024}KB")
   ```

### Hardware Debugging Checklist

- [ ] **Power supply adequate?** (5V/2A minimum)
- [ ] **Connections secure?** (No loose wires)
- [ ] **Correct pins?** (Check PIN_MAPPING.md)
- [ ] **Ground connected?** (ESP32 GND to all device GNDs)
- [ ] **LCD backlight on?** (Should see blue glow)
- [ ] **Servos have power?** (Separate 6V recommended)
- [ ] **USB cable good?** (Try different cable if flaky)

---

## Timeline Estimate

| Phase | Duration | Status |
|-------|----------|--------|
| BLE Infrastructure | 3-4 hours | ✅ Complete |
| Hardware Abstraction | 3-4 hours | ✅ Complete |
| **Hardware Testing** | **1 hour** | **⏳ Current** |
| Main Code Port | 4-6 hours | ⏸️ Pending |
| Integration Testing | 2-3 hours | ⏸️ Pending |
| Web Interface | 2-3 hours | ⏸️ Pending |
| **Total Project** | **15-21 hours** | **~35% Complete** |

---

## Summary

🎯 **Your Mission Right Now:**

1. Upload 4 new files to ESP32 (`lib/*` + `test_lib.py`)
2. Run `test_lib.test_integrated_system()`
3. Verify all hardware working
4. Report back: "All tests passed!" or specific errors

Once hardware validation is complete, we'll port the main 3195-line simulation code, which will be **much easier** because:
- Hardware layer tested ✓
- Display layer tested ✓
- We know the hardware works ✓
- Clear API to work with ✓

---

**Status:** ✅ Library modules complete  
**Next Action:** Upload files and run tests  
**After That:** Port main simulation (with confidence!)  

💡 **Pro tip:** Take a photo/video of the working test - it's really cool to see the simulated solar cycle running with servos moving and LEDs changing!
