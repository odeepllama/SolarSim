"""
main.py - Solar Simulator ESP32-S3 Entry Point
==============================================
This file runs automatically after boot.py

Initializes:
- I2C LCD display
- BLE server
- Solar simulation
- Command handling
"""

import gc
import time
from machine import Pin, I2C

print("\n[MAIN] Starting Solar Simulator...")

# ============================================
# Initialize Hardware
# ============================================

# Initialize I2C for LCD (GPIO21=SDA, GPIO22=SCL)
try:
    print("[MAIN] Initializing I2C...")
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    devices = i2c.scan()
    
    if devices:
        print(f"[MAIN] I2C devices found: {[hex(d) for d in devices]}")
        
        # Initialize LCD
        from lcd_i2c import LCD1602
        
        # Try common addresses
        lcd_addr = 0x27 if 0x27 in devices else (0x3F if 0x3F in devices else devices[0])
        lcd = LCD1602(i2c, lcd_addr)
        print(f"[MAIN] LCD initialized at {hex(lcd_addr)}")
        
        # Welcome message
        lcd.clear()
        lcd.print("SolarSim ESP32", 0, 0)
        lcd.print("Starting BLE...", 0, 1)
    else:
        print("[MAIN] Warning: No I2C devices found")
        lcd = None
        
except Exception as e:
    print(f"[MAIN] LCD initialization error: {e}")
    lcd = None

gc.collect()

# ============================================
# Initialize BLE Server
# ============================================

try:
    print("[MAIN] Initializing BLE server...")
    from ble_server import BLEServer
    
    # Command handler will be set later
    ble = BLEServer(name="SolarSim-ESP32", command_handler=None)
    print("[MAIN] BLE server started successfully")
    
    if lcd:
        lcd.clear()
        lcd.print("SolarSim ESP32", 0, 0)
        lcd.print("BLE Ready!", 0, 1)
        
except Exception as e:
    print(f"[MAIN] BLE initialization error: {e}")
    ble = None
    if lcd:
        lcd.clear()
        lcd.print("BLE Error!", 0, 0)
        lcd.print("Check console", 0, 1)

gc.collect()

# ============================================
# Simple Command Handler (Temporary)
# ============================================

def simple_command_handler(cmd):
    """
    Simple command handler for testing
    Will be replaced with full handler when solarsim_esp32.py is ready
    """
    print(f"[CMD] Received: {cmd}")
    
    parts = cmd.upper().strip().split()
    if not parts:
        return "ERROR: Empty command"
    
    command = parts[0]
    
    # Echo test
    if command == "ECHO":
        return f"Echo: {' '.join(parts[1:])}"
    
    # Status request
    elif command == "STATUS":
        mem_free = gc.mem_free() // 1024
        return f"STATUS OK - Free RAM: {mem_free}KB"
    
    # Test LCD
    elif command == "LCD" and len(parts) >= 2:
        if lcd:
            message = ' '.join(parts[1:])
            lcd.clear()
            lcd.print(message[:16], 0, 0)
            lcd.print("Command OK", 0, 1)
            return f"LCD: {message}"
        else:
            return "ERROR: LCD not initialized"
    
    # LED test (placeholder - will control NeoPixels later)
    elif command == "LED":
        return "LED: Not implemented yet"
    
    # Memory info
    elif command == "MEM":
        import gc
        gc.collect()
        free = gc.mem_free()
        total = gc.mem_alloc() + free
        return f"Memory: {free//1024}KB free / {total//1024}KB total"
    
    # Help
    elif command == "HELP":
        return "Commands: ECHO, STATUS, LCD, LED, MEM, HELP"
    
    # Unknown command
    else:
        return f"ERROR: Unknown command '{command}'"

# Set command handler for BLE
if ble:
    ble.command_handler = simple_command_handler
    print("[MAIN] Command handler registered")

# ============================================
# Main Loop
# ============================================

print("\n" + "="*50)
print("   Solar Simulator Ready!")
print("="*50)
print("\nConnect via:")
print("  1. USB Serial (115200 baud)")
print("  2. Bluetooth LE: 'SolarSim-ESP32'")
print("\nAvailable commands: ECHO, STATUS, LCD, MEM, HELP")
print("\nPress Ctrl+C to stop\n")

# Update LCD with ready status
if lcd:
    time.sleep(1)
    lcd.clear()
    lcd.display_status("--:--", "READY", 1.0, False)

# Status update counter
status_counter = 0
last_status_time = time.ticks_ms()

try:
    while True:
        # Update status every 5 seconds if BLE connected
        if ble and ble.is_connected():
            now = time.ticks_ms()
            if time.ticks_diff(now, last_status_time) >= 5000:
                status = {
                    "connected": True,
                    "uptime": time.ticks_ms() // 1000,
                    "memory": gc.mem_free() // 1024,
                    "counter": status_counter
                }
                ble.send_status(status)
                status_counter += 1
                last_status_time = now
        
        # Small delay to prevent tight loop
        time.sleep_ms(100)
        
        # Periodic garbage collection
        if status_counter % 10 == 0:
            gc.collect()
            
except KeyboardInterrupt:
    print("\n[MAIN] Shutting down...")
    if ble:
        ble.stop()
    if lcd:
        lcd.clear()
        lcd.print("Stopped", 0, 0)
    print("[MAIN] Goodbye!")
