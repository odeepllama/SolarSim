---
description: Flash MicroPython to ESP32-S3 and upload Solar Simulator files
---

# ESP32-S3 Flash and Upload Protocol

This workflow fully automates the process of erasing the flash, installing MicroPython firmware, prompting for a physical reset, and uploading the necessary `.py` files.

// turbo-all

1. First, find the connected ESP32-S3 device port. If this fails, the device is not plugged in or not in bootloader mode.
```bash
ls /dev/cu.usb*
```

2. Erase the existing flash memory. (Replace `/dev/cu.wchusbserial5AB90101341` with the actual port if it changed).
```bash
esptool.py --chip esp32s3 --port /dev/cu.wchusbserial5AB90101341 erase_flash
```

3. Write the new MicroPython firmware.
```bash
esptool.py --chip esp32s3 --port /dev/cu.wchusbserial5AB90101341 write_flash -z 0x0 ESP32_BLE/ESP32_GENERIC_S3-20251209-v1.27.0.bin
```

4. **MANUAL STEPREQUIRED**: The flash has been successfully written. You MUST now perform a physical reset of the board for it to boot into the new MicroPython environment.
   - Press the physical **RESET** button on the ESP32-S3 board.
   - Wait 3 seconds for the device to reboot.

5. Upload all the required Solar Simulator Python files from the `ESP32_Bluetooth` directory to the root of the device.
```bash
mpremote connect /dev/cu.wchusbserial5AB90101341 cp ESP32_Bluetooth/boot.py :boot.py + cp ESP32_Bluetooth/main.py :main.py + cp ESP32_Bluetooth/hardware.py :hardware.py + cp ESP32_Bluetooth/ble_comms.py :ble_comms.py + cp ESP32_Bluetooth/program_engine.py :program_engine.py + cp ESP32_Bluetooth/simulator.py :simulator.py
```

6. The upload is complete! The device is now running the updated firmware and code.
