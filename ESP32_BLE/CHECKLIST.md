# Pre-Delivery Checklist for ESP32-S3 Solar Simulator

## 📦 What You Have Ready

### ✅ Software Files Created
- [x] `ble_server.py` - Complete BLE GATT server implementation
- [x] `lcd_i2c.py` - I2C LCD 1602 driver with test code
- [x] `boot.py` - System initialization and boot diagnostics
- [x] `main.py` - Entry point with simple command handler
- [x] `ESP32_SETUP_GUIDE.md` - Complete setup instructions
- [x] `README.md` - Project overview and documentation

### ⏳ To Be Created (After Hardware Testing)
- [ ] `solarsim_esp32.py` - Full simulation port (based on SolarSimulator.py)
- [ ] Modified `ProfileBuilder.html` - Web Bluetooth API support

---

## 🛒 Shopping List

### Essential Hardware

#### ESP32-S3 Module ⭐ Most Important
**Recommended Model**: ESP32-S3-WROOM-1-N16R8
- **N16** = 16MB Flash
- **R8** = 8MB PSRAM (important for buffers!)

**Where to Buy**:
- Amazon: ~$10-15
- AliExpress: ~$5-8
- Digikey/Mouser: ~$8-12
- SparkFun/Adafruit: ~$20 (dev boards with USB-C)

**Alternative**: Any ESP32-S3 module works, but PSRAM variant recommended

#### I2C LCD Display
**Model**: 1602 LCD with I2C adapter (PCF8574)
- 16 characters × 2 lines
- Blue or green backlight
- I2C interface (reduces wiring to 4 wires)

**Where to Buy**:
- Amazon: ~$5-8
- AliExpress: ~$2-4
- eBay: ~$3-5

**Colors**: Usually blue/white or green/white text

#### USB-C Cable
- **Data capable** (not charge-only!)
- For programming and power
- Check you have one already

#### Optional but Recommended

**Breadboard or Prototyping Board**:
- For initial testing before soldering
- ~$5-10

**Jumper Wires**:
- Male-to-female for connections
- ~$3-5 for a set

**External Power Supply** (if servos draw too much):
- 5V 2-3A USB power supply
- Or breadboard power supply module
- ~$8-15

---

## 🧪 Testing Apps to Download

### nRF Connect (Essential for BLE Testing)
- **Platform**: iOS/Android
- **Cost**: Free
- **Link**: [App Store](https://apps.apple.com/app/nrf-connect-for-mobile/id1054362403)
- **Purpose**: Test BLE before modifying HTML

### LightBlue (Alternative BLE Tool)
- **Platform**: iOS/Android  
- **Cost**: Free
- **Purpose**: Another BLE debugging tool

### Chrome Browser (iPad)
- Make sure Chrome is installed for Web Bluetooth API support
- Safari also works but Chrome recommended

---

## 📅 When Hardware Arrives - Day 1 Tasks

### Hour 1: Flash MicroPython
1. [ ] Install esptool: `pip install esptool`
2. [ ] Download ESP32-S3 firmware from micropython.org
3. [ ] Find USB port (macOS: `/dev/cu.usbserial*`, Windows: `COMx`)
4. [ ] Erase flash: `esptool.py --chip esp32s3 erase_flash`
5. [ ] Flash firmware: `esptool.py --chip esp32s3 write_flash -z 0 firmware.bin`
6. [ ] Test REPL connection (Thonny or screen)

### Hour 2: Upload Files & Test BLE
1. [ ] Upload `ble_server.py` to ESP32
2. [ ] Upload `lcd_i2c.py` to ESP32
3. [ ] Upload `boot.py` to ESP32
4. [ ] Upload `main.py` to ESP32
5. [ ] Reboot ESP32 (press RST button or Ctrl+D)
6. [ ] Open nRF Connect app on iPad
7. [ ] Scan for "SolarSim-ESP32"
8. [ ] Connect and test commands

**Expected Output in REPL**:
```
==================================================
   Solar Simulator ESP32-S3 - Boot
==================================================
Reset cause: Power On
MicroPython: v1.xx.x
...
[MAIN] Starting Solar Simulator...
[MAIN] Initializing I2C...
[MAIN] Initializing BLE server...
[BLE] Server initialized: SolarSim-ESP32
...
==================================================
   Solar Simulator Ready!
==================================================
```

### Hour 3: Test LCD Display
1. [ ] Wire LCD to ESP32:
   - VCC → 5V
   - GND → GND
   - SDA → GPIO21
   - SCL → GPIO22
2. [ ] Reboot ESP32
3. [ ] Check LCD shows "SolarSim ESP32" / "BLE Ready!"
4. [ ] Test command: Send "LCD Hello ESP32" via BLE
5. [ ] Verify LCD updates

### Hour 4: Test Basic Components
1. [ ] Test NeoPixel control (if panel available)
2. [ ] Test servo control
3. [ ] Send various commands via nRF Connect
4. [ ] Monitor memory usage: send "MEM" command

---

## 🎯 Success Criteria for Day 1

After Day 1, you should have:
- ✅ ESP32-S3 running MicroPython
- ✅ BLE server visible on iPad
- ✅ Can send commands via nRF Connect
- ✅ LCD display showing status
- ✅ Commands processed and responses received

**If all green**, you're ready for Phase 2: Porting the full simulation!

---

## 📊 Estimated Costs

| Item | Price Range | Priority |
|------|-------------|----------|
| ESP32-S3 (PSRAM) | $8-20 | Essential ⭐⭐⭐ |
| 1602 I2C LCD | $3-8 | Essential ⭐⭐⭐ |
| USB-C Cable | $5-10 | Essential ⭐⭐⭐ |
| Jumper Wires | $3-5 | Recommended ⭐⭐ |
| Breadboard | $5-10 | Recommended ⭐⭐ |
| External Power | $8-15 | Optional ⭐ |
| **Total** | **$30-70** | |

**Budget Option**: ~$15-20 (ESP32 + LCD only)  
**Complete Kit**: ~$50-70 (all items)

---

## 🔮 Next Steps After Successful Testing

1. **Port Full Simulation** (3-5 days)
   - Create `solarsim_esp32.py` based on current SolarSimulator.py
   - Integrate with BLE server
   - Replace matrix display code with LCD updates
   - Test all simulation features

2. **Modify ProfileBuilder.html** (2-3 days)
   - Add Web Bluetooth API support
   - Create connection type auto-detection
   - Test all controls via BLE
   - Ensure feature parity with Serial version

3. **Final Integration** (1-2 days)
   - Test complete system end-to-end
   - Test profile uploads over BLE
   - Performance optimization
   - Documentation updates

**Total Estimated Time**: 1-2 weeks of focused work

---

## 💡 Pro Tips

1. **Order with Amazon Prime** if time-sensitive (2-day delivery)
2. **AliExpress** if budget-conscious (2-4 week shipping)
3. **Get PSRAM variant** of ESP32-S3 - worth the extra $2-3
4. **Buy 2 LCDs** in case one has wrong I2C address or is defective
5. **Keep RP2040 setup intact** during migration for comparison

---

## 📞 If You Get Stuck

**Problem**: Can't find USB port  
**Solution**: Check `ls /dev/cu.*` (macOS) or Device Manager (Windows)

**Problem**: LCD not detected  
**Solution**: Try both 0x27 and 0x3F addresses, check wiring

**Problem**: BLE not advertising  
**Solution**: Check `ble._ble.active()`, restart ESP32

**Problem**: Upload fails  
**Solution**: Hold BOOT button during upload, try slower baud rate

**Problem**: Memory errors  
**Solution**: Add `gc.collect()` calls, enable PSRAM

---

**Current Status**: ✅ Code ready, waiting for hardware!

**Estimated Hardware Arrival**: 2-5 days (Amazon) or 2-4 weeks (AliExpress)

**Next Milestone**: Successfully test BLE connection with nRF Connect app
