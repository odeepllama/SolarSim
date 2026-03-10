# 🌞 SolaSim — Open-Source Solar Simulator

<p align="center">
  <img src="SolaSim%20logo.png" alt="SolaSim Logo" width="300">
</p>

**SolaSim** is an open-source solar simulator for plant biology research. It uses LED panels and servo-driven sun tracking to recreate realistic daylight cycles — from simple sunrise-to-sunset sequences to multi-day scientific simulations based on real latitude and date.

Built with MicroPython firmware and browser-based control interfaces, it's designed to be affordable, reproducible, and accessible to researchers and educators.

> 🧪 Developed at [Akita International University](https://web.aiu.ac.jp/en/) for photobiology and plant science experiments.

---

## ✨ Key Features

- **Solar Simulation Modes** — BASIC (fixed 6 AM–6 PM) and SCIENTIFIC (astronomical calculations from latitude/date)
- **Multi-Step Programs** — Sequences with per-step speed, intensity, sun colour, hold/repeat, and multi-day support
- **360° Rotation Imaging** — Servo-driven turntable with camera trigger for time-lapse and stills capture
- **Wireless (BLE) & Wired (USB)** — Control from an iPad over Bluetooth or a desktop browser over USB
- **Real-Time Monitoring** — Live status tiles, solar arc visualisation, interactive timeline with playhead
- **Profile Management** — Save, load, compare, and share experiment profiles
- **English & Japanese UI** — Full bilingual interface with one-click toggle

---

## 🌐 Try It Now

The web interfaces are hosted on GitHub Pages — no installation required:

| Interface | URL | Use Case |
|-----------|-----|----------|
| **BLE (iPad)** | [odeepllama.github.io/SolarSim/ble/](https://odeepllama.github.io/SolarSim/ble/) | Wireless control via Bluefy browser on iPad |
| **USB (Desktop)** | [odeepllama.github.io/SolarSim/](https://odeepllama.github.io/SolarSim/) | Wired control via Chrome/Edge/Opera |

> **Note:** Web Serial and Web Bluetooth APIs require a compatible browser. See the in-app Help panel for details.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Web Interfaces                        │
│                                                          │
│  SolaSimStudio.html          SolaSimStudioBLE.html       │
│  (USB — Web Serial API)      (iPad — Web Bluetooth API)  │
│  Desktop Chrome/Edge/Opera   Bluefy browser on iPad      │
└──────────┬───────────────────────────────┬───────────────┘
           │ USB Serial                    │ BLE (NUS)
┌──────────▼──────────┐      ┌─────────────▼──────────────┐
│  ESP32-S3 Firmware  │      │  ESP32-S3 BLE Firmware     │
│  (ESP32/)           │      │  (BLE_iPad/)               │
│  USB + BLE capable  │      │  BLE-optimised, debounced  │
└─────────────────────┘      └────────────────────────────┘
┌─────────────────────┐
│  RP2040 Firmware    │
│  (RP2040/)          │
│  USB-only           │
└─────────────────────┘
```

---

## 📂 Repository Structure

| Folder | Description |
|--------|-------------|
| `ESP32/` | ESP32-S3 firmware (modular MicroPython) + USB web interface |
| `BLE_iPad/` | ESP32-S3 BLE-optimised firmware + BLE web interface for iPad |
| `RP2040/` | RP2040 firmware (single-file MicroPython, USB-only) |
| `Profiles/` | Example experiment profiles |
| `~Docs/` | Documentation and user guide |
| `.github/` | GitHub Actions workflow for auto-deployment |

---

## 🔧 Hardware Requirements

- **Microcontroller**: ESP32-S3 (recommended) or RP2040
- **LED Panels**: NeoPixel/WS2812B addressable LED strips or matrices
- **Servos**: For sun arc positioning and 360° rotation platform
- **OLED Display**: SSD1306 128×64 for on-device status
- **Camera Trigger**: Optional servo-based shutter trigger for imaging
- **3D-Printed Parts**: Housing and mounting components (STL files coming soon)

> 📋 Full parts list: [Bill of Materials (Google Sheet)](https://docs.google.com/spreadsheets/d/1aQhFblNy1jl5k1DLb-90Tq7NmfreDscm0g0mmVD8wfg/edit?usp=sharing)

---

## 🚀 Getting Started

### 1. Flash MicroPython Firmware

Download the appropriate MicroPython firmware for your board:
- **ESP32-S3**: Firmware `.bin` file included in `ESP32/`
- **RP2040**: Firmware `.uf2` file included in `RP2040/`

### 2. Upload Project Files

Using [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):

```bash
# For ESP32-S3 (BLE version for iPad)
cd BLE_iPad
mpremote connect /dev/YOUR_PORT cp boot.py main.py hardware.py simulator.py program_engine.py ble_comms.py ssd1306.py :

# For ESP32-S3 (USB version)
cd ESP32
mpremote connect /dev/YOUR_PORT cp boot.py main.py hardware.py simulator.py program_engine.py ble_comms.py ssd1306.py :
```

### 3. Connect via Browser

- **iPad (BLE)**: Open [SolaSim BLE](https://odeepllama.github.io/SolarSim/ble/) in the [Bluefy](https://apps.apple.com/us/app/bluefy-web-ble-browser/id1492822055) browser
- **Desktop (USB)**: Open [SolaSim USB](https://odeepllama.github.io/SolarSim/) in Chrome, Edge, or Opera

---

## 📖 Documentation

- **In-App Help**: Click the **Help** button in any web interface for a full interactive guide
- **User Guide**: See [`~Docs/SolarSimUserGuide.md`](~Docs/SolarSimUserGuide.md)

---

## 🤝 Contributing

This is a research project in active development. Contributions, suggestions, and bug reports are welcome! Please open an [Issue](https://github.com/odeepllama/SolarSim/issues) to get started.

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

Developed at [Akita International University](https://web.aiu.ac.jp/en/) with AI-assisted development using VS Code, GitHub Copilot, and Google Gemini.

---

<p align="center">
  <em>Bringing the sun indoors for plant science 🌱</em>
</p>
