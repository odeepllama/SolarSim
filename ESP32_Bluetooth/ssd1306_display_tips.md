# SSD1306 Display — ESP32-S3 Integration Guide

Self-contained reference for merging SSD1306 OLED support into the main branch.

---

## 1. Files Required

| File | Role |
|------|------|
| `ssd1306.py` | MicroPython I2C driver (from micropython-lib, MIT). Copy as-is to device. |
| `hardware.py` | Contains the `Display` class wrapper + I2C pin config |
| `simulator.py` | Contains the `show_dashboard()` call site in the main loop |

---

## 2. Pin Assignments (in `hardware.py`)

```python
I2C_SDA_PIN = 6
I2C_SCL_PIN = 7
I2C_FREQ = 400000
```

---

## 3. Boot / Init Order (Critical)

The display **must** initialize after BLE and NeoPixels. Current `main.py` order:

```
1. gc.collect()
2. Import modules (Hardware, BLEComms, SolarSimulator)
3. BLEComms()         ← BLE heap allocated FIRST (cleanest memory)
4. gc.collect()
5. Hardware()         ← Display is LAST item inside Hardware.__init__:
                         a. Servos
                         b. NeoPixels (two ~1.3 KB buffers)
                         c. I2C bus init
                         d. Display(i2c) — lazy-imports ssd1306 only if scan finds device
6. gc.collect()
7. SolarSimulator()   ← references hw.display safely
```

---

## 4. Display Class (in `hardware.py`, lines 76–233)

Key design points:
- **Stub by default**: `Display()` with no `i2c` arg → all methods are safe no-ops
- **Lazy import**: `from ssd1306 import SSD1306_I2C` only inside `Display.__init__` when I2C scan finds `0x3C` or `0x3D`
- **Auto-disable on error**: `show_dashboard()` sets `self._available = False` on any exception
- **Throttled updates**: Max 1/sec, skips if data unchanged (hash comparison)
- **Dashboard layout**: Time (3x font) + speed bar (right column) + intensity/step (2x font)

---

## 5. Main Loop Call Site (in `simulator.py`, line ~1092)

Called once per second inside the periodic update block:

```python
# Update OLED dashboard
step_cur = self.program.current_step + 1 if self.program.program_running else 0
step_total = len(self.program.program_steps) if self.program.program_running else 0
self.hw.display.show_dashboard(h, m, TIME_SCALE, INTENSITY_SCALE, step_cur, step_total)
```

---

## 6. Crash Root Causes (Historical)

1. **Memory pressure** — SSD1306 framebuffer (1 KB) + module load on top of BLE + two NeoPixel buffers pushes heap into fragmentation/OOM territory.
2. **I2C bus hangs** — `i2c.scan()` can block if SDA held low, causing timeouts that interfere with BLE timing.
3. **`framebuf` + BLE contention** — `SSD1306.show()` blocking I2C writes starve the BLE event loop.
4. **CPU-heavy text scaling** — `_text_scaled()` loops pixel-by-pixel (`8 × 8 × scale²` per char), blocking the event loop.

---

## 7. Safety Checklist

- [ ] **Lazy-load** `ssd1306` only after BLE is confirmed stable (not during `Hardware.__init__`)
- [ ] **Reduce update frequency** to every 2–3 seconds minimum
- [ ] **Run `gc.collect()`** before and after display init
- [ ] **Guard I2C scan** with a short timeout or skip scan entirely if display address is known
- [ ] **Avoid `_text_scaled`** during active BLE traffic — use 1x font or pre-rendered bitmaps instead
- [ ] **Add `gc.collect()` before I2C/Display block** in `Hardware.__init__` (not yet present)
