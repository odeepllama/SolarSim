"""
SolarSim BLE-UART Bridge (ESP32-S3, MicroPython ubluetooth)

- BLE GATT server for Web Bluetooth (Chrome).
- UART relay to SolarSim-Core (TX=GPIO17, RX=GPIO20, 115200 baud).
- Line-based protocol (\n delimited).
"""

import time
from machine import Pin, UART
import ubluetooth

# ===== Configuration =====
BLE_NAME = "SolarSim-Link"
UART_ID = 1
UART_TX_PIN = 17
UART_RX_PIN = 20
UART_BAUD = 115200

# UART line handling
UART_READ_CHUNK = 128
MAX_LINE_LEN = 256

# Handshake
HELLO_INTERVAL_MS = 1000
HELLO_MSG = "SYS:HELLO"
READY_MSG = "SYS:READY"

# Nordic UART Service (NUS) UUIDs
_UART_SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # Write from central
_UART_TX_UUID = ubluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Notify to central

_UART_RX = (
    _UART_RX_UUID,
    ubluetooth.FLAG_WRITE | ubluetooth.FLAG_WRITE_NO_RESPONSE,
)
_UART_TX = (
    _UART_TX_UUID,
    ubluetooth.FLAG_NOTIFY,
)

_UART_SERVICE = (
    _UART_SERVICE_UUID,
    (_UART_TX, _UART_RX),
)


class BLEUARTBridge:
    def __init__(self, name=BLE_NAME):
        self._ble = ubluetooth.BLE()
        self._ble.active(True)
        try:
            self._ble.config(gap_name=name)
        except Exception:
            pass
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._connections = set()
        # Use name-only payload to avoid exceeding 31-byte ADV limit
        self._payload = self._advertising_payload(name=name)
        self._payload_min = self._payload
        time.sleep_ms(100)
        print("[BLE] init OK, starting advertising...")
        self._advertise()

    def _advertise(self, interval_us=500000):
        for attempt in range(3):
            try:
                self._ble.gap_advertise(None)
            except Exception:
                pass
            try:
                self._ble.gap_advertise(interval_us, adv_data=self._payload)
                print("[BLE] advertising (full payload)")
                return
            except OSError:
                time.sleep_ms(150)
                try:
                    self._ble.gap_advertise(interval_us, adv_data=self._payload_min)
                    print("[BLE] advertising (minimal payload)")
                    return
                except OSError:
                    time.sleep_ms(150)
            if attempt == 1:
                try:
                    self._ble.active(False)
                    time.sleep_ms(200)
                    self._ble.active(True)
                    self._ble.irq(self._irq)
                    print("[BLE] reset after advertise error")
                except Exception:
                    pass
        print("[BLE] advertise failed after retries")

    def _irq(self, event, data):
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("[BLE] connected")
        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            print("[BLE] disconnected, restarting advertise")
            self._advertise()
        elif event == 3:  # _IRQ_GATTS_WRITE
            conn_handle, value_handle = data
            if value_handle == self._rx_handle:
                msg = self._ble.gatts_read(self._rx_handle)
                if msg:
                    self.on_rx(msg)

    def on_rx(self, data):
        """Override in main loop: data is bytes from BLE central."""
        pass

    def notify(self, data):
        if not self._connections:
            return
        for conn_handle in self._connections:
            try:
                self._ble.gatts_notify(conn_handle, self._tx_handle, data)
            except Exception:
                pass

    @staticmethod
    def _advertising_payload(limited_disc=False, br_edr=False, name=None, services=None):
        payload = bytearray()

        def _append(ad_type, value):
            payload.extend(bytearray((len(value) + 1, ad_type)) + value)

        _append(0x01, bytearray(((0x02 if limited_disc else 0x06) + (0x00 if br_edr else 0x04),)))

        if name:
            _append(0x09, name.encode())

        if services:
            for uuid in services:
                b = bytes(uuid)
                if len(b) == 2:
                    _append(0x03, b)
                elif len(b) == 16:
                    _append(0x07, b)
        return payload


# ===== UART setup =====
_uart = UART(UART_ID, baudrate=UART_BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))
_uart.init(bits=8, parity=None, stop=1)

# ===== Bridge state =====
_ble = BLEUARTBridge()
_uart_line_buf = bytearray()
_ble_line_buf = bytearray()
_last_hello_ms = time.ticks_ms()
_link_ready = False


def _send_uart_line(line_str):
    _uart.write((line_str + "\n").encode())


def _handle_uart_line(line_bytes):
    global _link_ready
    try:
        line = line_bytes.decode().strip()
    except Exception:
        return

    if line == HELLO_MSG:
        _send_uart_line(READY_MSG)
        _link_ready = True
        print("[UART] HELLO -> READY")
        return
    if line == READY_MSG:
        _link_ready = True
        print("[UART] READY received")
        return

    # Forward normal lines to BLE central
    print("[UART] -> BLE:", line)
    _ble.notify(line_bytes + b"\n")


def _handle_ble_line(line_bytes):
    # Forward BLE line to UART
    try:
        line = line_bytes.decode().strip()
    except Exception:
        return
    if not line:
        return
    print("[BLE] -> UART:", line)
    _send_uart_line(line)


# BLE RX callback
_ble.on_rx = _handle_ble_line


# ===== Main loop =====
while True:
    now_ms = time.ticks_ms()

    # Periodic handshake until ready
    if not _link_ready and time.ticks_diff(now_ms, _last_hello_ms) >= HELLO_INTERVAL_MS:
        _send_uart_line(HELLO_MSG)
        _last_hello_ms = now_ms

    # Read UART bytes
    if _uart.any():
        data = _uart.read(UART_READ_CHUNK)
        if data:
            for b in data:
                if b in (10, 13):  # \n or \r
                    if _uart_line_buf:
                        _handle_uart_line(bytes(_uart_line_buf))
                        _uart_line_buf = bytearray()
                else:
                    if len(_uart_line_buf) < MAX_LINE_LEN:
                        _uart_line_buf.append(b)
                    else:
                        _uart_line_buf = bytearray()

    time.sleep_ms(5)
