# Dual-Mode Connection Support Guide

**Purpose:** Enable ProfileBuilder.html to work with both Web Serial API (desktop) and Web Bluetooth API (iPad)

---

## Why Dual-Mode?

| Connection Type | Platform | Speed | Range | Best For |
|-----------------|----------|-------|-------|----------|
| **USB Serial** | Desktop Chrome/Edge | Fast | Wired only | Development, desktop use |
| **Bluetooth LE** | iPad, Desktop | Medium | ~10 meters | Wireless, mobile use |

---

## ESP32-S3 Side: Dual-Mode Support

### Option 1: Use `main_dual_mode.py`

Replace current `main.py` with `main_dual_mode.py`:
- ✅ Handles both BLE and USB Serial simultaneously
- ✅ Same command handler for both
- ✅ Reports connection mode via `MODE` command
- ✅ LCD shows current connection type

**To enable:**
```bash
# On ESP32-S3
mv main.py main_ble_only.py.backup
mv main_dual_mode.py main.py
# Reset ESP32
```

### Option 2: Modify Current `main.py`

Add serial input handler to existing `main.py`:

```python
# Add after BLE initialization
import sys
import select

def check_serial_input():
    """Check for USB Serial commands"""
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            return line if line else None
    except:
        return None

# In main loop, before time.sleep()
serial_cmd = check_serial_input()
if serial_cmd:
    response = handle_command(serial_cmd)
    print(response)  # Send to Serial
```

---

## ProfileBuilder.html Side: Connection Detection

### Auto-Detection Logic

```javascript
// Connection Manager for ProfileBuilder.html
class ConnectionManager {
    constructor() {
        this.connectionType = null;  // 'serial', 'bluetooth', or null
        this.device = null;
        this.writer = null;
        this.reader = null;
    }
    
    // Check which APIs are available
    async detectAvailableMethods() {
        const available = {
            serial: 'serial' in navigator,
            bluetooth: 'bluetooth' in navigator
        };
        
        console.log('Available connection methods:', available);
        return available;
    }
    
    // Let user choose connection type
    async connect(preferredMethod = 'auto') {
        const available = await this.detectAvailableMethods();
        
        if (preferredMethod === 'auto') {
            // Auto-select: prefer Serial on desktop, Bluetooth on iPad
            if (available.serial && !this.isIPad()) {
                preferredMethod = 'serial';
            } else if (available.bluetooth) {
                preferredMethod = 'bluetooth';
            } else {
                throw new Error('No compatible connection method available');
            }
        }
        
        if (preferredMethod === 'serial' && available.serial) {
            return await this.connectSerial();
        } else if (preferredMethod === 'bluetooth' && available.bluetooth) {
            return await this.connectBluetooth();
        } else {
            throw new Error(`${preferredMethod} not available`);
        }
    }
    
    // Web Serial API connection (desktop)
    async connectSerial() {
        console.log('Connecting via USB Serial...');
        
        try {
            // Request port
            const port = await navigator.serial.requestPort();
            await port.open({ baudRate: 115200 });
            
            // Setup reader/writer
            this.device = port;
            this.writer = port.writable.getWriter();
            this.connectionType = 'serial';
            
            // Start read loop
            this.startSerialReader(port.readable);
            
            console.log('USB Serial connected!');
            return true;
            
        } catch (error) {
            console.error('Serial connection failed:', error);
            throw error;
        }
    }
    
    // Web Bluetooth API connection (iPad/desktop)
    async connectBluetooth() {
        console.log('Connecting via Bluetooth...');
        
        try {
            // Request device
            const device = await navigator.bluetooth.requestDevice({
                filters: [{ 
                    name: 'SolarSim-ESP32'
                }],
                optionalServices: ['12345678-1234-5678-1234-56789abcdef0']
            });
            
            // Connect to GATT server
            const server = await device.gatt.connect();
            const service = await server.getPrimaryService(
                '12345678-1234-5678-1234-56789abcdef0'
            );
            
            // Get characteristics
            const commandChar = await service.getCharacteristic(
                '12345678-1234-5678-1234-56789abcdef1'
            );
            const responseChar = await service.getCharacteristic(
                '12345678-1234-5678-1234-56789abcdef2'
            );
            const statusChar = await service.getCharacteristic(
                '12345678-1234-5678-1234-56789abcdef3'
            );
            
            // Subscribe to notifications
            await responseChar.startNotifications();
            await statusChar.startNotifications();
            
            responseChar.addEventListener('characteristicvaluechanged', 
                this.handleBLEResponse.bind(this));
            statusChar.addEventListener('characteristicvaluechanged', 
                this.handleBLEStatus.bind(this));
            
            // Store connection info
            this.device = device;
            this.commandChar = commandChar;
            this.connectionType = 'bluetooth';
            
            console.log('Bluetooth connected!');
            return true;
            
        } catch (error) {
            console.error('Bluetooth connection failed:', error);
            throw error;
        }
    }
    
    // Send command (works for both methods)
    async sendCommand(command) {
        const encoder = new TextEncoder();
        const data = encoder.encode(command + '\n');
        
        if (this.connectionType === 'serial') {
            await this.writer.write(data);
        } else if (this.connectionType === 'bluetooth') {
            await this.commandChar.writeValue(data);
        } else {
            throw new Error('Not connected');
        }
    }
    
    // Handle responses
    startSerialReader(readable) {
        const reader = readable.getReader();
        const decoder = new TextDecoder();
        
        (async () => {
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const text = decoder.decode(value);
                this.handleResponse(text);
            }
        })();
    }
    
    handleBLEResponse(event) {
        const decoder = new TextDecoder();
        const text = decoder.decode(event.target.value);
        this.handleResponse(text);
    }
    
    handleBLEStatus(event) {
        const decoder = new TextDecoder();
        const status = decoder.decode(event.target.value);
        this.handleStatus(status);
    }
    
    handleResponse(response) {
        console.log('Response:', response);
        // Update UI with response
        document.getElementById('response').textContent = response;
    }
    
    handleStatus(status) {
        console.log('Status:', status);
        // Update UI with status
        document.getElementById('status').textContent = status;
    }
    
    // Utility: Detect iPad
    isIPad() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }
    
    // Disconnect
    async disconnect() {
        if (this.connectionType === 'serial' && this.device) {
            await this.writer.releaseLock();
            await this.device.close();
        } else if (this.connectionType === 'bluetooth' && this.device) {
            await this.device.gatt.disconnect();
        }
        
        this.connectionType = null;
        this.device = null;
        console.log('Disconnected');
    }
}

// Usage in ProfileBuilder.html
const conn = new ConnectionManager();

// Auto-connect (smart selection)
document.getElementById('connect-auto').addEventListener('click', async () => {
    try {
        await conn.connect('auto');
        alert('Connected!');
    } catch (e) {
        alert('Connection failed: ' + e.message);
    }
});

// Force Serial
document.getElementById('connect-serial').addEventListener('click', async () => {
    try {
        await conn.connect('serial');
        alert('Connected via USB Serial!');
    } catch (e) {
        alert('Serial connection failed: ' + e.message);
    }
});

// Force Bluetooth
document.getElementById('connect-bluetooth').addEventListener('click', async () => {
    try {
        await conn.connect('bluetooth');
        alert('Connected via Bluetooth!');
    } catch (e) {
        alert('Bluetooth connection failed: ' + e.message);
    }
});

// Send command
document.getElementById('send').addEventListener('click', async () => {
    const cmd = document.getElementById('command').value;
    try {
        await conn.sendCommand(cmd);
    } catch (e) {
        alert('Send failed: ' + e.message);
    }
});
```

---

## UI Suggestions for ProfileBuilder.html

### Connection Button Options

**Option 1: Smart Connect (Recommended)**
```html
<button id="connect-auto">Connect</button>
```
- Auto-detects best method
- Simple for users
- Prefers Serial on desktop, Bluetooth on iPad

**Option 2: Manual Selection**
```html
<button id="connect-serial">Connect via USB</button>
<button id="connect-bluetooth">Connect via Bluetooth</button>
```
- User chooses method
- Good for testing
- More control

**Option 3: Hybrid**
```html
<button id="connect-auto">Quick Connect</button>
<details>
  <summary>Advanced</summary>
  <button id="connect-serial">Force USB Serial</button>
  <button id="connect-bluetooth">Force Bluetooth</button>
</details>
```
- Default simple, advanced available
- Best user experience

---

## Testing Dual-Mode

### Test on Desktop Chrome

1. **Serial test:**
   - Connect ESP32 via USB-C
   - Open ProfileBuilder.html
   - Click "Connect via USB"
   - Send commands
   - Should work instantly

2. **Bluetooth test:**
   - Same setup
   - Click "Connect via Bluetooth"
   - Select "SolarSim-ESP32" from list
   - Send commands
   - Should work wirelessly

3. **Simultaneous test:**
   - Open TWO browser windows
   - Window 1: Connect via USB Serial
   - Window 2: Connect via Bluetooth
   - Both should work at same time
   - ESP32 LCD shows "Mode: BOTH"

### Test on iPad

1. **Bluetooth only:**
   - Open ProfileBuilder.html in Safari/Chrome
   - Click "Connect" (auto-selects Bluetooth)
   - Select "SolarSim-ESP32"
   - Send commands
   - Should work wirelessly

2. **Serial unavailable:**
   - Serial button should be disabled/hidden
   - Only Bluetooth option shown
   - Clear error message if Serial attempted

---

## Performance Comparison

| Metric | USB Serial | Bluetooth LE |
|--------|-----------|--------------|
| **Latency** | <10ms | 50-200ms |
| **Throughput** | 115200 baud (~11KB/s) | ~5KB/s |
| **Reliability** | Very high | Medium (interference possible) |
| **Range** | Cable length only | ~10 meters |
| **Setup** | Plug in cable | Pair device |
| **iPad Support** | ❌ No | ✅ Yes |
| **Development** | ✅ Easier debugging | ⚠️ Harder to debug |

---

## Recommendations

### For Development Phase
- Use **USB Serial** (faster, more reliable, easier debugging)
- Keep Bluetooth enabled for wireless testing

### For Production/Demo
- Use **Bluetooth** (wireless, works on iPad)
- Keep Serial as fallback for troubleshooting

### For ProfileBuilder.html
- Implement **"Smart Connect"** button (auto-detects best method)
- Add manual override buttons for advanced users
- Show connection type indicator in UI

---

## Migration Path

### Phase 2 (Current): BLE Testing
- Finish BLE-only testing first
- Verify all hardware works
- Confirm commands functional

### Phase 2.5 (Optional): Add Serial
- Upload `main_dual_mode.py`
- Test both connection types
- Verify no conflicts

### Phase 3: Main Code Port
- Port SolarSimulator.py
- Works with both connection types automatically
- Same command handler for both

### Phase 4: Web Interface
- Modify ProfileBuilder.html
- Add connection type detection
- Test on both platforms

---

## Summary

**Current Status:** BLE-only (Phase 2)

**To Add Serial Support:**
1. Upload `main_dual_mode.py` → `main.py`
2. Reset ESP32
3. Test with both REPL (Serial) and nRF Connect (BLE)

**Benefits:**
- ✅ Desktop: Fast, reliable USB Serial
- ✅ iPad: Wireless Bluetooth
- ✅ Development: Serial for debugging
- ✅ Production: Bluetooth for demos
- ✅ Fallback: Always have both options

**When to Add:**
- **Now:** If you want maximum flexibility
- **After Phase 3:** After main code port complete
- **Phase 4:** When modifying ProfileBuilder.html anyway

---

**Recommendation:** Add dual-mode support **after Phase 2 testing** is complete. Verify BLE works first, then add Serial as enhancement.
