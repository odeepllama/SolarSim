"""
main.py - Solar Simulator ESP32-S3 Entry Point (Dual Interface)
===============================================================
This file runs automatically after boot.py

Initializes:
- I2C LCD display
- BLE server (legacy/direct mode)
- Solar simulation
- Dual Command Interfaces:
  1. USB Serial (Debug/Direct)
  2. UART1 Link (Connection from BLE Link Device)
"""

import gc
import time
import sys
import select
from machine import Pin, I2C, UART

print("\n[MAIN] Starting Solar Simulator (Dual Interface)...")

# ============================================
# Configuration
# ============================================

# UART1 Link (Connects to BLE Link Device)
UART_ID = 1
UART_BAUD = 115200
TX_PIN = 17
RX_PIN = 18

# ============================================
# Initialize Hardware
# ============================================

# 1. Initialize I2C for LCD
lcd = None
try:
    print("[MAIN] Initializing I2C...")
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    devices = i2c.scan()
    
    if devices:
        print(f"[MAIN] I2C devices found: {[hex(d) for d in devices]}")
        from lcd_i2c import LCD1602
        # Try common addresses
        lcd_addr = 0x27 if 0x27 in devices else (0x3F if 0x3F in devices else devices[0])
        lcd = LCD1602(i2c, lcd_addr)
        print(f"[MAIN] LCD initialized at {hex(lcd_addr)}")
        
        lcd.clear()
        lcd.print("SolarSim Main", 0, 0)
        lcd.print("Init UART...", 0, 1)
    else:
        print("[MAIN] Warning: No I2C devices found")
        
except Exception as e:
    print(f"[MAIN] LCD initialization error: {e}")

# 2. Initialize UART1 Link
uart_link = None
try:
    print(f"[MAIN] Initializing UART{UART_ID} Link...")
    uart_link = UART(UART_ID, baudrate=UART_BAUD, tx=Pin(TX_PIN), rx=Pin(RX_PIN))
    uart_link.init(bits=8, parity=None, stop=1)
    print(f"[MAIN] UART{UART_ID} started on TX={TX_PIN}, RX={RX_PIN}")
    if lcd:
        lcd.print("UART Link OK", 0, 1)
except Exception as e:
    print(f"[MAIN] UART initialization error: {e}")
    if lcd:
        lcd.print("UART Error!", 0, 1)

gc.collect()

# ============================================
# Initialize BLE Server (Legacy Direct Mode)
# ============================================

# Note: We keep this for direct connections, but primary control 
# is likely via the BLE Link Device now.
ble = None
try:
    print("[MAIN] Initializing local BLE server...")
    from ble_server import BLEServer
    # Command handler will be set later
    ble = BLEServer(name="SolarSim-Main", command_handler=None)
    print("[MAIN] BLE server started successfully")
except Exception as e:
    print(f"[MAIN] BLE initialization error: {e}")

gc.collect()

# ============================================
# Initialize Solar Simulator
# ============================================

simulator = None
try:
    print("[MAIN] Initializing solar simulator...")
    from solarsim_esp32 import SolarSimulator
    
    simulator = SolarSimulator()
    print("[MAIN] Solar simulator initialized")
    
    # Set direct BLE command handler
    if ble:
        ble.command_handler = simulator.process_command
        
except Exception as e:
    print(f"[MAIN] Simulator initialization error: {e}")
    # Fallback simple handler
    def fallback_handler(cmd):
        return f"ERROR: Simulator not initialized - {str(e)}"
    if ble:
        ble.command_handler = fallback_handler

gc.collect()

# ============================================
# Input Handlers
# ============================================

def check_usb_input():
    """Check for commands from USB Serial (sys.stdin)"""
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line:
                return line.strip()
    except:
        pass
    return None

def check_uart_input():
    """Check for commands from UART1 Link"""
    if not uart_link or not uart_link.any():
        return None
    
    try:
        # Read a line (terminates with \n)
        line = uart_link.readline()
        if line:
            return line.decode('utf-8').strip()
    except Exception as e:
        print(f"[UART] Error reading: {e}")
    return None

# ============================================
# Main Loop
# ============================================

print("\n" + "="*50)
print("   Solar Simulator Ready!")
print("="*50)
print(f"1. USB Serial: Active")
print(f"2. UART Link:  {'Active' if uart_link else 'Disabled'} (Pin {TX_PIN}/{RX_PIN})")
print(f"3. Direct BLE: {'Active' if ble else 'Disabled'}")
print("\nPress Ctrl+C to stop\n")

# Update LCD
if lcd:
    time.sleep(1)
    lcd.clear()
    lcd.print("SolarSim Ready", 0, 0)
    lcd.print("Waiting...", 0, 1)

# Variables for receiving partial UART lines
uart_buffer = ""

status_counter = 0
last_status_time = time.ticks_ms()
last_sim_update = time.ticks_ms()

try:
    while True:
        # 1. Update simulation
        if simulator:
            now = time.ticks_ms()
            if time.ticks_diff(now, last_sim_update) >= 1000:
                simulator.update()
                last_sim_update = now
        
        # 2. Check USB Input
        usb_cmd = check_usb_input()
        if usb_cmd:
            print(f"[USB] Received: {usb_cmd}")
            if simulator:
                response = simulator.process_command(usb_cmd)
                print(response)  # Send response to USB stdout
                
                if lcd:
                    lcd.clear()
                    lcd.print("USB CMD", 0, 0)
                    lcd.print(usb_cmd[:16], 0, 1)
        
        # 3. Check UART Link Input
        if uart_link and uart_link.any():
            try:
                # We read byte by byte or buffer to ensure we get a full line
                # Simple implementation: readline
                line_data = uart_link.readline()
                if line_data:
                    try:
                        uart_cmd = line_data.decode('utf-8').strip()
                        if uart_cmd:
                            print(f"[UART] Received: {uart_cmd}")
                            
                            if simulator:
                                response = simulator.process_command(uart_cmd)
                                
                                # Send response back via UART
                                uart_link.write(f"{response}\n")
                                print(f"[UART] Sent: {response}")
                                
                                if lcd:
                                    lcd.clear()
                                    lcd.print("UART CMD", 0, 0)
                                    lcd.print(uart_cmd[:16], 0, 1)
                    except UnicodeError:
                        pass
            except Exception as e:
                print(f"[UART] Error: {e}")

        # 4. Periodic Status Broadcast (to direct BLE and UART Link)
        # This allows the remote interface to stay updated
        now = time.ticks_ms()
        if time.ticks_diff(now, last_status_time) >= 5000:
            if simulator:
                # Generate status string manually to share logic
                sim_mins = simulator.get_sim_time() if hasattr(simulator, 'get_sim_time') else 0
                # Or just invoke a STATUS command internally? 
                # Better to just let the remote poll via STATUS command for now to avoid congestion.
                pass
                
            # Legacy BLE status
            if ble and ble.is_connected():
                status = {
                    "uptime": time.ticks_ms() // 1000,
                    "memory": gc.mem_free() // 1024
                }
                ble.send_status(status)
            
            last_status_time = now
        
        time.sleep_ms(10)
        
        # GC
        if status_counter % 100 == 0:
            gc.collect()
        status_counter += 1
            
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
