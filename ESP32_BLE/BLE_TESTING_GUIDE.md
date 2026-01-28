# BLE Testing Guide - nRF Connect App

Complete guide to testing ESP32 BLE functionality using nRF Connect app on iPad.

---

## 🎯 Prerequisites

1. ✅ ESP32-S3 running with `main.py` loaded
2. ✅ nRF Connect app installed on iPad (free from App Store)
3. ✅ iPad Bluetooth enabled
4. ✅ ESP32 powered on and advertising

---

## 📱 Step-by-Step Testing with nRF Connect

### Step 1: Open nRF Connect

1. Launch **nRF Connect** app on iPad
2. Allow Bluetooth permissions if prompted
3. You should see the main scanner screen

### Step 2: Scan for Device

1. Tap **SCAN** button (bottom right)
2. Wait 2-5 seconds
3. Look for **"SolarSim-ESP32"** in the device list

**Troubleshooting**:
- If not visible, check ESP32 is powered and main.py is running
- Try pulling down to refresh scan
- Check REPL output on ESP32 for "[BLE] Advertising" message

### Step 3: Connect to Device

1. Tap on **"SolarSim-ESP32"**
2. Tap **CONNECT** button
3. Wait for connection (1-3 seconds)
4. Device details screen should appear

**Expected ESP32 Output**:
```
[BLE] Client connected: XX:XX:XX:XX:XX:XX (handle=0)
```

### Step 4: Explore Services

1. Tap **"Unknown Service"** or service UUID starting with `12345678...`
2. You should see 3 characteristics:
   - **Command** (UUID ending in ...def1) - Write icon
   - **Response** (UUID ending in ...def2) - Notify icon
   - **Status** (UUID ending in ...def3) - Notify icon

---

## 📝 Test Commands

### Test 1: Echo Command

**Purpose**: Verify basic command/response flow

1. Tap **Command** characteristic (UUID ending ...def1)
2. Tap **↑** (Upload/Write) icon
3. Select **"Text"** format (not UTF-8 or Hex)
4. Type: `ECHO Hello from iPad!`
5. Tap **SEND**

**Expected Result**:
- ESP32 console shows: `[CMD] Received: ECHO Hello from iPad!`
- Response characteristic updates (may need to subscribe to notifications)

### Test 2: Subscribe to Response Notifications

**Purpose**: Receive command responses automatically

1. Tap **Response** characteristic (UUID ending ...def2)
2. Tap the **↓↓↓** (Notify) icon to enable notifications
3. Icon should turn blue when enabled
4. Now send another command
5. Response should pop up automatically

Example:
```
Send: STATUS
Response: STATUS OK - Free RAM: 412KB
```

### Test 3: Check Status Updates

**Purpose**: Verify periodic status notifications

1. Tap **Status** characteristic (UUID ending ...def3)
2. Enable notifications (↓↓↓ icon)
3. Wait 5 seconds
4. You should see JSON updates appear:

```json
{
  "connected": true,
  "uptime": 123,
  "memory": 412,
  "counter": 5
}
```

Updates arrive every 5 seconds while connected.

### Test 4: LCD Control Command

**Purpose**: Test hardware control via BLE

**Requirements**: LCD must be connected and working

1. Send command: `LCD Testing BLE!`
2. Check ESP32 LCD display
3. Should show: "Testing BLE!" on line 1

**Expected ESP32 Output**:
```
[CMD] Received: LCD Testing BLE!
```

### Test 5: Memory Info

**Purpose**: Check system resources

1. Send command: `MEM`
2. Response shows: `Memory: XXXkB free / YYYkB total`

Example:
```
Send: MEM
Response: Memory: 405KB free / 512KB total
```

### Test 6: Help Command

**Purpose**: List available commands

1. Send command: `HELP`
2. Response: `Commands: ECHO, STATUS, LCD, LED, MEM, HELP`

---

## 📊 Full Test Command List

| Command | Response | Purpose |
|---------|----------|---------|
| `ECHO test` | `Echo: test` | Test basic communication |
| `STATUS` | `STATUS OK - Free RAM: XXXkB` | Check system status |
| `LCD Hello!` | `LCD: Hello!` | Test LCD display |
| `MEM` | `Memory: XXXkB free / YYYkB total` | Check available RAM |
| `HELP` | List of commands | Show available commands |

---

## 🔍 Advanced Testing

### Test Long Messages

Test MTU (Maximum Transmission Unit) handling:

```
Send: ECHO This is a longer message to test if the BLE server can handle messages that exceed the typical 20-byte MTU limit
```

**Expected**: Message sent in chunks, reassembled by ESP32

### Test Rapid Commands

Send commands quickly in succession:
1. `STATUS`
2. `MEM`
3. `ECHO test1`
4. `ECHO test2`

**Expected**: All processed in order, responses received

### Test Reconnection

1. Disconnect from device (tap DISCONNECT)
2. Wait 2 seconds
3. Reconnect
4. Verify commands still work

**Expected**: ESP32 should re-advertise after disconnect

---

## 🐛 Troubleshooting

### Problem: Device Not Found

**Symptoms**: "SolarSim-ESP32" doesn't appear in scan

**Solutions**:
1. Check ESP32 is powered on (USB connected)
2. Check REPL shows: `[BLE] Advertising as 'SolarSim-ESP32'`
3. Try restarting ESP32 (press RST button or Ctrl+D in REPL)
4. Check iPad Bluetooth is ON
5. Try closing and reopening nRF Connect app

**REPL Check**:
```python
>>> ble._ble.active()
True  # Should be True

>>> ble._advertise()  # Manually restart advertising
```

### Problem: Connection Fails

**Symptoms**: "Connecting..." times out or fails

**Solutions**:
1. Restart ESP32
2. Forget device in iPad Bluetooth settings
3. Clear nRF Connect cache (app settings)
4. Check ESP32 console for error messages

### Problem: No Response to Commands

**Symptoms**: Commands sent but no response received

**Solutions**:
1. Enable notifications on Response characteristic
2. Check ESP32 console shows: `[CMD] Received: ...`
3. Verify command handler is registered:
   ```python
   >>> ble.command_handler
   <function simple_command_handler at ...>  # Should exist
   ```
4. Try simple command like `HELP` first

### Problem: Disconnects Randomly

**Symptoms**: Connection drops after short time

**Solutions**:
1. Check ESP32 power supply (insufficient power?)
2. Monitor memory: `gc.mem_free()` - may be running out
3. Add `gc.collect()` calls in main loop
4. Check for exceptions in ESP32 console

### Problem: Garbled Responses

**Symptoms**: Response text is corrupted or incomplete

**Solutions**:
1. Check text encoding in nRF Connect (should be "Text" or "UTF-8")
2. Verify ESP32 sending valid UTF-8
3. May be MTU issue - try shorter commands
4. Check BLE signal strength (move closer)

---

## 📈 Expected Performance

| Metric | Expected Value | Notes |
|--------|----------------|-------|
| **Connection Time** | 1-3 seconds | iPad → ESP32 |
| **Command Latency** | 50-200ms | Send → Response |
| **Max Message Size** | ~512 bytes | (chunked automatically) |
| **Range** | 10-30m | Depends on environment |
| **Battery Impact** | Low | BLE is power-efficient |
| **Reconnection** | 2-5 seconds | After disconnect |

---

## ✅ Success Checklist

After completing this guide, you should have:

- [x] Connected to ESP32 via BLE
- [x] Sent command successfully  
- [x] Received response
- [x] Enabled notifications
- [x] Tested LCD control
- [x] Verified status updates
- [x] Tested reconnection
- [x] Understood BLE architecture

**If all checked ✅, you're ready to modify ProfileBuilder.html for Web Bluetooth!**

---

## 🎓 Understanding the BLE Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│  iPad nRF       │                    │   ESP32-S3      │
│  Connect App    │                    │                 │
│                 │                    │  ble_server.py  │
│  1. Write to    ├────[Command]─────>│  ↓              │
│     Command     │    "SET SPEED 6"   │  handler()      │
│     Char        │                    │  ↓              │
│                 │                    │  Process        │
│  2. Receive     │<────[Response]─────┤  ↓              │
│     Response    │     "SPEED: 6"     │  Send Response  │
│     Notify      │                    │                 │
│                 │                    │                 │
│  3. Receive     │<────[Status]───────┤  Every 5 sec    │
│     Status      │     {json}         │  auto-send      │
│     Notify      │                    │                 │
└─────────────────┘                    └─────────────────┘
```

**Key Concepts**:
- **Services**: Container for related characteristics (we have one)
- **Characteristics**: Individual data points (we have 3)
- **Write**: App → ESP32 (commands)
- **Notify**: ESP32 → App (responses, status)
- **UUID**: Unique identifier for each service/characteristic

---

## 🔜 Next Steps

Once BLE testing is successful:

1. **Test NeoPixel Control**: Implement LED test command
2. **Test Servo Control**: Implement servo movement command  
3. **Port Full Simulator**: Create `solarsim_esp32.py`
4. **Web Bluetooth**: Modify ProfileBuilder.html to use Web Bluetooth API
5. **Integration**: Full system testing with web interface

---

**Testing Status**: Ready for immediate testing when hardware arrives!

**Estimated Testing Time**: 30-60 minutes for complete verification

**Questions?** Check ESP32_SETUP_GUIDE.md or REPL output for diagnostics
