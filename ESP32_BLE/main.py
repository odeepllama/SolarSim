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
# Initialize Solar Simulator
# ============================================

try:
    print("[MAIN] Initializing solar simulator...")
    from solarsim_esp32 import SolarSimulator
    
    simulator = SolarSimulator()
    print("[MAIN] Solar simulator initialized")
    
    # Set BLE command handler to use simulator
    if ble:
        ble.command_handler = simulator.process_command
        print("[MAIN] Command handler registered")
        
except Exception as e:
    print(f"[MAIN] Simulator initialization error: {e}")
    simulator = None
    error_msg = str(e)  # Capture error message
    
    # Fallback simple handler if simulator fails
    def fallback_handler(cmd):
        return f"ERROR: Simulator not initialized - {error_msg}"
    
    if ble:
        ble.command_handler = fallback_handler

gc.collect()

# ============================================
# Main Loop
# ============================================

print("\n" + "="*50)
print("   Solar Simulator Ready!")
print("="*50)
print("\nConnect via:")
print("  1. USB Serial (115200 baud)")
print("  2. Bluetooth LE: 'SolarSim-ESP32'")
print("\nAvailable commands: ECHO, STATUS, SPEED, TIME, FILL, ROTATE, CAMERA, MEM, HELP")
print("\nPress Ctrl+C to stop\n")

# Update LCD with ready status
if lcd:
    time.sleep(1)
    lcd.clear()
    lcd.print("SolarSim Ready", 0, 0)
    lcd.print("BLE Active", 0, 1)

# Status update counter
status_counter = 0
last_status_time = time.ticks_ms()
last_sim_update = time.ticks_ms()

try:
    while True:
        # Update simulation if initialized
        if simulator:
            now = time.ticks_ms()
            if time.ticks_diff(now, last_sim_update) >= 1000:  # Update every second
                simulator.update()
                last_sim_update = now
        
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
    if simulator:
        simulator.shutdown()
    if ble:
        ble.stop()
    if lcd:
        lcd.clear()
        lcd.print("Stopped", 0, 0)
    print("[MAIN] Goodbye!")
