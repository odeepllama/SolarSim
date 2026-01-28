"""
Dual-Mode main.py - Supports both BLE and USB Serial
=======================================================
This version handles commands from both:
1. BLE GATT characteristics (wireless, works on iPad)
2. USB Serial (wired, works on desktop with Web Serial API)

Drop-in replacement for current main.py to enable dual-mode support.
"""

import time
import gc
import sys
import select
from ble_server import BLEServer
from lcd_i2c import LCD1602
from machine import Pin, I2C

# ============================================================================
# HARDWARE INITIALIZATION
# ============================================================================

print("\n" + "="*50)
print("Solar Simulator ESP32-S3 (DUAL-MODE)")
print("BLE + USB Serial Support")
print("="*50 + "\n")

# Initialize I2C and LCD
print("[INIT] Initializing I2C LCD...")
try:
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    devices = i2c.scan()
    
    if devices:
        addr = 0x27 if 0x27 in devices else devices[0]
        lcd = LCD1602(i2c, addr)
        lcd.clear()
        lcd.print("SolarSim DUAL", 0, 0)
        lcd.print("BLE + Serial", 0, 1)
        print(f"[INIT] LCD found at {hex(addr)}")
    else:
        print("[INIT] No LCD found")
        lcd = None
except Exception as e:
    print(f"[INIT] LCD error: {e}")
    lcd = None

time.sleep(1)

# ============================================================================
# COMMAND HANDLER (Shared by both BLE and Serial)
# ============================================================================

def handle_command(command):
    """
    Process command from either BLE or Serial
    Returns response string
    """
    try:
        parts = command.strip().split()
        if not parts:
            return "ERROR: Empty command"
        
        cmd = parts[0].upper()
        
        # ECHO - Echo back the message
        if cmd == "ECHO":
            return " ".join(parts[1:]) if len(parts) > 1 else "ECHO"
        
        # STATUS - Return system status
        elif cmd == "STATUS":
            gc.collect()
            free_kb = gc.mem_free() // 1024
            return f"OK: ESP32-S3 running, {free_kb}KB free"
        
        # LCD - Display on LCD
        elif cmd == "LCD":
            if lcd:
                line0 = " ".join(parts[1:3]) if len(parts) > 2 else "Test"
                line1 = " ".join(parts[3:]) if len(parts) > 3 else "Message"
                lcd.clear()
                lcd.print(line0[:16], 0, 0)
                lcd.print(line1[:16], 0, 1)
                return f"OK: LCD updated"
            else:
                return "ERROR: No LCD available"
        
        # MEM - Memory info
        elif cmd == "MEM":
            gc.collect()
            free = gc.mem_free()
            allocated = gc.mem_alloc()
            total = free + allocated
            return f"OK: Free={free//1024}KB, Allocated={allocated//1024}KB, Total={total//1024}KB"
        
        # PING - Connection test
        elif cmd == "PING":
            return "PONG"
        
        # HELP - List commands
        elif cmd == "HELP":
            return "Commands: ECHO, STATUS, LCD, MEM, PING, HELP, MODE"
        
        # MODE - Report connection mode
        elif cmd == "MODE":
            return "OK: Dual-mode (BLE + Serial)"
        
        else:
            return f"ERROR: Unknown command '{cmd}'"
    
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# BLE HANDLER
# ============================================================================

print("[INIT] Starting BLE server...")
ble = BLEServer(name="SolarSim-ESP32", command_callback=handle_command)
ble.start_advertising()
print("[INIT] BLE advertising started")
print(f"[INIT] Service UUID: {ble.service_uuid}")

if lcd:
    lcd.clear()
    lcd.print("BLE: Waiting", 0, 0)
    lcd.print("Serial: Ready", 0, 1)

# ============================================================================
# USB SERIAL HANDLER (Non-blocking)
# ============================================================================

def check_serial_input():
    """
    Check for commands from USB Serial (non-blocking)
    Returns: command string or None
    """
    try:
        # Check if data available on stdin
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line:
                return line.strip()
    except Exception as e:
        # select not available on all MicroPython builds
        # Fallback to blocking read with timeout
        pass
    return None


# Alternative for platforms without select:
def check_serial_input_alt():
    """
    Alternative serial check using sys.stdin.read() with small buffer
    """
    try:
        if sys.stdin in sys.stdin:  # Check if readable
            line = sys.stdin.readline()
            return line.strip() if line else None
    except:
        return None


# ============================================================================
# MAIN LOOP - Handle both BLE and Serial
# ============================================================================

print("\n[MAIN] Entering main loop...")
print("[MAIN] Ready to accept commands via:")
print("[MAIN]   - USB Serial (Web Serial API on desktop)")
print("[MAIN]   - BLE (Web Bluetooth API on iPad/desktop)")
print()

last_status_update = time.ticks_ms()
status_interval = 5000  # Update status every 5 seconds

connection_mode = "WAITING"  # "WAITING", "BLE", "SERIAL", "BOTH"

try:
    while True:
        # ====================================================================
        # Process USB Serial Input
        # ====================================================================
        try:
            serial_cmd = check_serial_input()
            if serial_cmd:
                print(f"[SERIAL] Received: {serial_cmd}")
                response = handle_command(serial_cmd)
                print(response)  # Send response back via Serial
                
                # Update connection mode
                if connection_mode == "WAITING":
                    connection_mode = "SERIAL"
                elif connection_mode == "BLE":
                    connection_mode = "BOTH"
                
                if lcd:
                    lcd.clear()
                    lcd.print("Serial CMD OK", 0, 0)
                    lcd.print(serial_cmd[:16], 0, 1)
        except Exception as e:
            print(f"[SERIAL] Error: {e}")
        
        # ====================================================================
        # BLE Status Update (handled by callbacks, but update LCD)
        # ====================================================================
        now = time.ticks_ms()
        if time.ticks_diff(now, last_status_update) > status_interval:
            last_status_update = now
            
            # Send periodic status via BLE if connected
            if ble.is_connected():
                gc.collect()
                status_msg = f"Mode:{connection_mode},Free:{gc.mem_free()//1024}KB"
                ble.send_status(status_msg)
                
                # Update connection mode
                if connection_mode == "WAITING":
                    connection_mode = "BLE"
                elif connection_mode == "SERIAL":
                    connection_mode = "BOTH"
                
                if lcd and connection_mode != "WAITING":
                    lcd.clear()
                    lcd.print(f"Mode: {connection_mode}", 0, 0)
                    lcd.print(f"{gc.mem_free()//1024}KB free", 0, 1)
        
        # ====================================================================
        # Garbage Collection
        # ====================================================================
        gc.collect()
        
        # Small delay to prevent busy-waiting
        time.sleep_ms(10)

except KeyboardInterrupt:
    print("\n[MAIN] Keyboard interrupt - stopping...")
    if lcd:
        lcd.clear()
        lcd.print("System Stopped", 0, 0)

except Exception as e:
    print(f"\n[MAIN] Fatal error: {e}")
    if lcd:
        lcd.clear()
        lcd.print("ERROR!", 0, 0)
        lcd.print(str(e)[:16], 0, 1)

finally:
    print("[MAIN] Cleanup complete")
