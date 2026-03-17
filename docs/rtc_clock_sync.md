# 🕐 Real-Time Clock Sync (DS3231)

## Purpose

When the RP2040 runs standalone (without a computer attached), it has no way to know the current time of day. The optional DS3231 real-time clock module provides a battery-backed clock that retains the time even when powered off.

This allows the simulation to start at the correct local time — useful for multi-day experiments where program steps need to align with actual sunrise/sunset times.

## How It Works

1. **Setting the clock**: When SolaSimStudio connects to an RP2040 (USB or BLE), it automatically sends the browser's current date and time to a connected DS3231 module. No user action is required, but a log message is shown.

2. **Syncing at boot**: Hold **Button A** during power-on. If the DS3231 is connected and has a valid time, the simulation start time is set to the current clock time. If no module is detected, the simulation uses the default start time.

3. **Syncing during operation**: Long-press **Button A** (~1.5 seconds) to re-read the clock and re-anchor the simulation time.

> **Note:** If no DS3231 module is connected, the firmware runs normally with no errors or warnings. The RTC feature is entirely optional.

## Wiring

Connect the DS3231 module to the RP2040:bit via a micro:bit breakout board:

| DS3231 Pin | Function | RP2040 GPIO | micro:bit breakout pin |
|-----------|----------|------------|----------------------|
| D (SDA) | I2C Data | GP18 | Pin 20 |
| C (SCL) | I2C Clock | GP19 | Pin 19 |
| VCC | Power | — | 3.3V |
| GND | Ground | — | GND |

## Console Messages

The firmware only prints messages when the RTC is detected — silent otherwise:

| Event | Message |
|-------|---------|
| Boot sync successful | `[RTC] Synced: 16:49` |
| Long press sync successful | `[RTC] Synced: 16:49` |
| Long press, no module | `[RTC] No clock module connected` |
| Clock set from browser | `[RTC] Clock set: 2026-03-17 16:49:23` |
| Clock reads midnight | `[RTC] Clock reads 00:00 — needs setting via HTML` |
