# NeoPixel Panel Array Wiring

> 🚧 **This document is under construction.** Detailed wiring diagrams and instructions coming soon.

## Overview

SolaSim uses a semi-circular array of NeoPixel (WS2812B) 8×8 LED matrices to simulate the sun's path across the sky. The panels are daisy-chained in series, with data flowing from the microcontroller through each panel in sequence.

## Panel Configuration

- **Panel type**: WS2812B addressable 8×8 LED matrices
- **Data protocol**: Single-wire NeoPixel (800 kHz)
- **Wiring**: Daisy-chained (DOUT → DIN of next panel)

## Wiring Diagram

*Coming soon — a diagram showing the physical layout and wiring connections.*

## Pin Assignments

| Signal | RP2040 Pin | ESP32-S3 Pin |
|--------|-----------|--------------|
| NeoPixel Data | *TBD* | *TBD* |

## Power Considerations

- Each WS2812B LED can draw up to 60 mA at full white brightness
- An 8×8 panel (64 LEDs) can draw up to **3.84 A** at maximum
- Use an appropriate external power supply — **do not power panels from the microcontroller's USB**
- Connect ground between the power supply and the microcontroller

## Notes

- Panel order in the array determines the simulated sun position
- The firmware maps panel indices to physical positions along the semi-circular arc
