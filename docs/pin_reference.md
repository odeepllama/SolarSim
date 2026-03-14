# Pin Reference

Complete pin assignments for both supported microcontroller platforms. The RP2040 column includes the corresponding [BBC micro:bit edge connector](https://spotpear.com/index/study/detail/id/943.html) pin on the RP2040:bit breakout board.

## Signal Pin Assignments

| Function | RP2040 GPIO | Micro:bit Pin | Voltage | ESP32-S3 GPIO |
|----------|------------|---------------|---------|---------------|
| **Servo 1** — Platform rotation | GP6 | Pin 3 | 3.3V | GPIO 1 |
| **Servo 2** — Primary camera trigger (DSLR) | GP10 | Pin 13 | 5V | GPIO 2 |
| **Servo 3** — Secondary camera trigger | GP11 | Pin 15 | 5V | GPIO 3 |
| **NeoPixel Data** — LED panel chain | GP15 | Pin 7 | 3.3V | GPIO 4 |
| **Camera Shutter** — BT trigger (active LOW) | GP14 | Pin 6 | 3.3V | GPIO 5 |
| **Button A** | GP0 | Pin 0 (P0) | — | GPIO 8 |
| **Button B** | GP1 | Pin 1 (P1) | — | GPIO 9 |
| **I2C SDA** — OLED display (ESP32-S3 only) | N/A | N/A | — | GPIO 6 |
| **I2C SCL** — OLED display (ESP32-S3 only) | N/A | N/A | — | GPIO 7 |

## Platform Notes

### RP2040:bit

![Micro:bit vs RP2040 board pinouts](microbit%20vs%20RP2040%20board%20pinouts.png)

The [RP2040:bit board](https://spotpear.com/index/study/detail/id/943.html) by Spotpear is pin-compatible with the BBC micro:bit edge connector. This means standard micro:bit breakout boards can be used for convenient access to the GPIO pins listed above.

- Servo 1 is on a **3.3V** output — sufficient for signal but use external 5V for servo power
- Servos 2 and 3 are on **5V** outputs on the breakout board
- The board also includes a built-in **5×5 LED matrix** driven via POV (persistence of vision) using GPIO pins 2–5, 7–9, 21, 22, and 25

### ESP32-S3

- The ESP32-S3 uses a direct GPIO numbering scheme (no breakout board mapping)
- Includes **I2C** support for an optional SSD1306 OLED status display (128×64)
- Supports **BLE** connectivity (not available on RP2040)

## Source Files

- **RP2040**: [SolarSimulatorSun.py](../RP2040/SolarSimulatorSun.py) — lines 14–19 (header) and 213–227 (pin definitions)
- **ESP32-S3**: [hardware.py](../ESP32/hardware.py) — lines 28–36 (pin definitions)
