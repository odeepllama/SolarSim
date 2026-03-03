# SolaSim Studio — Project Overview

Solar simulation hardware control system with two firmware targets and two web interfaces.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Web Interfaces                        │
│                                                          │
│  SolaSimStudio.html          SolaSimStudioBLE.html       │
│  (USB — Web Serial API)      (iPad — Web Bluetooth API)  │
│  Desktop Chrome/Edge/Opera   Bluefy browser on iPad      │
│  RP2040 + ESP32 support      ESP32-only                  │
└──────────┬───────────────────────────────┬───────────────┘
           │ USB Serial                    │ BLE (NUS)
┌──────────▼──────────┐      ┌─────────────▼──────────────┐
│  ESP32-S3 Firmware  │      │  ESP32-S3 BLE Firmware     │
│  (ESP32/) │      │  (BLE_iPad/)               │
│  USB + BLE capable  │      │  BLE-optimised, debounced  │
└─────────────────────┘      └────────────────────────────┘
┌─────────────────────┐
│  RP2040 Firmware    │
│  (RP2040/)          │
│  USB-only, single   │
│  monolithic file    │
└─────────────────────┘
```

## Web Interfaces

| File | Transport | Deploy URL | Use Case |
|------|-----------|------------|----------|
| `SolaSimStudio.html` | USB (Web Serial) | `/SolarSim/` | Desktop browser to RP2040 or ESP32 via cable |
| `SolaSimStudioBLE.html` | BLE (Web Bluetooth) | `/SolarSim/Bt/` | iPad/tablet to ESP32 wirelessly via Bluefy |

Both interfaces share the same feature set: status tiles, solar arc, command console, profile management, timeline, Quick Edit, and print summary. The BLE variant has BLE-specific tuning (status debounce, retry spacing, no USB button).

## Firmware Targets

### ESP32-S3 (MicroPython)

Supports both USB serial and BLE connections. Modular architecture split across multiple files.

### RP2040 (MicroPython)

USB serial only. Monolithic single-file design due to memory constraints on the RP2040 platform.

---

## Folder Structure

### `ESP32/` — ESP32 Firmware + Wired Web Interface

> **Note:** Folder name is a historical misnomer — this is the **wired USB** variant. The HTML file connects via Web Serial, not Bluetooth.

| File | Purpose |
|------|---------|
| `SolaSimStudio.html` | Web interface (USB via Web Serial API) |
| `main.py` | Entry point — initialises hardware and simulator |
| `simulator.py` | Core simulation engine: solar calculations, command processing, main loop |
| `hardware.py` | Hardware abstraction: servos, NeoPixels, OLED, buttons |
| `program_engine.py` | Multi-step program sequencer with repeats, transitions, profiles |
| `ble_comms.py` | BLE GATT server (NUS) — present but not used by the wired HTML |
| `ssd1306.py` | SSD1306 OLED display driver |
| `boot.py` | MicroPython boot configuration |
| `rainbow_forward_reverse.txt` | Example multi-day program profile |
| `planty.svg` / `planty_b&w.svg` | Logo assets for the web interface |
| `ESP32_GENERIC_S3-*.bin` | MicroPython firmware binary for flashing |

### `BLE_iPad/` — ESP32 BLE Firmware + BLE Web Interface

Optimised for iPad use over Bluetooth Low Energy. Key differences from `ESP32/`:
- `main.py` initialises BLE **before** large imports (prevents heap fragmentation)
- `simulator.py` has BLE-specific status debouncing and output throttling
- HTML has wider retry delays, fresh-connect handling, no USB button

| File | Purpose |
|------|---------|
| `SolaSimStudioBLE.html` | Web interface (BLE via Web Bluetooth API) |
| `main.py` | Entry point — BLE-first init order to prevent bootloops |
| `simulator.py` | Core engine with BLE status debounce (3s) and output throttle |
| `hardware.py` | Hardware abstraction (shared with ESP32) |
| `program_engine.py` | Program sequencer (shared with ESP32) |
| `ble_comms.py` | BLE GATT server — NUS service, 512-byte MTU, chunked sends |
| `ssd1306.py` | SSD1306 OLED display driver |
| `boot.py` | MicroPython boot configuration |
| `rainbow_forward_reverse.txt` | Example multi-day program profile |
| `planty.svg` / `planty_b&w.svg` | Logo assets for the web interface |

### `RP2040/` — RP2040 Firmware

Single-file firmware for the RP2040:bit platform. No BLE support.

| File | Purpose |
|------|---------|
| `SolarSimulatorSun.py` | Monolithic firmware — all logic in one file |
| `main.py` | Entry point (imports and runs SolarSimulatorSun) |
| `main_app.mpy` | Pre-compiled bytecode version for faster startup |
| `RPI_PICO-*.uf2` | MicroPython firmware binary for flashing |

---

## Deployment

GitHub Actions (`.github/workflows/deploy-pages.yml`) auto-deploys on push:

| Branch | SolaSimStudio.html | SolaSimStudioBLE.html |
|--------|--------------------|-----------------------|
| `main` | `/` (production) | `/Bt/` (production) |
| other | `/test/` | `/Bt/test/` |

---

## Key Shared Features

- **Solar simulation**: BASIC (constant 6AM–6PM) and SCIENTIFIC (latitude/date-based astronomical) modes
- **Program engine**: Multi-step sequences with speed, intensity, sun color per step, hold/repeat, multi-day support
- **Rotation imaging**: 360° turntable with camera trigger servo, configurable speed presets, stills/video modes
- **Profile management**: Save/load/upload profiles, auto-load on startup, comparison and diff viewer
- **Status monitoring**: Real-time tiles, solar arc visualisation, timeline playhead with step/day navigation
- **Interactive tiles**: Click to adjust speed, intensity, time, sun color, toggle program/rotation/dual sun
- **Internationalisation**: English and Japanese UI with toggle button
