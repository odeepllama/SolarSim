"""
BLE GATT Server for Solar Simulator
====================================
Provides Bluetooth Low Energy communication interface for iPad/browser control
using Web Bluetooth API.

Service UUID: 12345678-1234-5678-1234-56789abcdef0

Characteristics:
- Command (Write): Receive commands from browser
- Response (Read/Notify): Send command responses back  
- Status (Read/Notify): Periodic status updates (JSON)
"""

import ubluetooth
import struct
import json
from micropython import const

# BLE Event Constants
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_GATTS_INDICATE_DONE = const(20)

# Define Solar Simulator BLE Service UUIDs
SOLAR_SIM_SERVICE_UUID = ubluetooth.UUID('12345678-1234-5678-1234-56789abcdef0')
COMMAND_CHAR_UUID = ubluetooth.UUID('12345678-1234-5678-1234-56789abcdef1')
RESPONSE_CHAR_UUID = ubluetooth.UUID('12345678-1234-5678-1234-56789abcdef2')
STATUS_CHAR_UUID = ubluetooth.UUID('12345678-1234-5678-1234-56789abcdef3')

# GATT Characteristic Flags
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

class BLEServer:
    def __init__(self, name="SolarSim-ESP32", command_handler=None):
        """
        Initialize BLE GATT server
        
        Args:
            name: Device name to advertise
            command_handler: Function to call when commands received
                           Signature: handler(command_string) -> response_string
        """
        self.name = name
        self.command_handler = command_handler
        self._ble = ubluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        
        # Connection state
        self._connections = set()
        self._conn_handle = None
        
        # Response queue (for commands that need async responses)
        self._response_queue = []
        
        # Register GATT services
        self._register_services()
        
        # Start advertising
        self._advertise()
        
        print(f"[BLE] Server initialized: {self.name}")
        print(f"[BLE] Service UUID: {SOLAR_SIM_SERVICE_UUID}")
        
    def _register_services(self):
        """Register GATT service and characteristics"""
        
        # Define characteristics with their properties
        # Command characteristic: Write-only (browser sends commands)
        COMMAND_CHAR = (
            COMMAND_CHAR_UUID,
            _FLAG_WRITE,
        )
        
        # Response characteristic: Read + Notify (send responses back)
        RESPONSE_CHAR = (
            RESPONSE_CHAR_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )
        
        # Status characteristic: Read + Notify (periodic status updates)
        STATUS_CHAR = (
            STATUS_CHAR_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )
        
        # Define the service with all characteristics
        SOLAR_SERVICE = (
            SOLAR_SIM_SERVICE_UUID,
            (COMMAND_CHAR, RESPONSE_CHAR, STATUS_CHAR,)
        )
        
        # Register services and get handles
        ((self._cmd_handle, self._resp_handle, self._status_handle,),) = \
            self._ble.gatts_register_services((SOLAR_SERVICE,))
        
        print(f"[BLE] Service registered - Handles: cmd={self._cmd_handle}, "
              f"resp={self._resp_handle}, status={self._status_handle}")
    
    def _irq(self, event, data):
        """BLE interrupt handler - called for all BLE events"""
        
        if event == _IRQ_CENTRAL_CONNECT:
            # A device has connected
            conn_handle, addr_type, addr = data
            self._connections.add(conn_handle)
            self._conn_handle = conn_handle
            addr_str = ':'.join(['%02X' % b for b in bytes(addr)])
            print(f"[BLE] Client connected: {addr_str} (handle={conn_handle})")
            
        elif event == _IRQ_CENTRAL_DISCONNECT:
            # Device disconnected
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            if conn_handle == self._conn_handle:
                self._conn_handle = None
            print(f"[BLE] Client disconnected (handle={conn_handle})")
            # Start advertising again to allow reconnection
            self._advertise()
            
        elif event == _IRQ_GATTS_WRITE:
            # Data written to a characteristic
            conn_handle, attr_handle = data
            
            if attr_handle == self._cmd_handle:
                # Command received
                self._handle_command(conn_handle)
                
        elif event == _IRQ_GATTS_READ_REQUEST:
            # Client requested to read a characteristic
            # (Usually handled automatically, but we can customize)
            pass
    
    def _handle_command(self, conn_handle):
        """Process command written to command characteristic"""
        try:
            # Read the command data
            command_data = self._ble.gatts_read(self._cmd_handle)
            command = command_data.decode('utf-8').strip()
            
            print(f"[BLE] Received command: {command}")
            
            # Process command through handler
            if self.command_handler:
                # Capture printed output to send back as response
                response = self.command_handler(command)
                if response:
                    self.send_response(response)
            else:
                self.send_response(f"No handler configured for: {command}")
                
        except Exception as e:
            error_msg = f"[BLE] Error processing command: {e}"
            print(error_msg)
            self.send_response(error_msg)
    
    def send_response(self, text):
        """
        Send response text back to browser via Response characteristic
        
        Args:
            text: Response string to send
        """
        if not self._conn_handle:
            print("[BLE] No connected client to send response to")
            return
            
        try:
            # Encode and truncate if needed (BLE has MTU limits, typically 20-512 bytes)
            data = text.encode('utf-8')
            
            # Split into chunks if too large (MTU typically 23 bytes for notifications)
            MTU_SIZE = 20  # Safe default, some devices support more
            
            if len(data) <= MTU_SIZE:
                # Send in one chunk
                self._ble.gatts_notify(self._conn_handle, self._resp_handle, data)
            else:
                # Send in multiple chunks
                for i in range(0, len(data), MTU_SIZE):
                    chunk = data[i:i+MTU_SIZE]
                    self._ble.gatts_notify(self._conn_handle, self._resp_handle, chunk)
                    # Small delay between chunks
                    import time
                    time.sleep_ms(10)
                    
            print(f"[BLE] Sent response: {text[:50]}..." if len(text) > 50 else f"[BLE] Sent response: {text}")
            
        except Exception as e:
            print(f"[BLE] Error sending response: {e}")
    
    def send_status(self, status_dict):
        """
        Send JSON status update via Status characteristic
        
        Args:
            status_dict: Dictionary to send as JSON
        """
        if not self._conn_handle:
            return
            
        try:
            # Convert to JSON
            json_str = json.dumps(status_dict)
            data = json_str.encode('utf-8')
            
            # Send via notification
            MTU_SIZE = 20
            if len(data) <= MTU_SIZE:
                self._ble.gatts_notify(self._conn_handle, self._status_handle, data)
            else:
                # For large status updates, send in chunks
                for i in range(0, len(data), MTU_SIZE):
                    chunk = data[i:i+MTU_SIZE]
                    self._ble.gatts_notify(self._conn_handle, self._status_handle, chunk)
                    import time
                    time.sleep_ms(10)
                    
        except Exception as e:
            print(f"[BLE] Error sending status: {e}")
    
    def _advertise(self, interval_us=500000):
        """
        Start advertising BLE service
        
        Args:
            interval_us: Advertisement interval in microseconds (default 500ms)
        """
        # Create advertising payload
        # Format: Flags + Complete Local Name
        name_bytes = self.name.encode()
        
        # AD Structure: Length, Type, Data
        # Flags (0x01): General Discoverable + BR/EDR Not Supported
        # Name (0x09): Complete Local Name
        adv_data = bytearray([
            0x02, 0x01, 0x06,  # Flags
            len(name_bytes) + 1, 0x09  # Name length + type
        ]) + name_bytes
        
        # Service UUID advertisement
        service_data = bytearray([
            0x11, 0x07  # Length=17, Type=Complete 128-bit Service UUIDs
        ]) + bytes(SOLAR_SIM_SERVICE_UUID)
        
        # Start advertising with just the name payload
        self._ble.gap_advertise(interval_us, adv_data=adv_data)
        print(f"[BLE] Advertising as '{self.name}'")
    
    def is_connected(self):
        """Check if any client is connected"""
        return len(self._connections) > 0
    
    def disconnect_all(self):
        """Disconnect all connected clients"""
        for conn_handle in list(self._connections):
            try:
                self._ble.gap_disconnect(conn_handle)
            except:
                pass
        self._connections.clear()
        self._conn_handle = None
    
    def stop(self):
        """Stop BLE server and advertising"""
        self.disconnect_all()
        self._ble.active(False)
        print("[BLE] Server stopped")


# Example usage / testing
if __name__ == "__main__":
    import time
    
    def test_command_handler(cmd):
        """Simple test handler that echoes commands"""
        response = f"Echo: {cmd}"
        print(f"Handler processing: {cmd}")
        return response
    
    # Create BLE server
    ble = BLEServer(name="SolarSim-TEST", command_handler=test_command_handler)
    
    print("BLE Server running. Use nRF Connect app to test:")
    print("1. Scan for 'SolarSim-TEST'")
    print("2. Connect to device")
    print("3. Find Command characteristic")
    print("4. Write text like 'SET SPEED 6'")
    print("5. Check Response characteristic for reply")
    
    # Keep running and send periodic status updates
    counter = 0
    try:
        while True:
            time.sleep(5)
            if ble.is_connected():
                # Send test status update
                status = {
                    "test": True,
                    "counter": counter,
                    "time": time.ticks_ms()
                }
                ble.send_status(status)
                counter += 1
    except KeyboardInterrupt:
        print("\nStopping BLE server...")
        ble.stop()
