# SolarSimulator — Claude Context

See also: parent `Coding/CLAUDE.md` for cross-platform and repo overview.

## What This Project Is

**SolaSim** — an open-source solar simulator for phototaxis research. LED panels on a
semi-circular arc recreate sunrise-to-sunset sequences. Browser UI controls the device
over USB Web Serial (Chrome/Edge/Opera only). Published at `odeepllama/SolarSim`.

## Key Files

| Path | Description |
|------|-------------|
| `SolaSimStudio.html` | Main web interface (Web Serial, no server needed) |
| `setup.html` | Browser-based firmware wizard (RP2040 only) |
| `RP2040/SolarSimulator.py` | Recommended firmware — single-file MicroPython |
| `RP2040/main.py` + `main_app.mpy` | Entry point + compiled app deployed to device |
| `ESP32/main.py` | Experimental ESP32-S3 firmware (modular) |
| `Profiles/` | Example experiment profiles |

## Firmware Targets

- **RP2040** (recommended) — RP2040:bit board, MicroPython v1.27.0, single-file deploy
- **ESP32-S3** (experimental) — modular MicroPython, flash via `esptool`

No Python venv needed — firmware runs on the microcontroller, not the host machine.

## Hardware Notes

- LED panels: NeoPixel/WS2812B seven 8×8 matrices
- Servos: 360° turntable + camera trigger
- Optional: SSD1306 OLED (ESP32 only), DS3231 RTC (SDA→pin 20, SCL→pin 19)
- 3D-printed parts: see Printables link in README

## Deployment

1. Flash `RP2040/RPI_PICO-...-v1.27.0.uf2` via BOOTSEL drag-and-drop
2. Copy `main.py` + `main_app.mpy` to device (Thonny or `mpremote`)
3. Open `SolaSimStudio.html` in Chrome and connect

## Sub-Project

`SelfDrivingPlant/` is a separate git repo nested here — see its own CLAUDE.md.
Do not run git operations on both machines simultaneously (`.git` is on Google Drive).
