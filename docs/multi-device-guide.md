# Connecting Multiple RP2040 Devices from One Laptop

This guide covers how to control two or more SolaSim devices simultaneously from a single computer using SolaSimStudio.

## Overview

Each browser tab runs an independent instance of SolaSimStudio with its own serial connection. To control multiple devices, open one tab per device — all served from the same URL.

## Setup

1. **Plug in both RP2040 boards** via USB (directly or through a hub)
2. **Open SolaSimStudio** in your first browser tab
3. **Click Connect** → the browser's port picker will appear showing all available devices
4. **Select your first device** and connect
5. **Open a second tab** at the same URL
6. **Click Connect** → the picker will show the remaining device (the first will be grayed out)
7. **Select the second device** — both tabs are now connected independently

## Identifying Which Device is Which

All RP2040 boards have the same USB vendor/product ID, so the port picker can't show device names. Instead, devices are distinguished by their **port path**, which is determined by the **physical USB port** you plug into.

### Finding your port paths

Plug in one device, check the port path, then plug in the second device and check again.

**Windows** — in PowerShell:
```powershell
Get-WMIObject Win32_SerialPort | Select-Object DeviceID, Description
```
Or open **Device Manager → Ports (COM & LPT)**.

**macOS** — in Terminal:
```bash
ls /dev/cu.usbmodem*
```

**Linux** — in Terminal:
```bash
ls /dev/ttyACM*
```

### Typical port naming by platform

| Platform | Example paths | Pattern |
|----------|--------------|---------|
| **Windows** | `COM3`, `COM4` | Assigned in order; consistent per port after first use |
| **macOS** (two USB-C ports) | `/dev/cu.usbmodem1101`, `/dev/cu.usbmodem3101` | Number based on USB bus/port topology |
| **macOS** (USB hub) | `/dev/cu.usbmodem1101`, `/dev/cu.usbmodem1102` | Sequential on same hub |
| **Linux** | `/dev/ttyACM0`, `/dev/ttyACM1` | Sequential; may change between reboots |

> **Tip:** Port paths are generally deterministic per physical USB port. Label your hub ports or USB cables to keep track of which device is which.

## Troubleshooting

### "The device port is already in use"

This means another tab (or another app like Thonny) already has that port open. Check for:
- Another SolaSimStudio tab connected to the same device
- Thonny, PuTTY, or another serial terminal running in the background

### Port picker doesn't appear

If only one RP2040 is connected, SolaSimStudio auto-connects without showing the picker. The picker only appears when you click Connect manually or when multiple devices are detected.

### Both tabs show the same data

Double-check you selected **different** ports in each tab. The first device's port will appear grayed out in the second tab's picker — make sure you selected the other one.
