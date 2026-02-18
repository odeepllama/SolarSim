"""
Dual-Mode main.py - Supports both BLE and Dedicated UART Bridge
===============================================================
This version determines the node role:
1. BLE Link Device (Bridge): Receives BLE commands -> Forwards to UART1 (Pins 17/18)
2. UART1 listens for responses -> Forwards back to BLE
3. USB Serial preserved for debugging
"""

import time
import gc
import sys
import select
from ble_server import BLEServer
from lcd_i2c import LCD1602
from machine import Pin, I2C, UART

# ============================================================================
# CONFIGURATION
# ============================================================================

# UART1 Configuration (Inter-device link)
UART_ID = 1
UART_BAUD = 115200
TX_PIN = 17
RX_PIN = 18

# ============================================================================
# HARDWARE INITIALIZATION
# ============================================================================

print("\n" + "="*50)
print("Solar Simulator - BLE Link Device (Bridge)")
print(f"Bridging BLE <-> UART{UART_ID} (TX={TX_PIN}, RX={RX_PIN})")
print("="*50 + "\n")

# Initialize I2C and LCD
print("[INIT] Initializing I2C LCD...")
try:
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    devices = i2c.scan()
    
    if devices:
        addr = 0x27 if 0x27 in devices else (0x3F if 0x3F in devices else devices[0])
        lcd = LCD1602(i2c, addr)
        lcd.clear()
        lcd.print("BLE Bridge", 0, 0)
        lcd.print("Init UART...", 0, 1)
        print(f"[INIT] LCD found at {hex(addr)}")
    else:
        print("[INIT] No LCD found")
        lcd = None
except Exception as e:
    print(f"[INIT] LCD error: {e}")
    lcd = None

# Initialize Dedicated UART for Inter-Device Communication
print(f"[INIT] Initializing UART{UART_ID}...")
try:
    uart_link = UART(UART_ID, baudrate=UART_BAUD, tx=Pin(TX_PIN), rx=Pin(RX_PIN))
    uart_link.init(bits=8, parity=None, stop=1)
    print(f"[INIT] UART{UART_ID} started on TX={TX_PIN}, RX={RX_PIN}")
except Exception as e:
    print(f"[INIT] Error starting UART: {e}")
    uart_link = None

time.sleep(1)

# ============================================================================
# COMMAND HANDLER
# ============================================================================

def handle_ble_command(command):
    """
    Callback for when a command is received via BLE.
    Forwards the command to the Main Device via UART.
    """
    cmd = command.strip()
    if not cmd:
        return "ERROR: Empty command"

    print(f"[BLE->UART] Forwarding: {cmd}")
    
    # Forward to Main Device via UART if available
    if uart_link:
        try:
            uart_link.write(f"{cmd}\n")  # Ensure newline for readline() on other end
            return None  # Don't send immediate response, wait for UART reply
            # Note: If we return a string here, BLEServer sends it immediately.
            # We explicitly return None so we can send the *real* response from UART later.
        except Exception as e:
            return f"ERROR: UART write failed: {e}"
    else:
        return "ERROR: UART link down"

# ============================================================================
# BLE INITIALIZATION
# ============================================================================

print("[INIT] Starting BLE server...")
# We pass handle_ble_command. Note: If it returns None, BLEServer won't send a reply immediately,
# which allows us to send the asynchronous UART reply later.
ble = BLEServer(name="SolarSim-ESP32", command_handler=handle_ble_command)
print("[INIT] BLE advertising started")

if lcd:
    lcd.clear()
    lcd.print("BLE: Ready", 0, 0)
    lcd.print("Bridge Active", 0, 1)

# ============================================================================
# USB SERIAL DEBUG HELPERS
# ============================================================================

def check_usb_serial():
    """Check for debug commands on USB Serial"""
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line:
                return line.strip()
    except:
        pass
    return None

# ============================================================================
# MAIN LOOP
# ============================================================================

print("\n[MAIN] Bridge Running...")
print("[MAIN] 1. Connect BLE App")
print("[MAIN] 2. Commands sent to BLE are forwarded to UART")
print("[MAIN] 3. Responses from UART are forwarded to BLE")

buffer = ""

try:
    while True:
        # 1. Check UART for responses from Main Device
        if uart_link and uart_link.any():
            try:
                # Read available data
                data = uart_link.read()
                if data:
                    # Decode and handle potentially fragmented messages
                    try:
                        text = data.decode('utf-8')
                        
                        # Simple line buffering
                        buffer += text
                        
                        if '\n' in buffer:
                            lines = buffer.split('\n')
                            # Process all complete lines
                            for line in lines[:-1]:
                                clean_line = line.strip()
                                if clean_line:
                                    print(f"[UART->BLE] Response: {clean_line}")
                                    
                                    # Forward to BLE
                                    if ble.is_connected():
                                        # Use send_response for generic messages or specific logic
                                        ble.send_response(clean_line)
                                        
                                        # Update LCD with status if applicable
                                        if lcd and "Time:" in clean_line:
                                            # "Time:06:00 Speed:1X..."
                                            parts = clean_line.split()
                                            if len(parts) >= 2:
                                                lcd.clear()
                                                lcd.print(parts[0], 0, 0) # Time:HH:MM
                                                lcd.print(parts[1], 0, 1) # Speed
                            
                            # Keep the remainder
                            buffer = lines[-1]
                            
                    except UnicodeError:
                        print("[Bridge] binary data ignored")
                        
            except Exception as e:
                print(f"[Bridge] UART Read Error: {e}")

        # 2. Check USB Serial (Local Debugging Override)
        debug_cmd = check_usb_serial()
        if debug_cmd:
            print(f"[USB->UART] Debug Send: {debug_cmd}")
            if uart_link:
                uart_link.write(f"{debug_cmd}\n")

        # 3. Frequent BLE housekeeping
        # (BLEServer handles interrupts automatically)
        
        # Small sleep to yield
        time.sleep_ms(10)

except KeyboardInterrupt:
    print("\n[MAIN] Stopping Bridge...")
    if ble:
        ble.stop()
    if lcd:
        lcd.clear()
        lcd.print("Bridge Stopped", 0, 0)
    print("[MAIN] Done")
