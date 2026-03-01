# SPDX-License-Identifier: GPL-3.0-or-later
"""
ble_comms.py — BLE GATT Server for ESP32-S3 Solar Simulator
=============================================================
Provides Web Bluetooth communication with Chrome browser.

Service UUID: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
Characteristics:
  Command  (Write):       6E400002-... — receive commands from browser
  Response (Read+Notify): 6E400003-... — send command responses back
  Status   (Read+Notify): 6E400004-... — periodic status updates

MTU: 512 bytes (509 payload per notification after 3-byte ATT header)
"""

import ubluetooth
from micropython import const
from time import sleep_ms, ticks_ms, ticks_diff
import gc

# ======================================================
# BLE Event Constants
# ======================================================
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_MTU_EXCHANGED = const(21)

# ======================================================
# GATT Characteristic Flags
# ======================================================
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)

# ======================================================
# Service & Characteristic UUIDs (inherited from ble_server.py)
# ======================================================
SOLAR_SIM_SERVICE_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
COMMAND_CHAR_UUID      = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
RESPONSE_CHAR_UUID     = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
STATUS_CHAR_UUID       = ubluetooth.UUID('6E400004-B5A3-F393-E0A9-E50E24DCCA9E')

# ======================================================
# MTU Configuration
# ======================================================
TARGET_MTU = 512          # Negotiated MTU target
ATT_HEADER_SIZE = 3       # ATT notification header
DEFAULT_PAYLOAD = 20      # Conservative fallback payload
CHUNK_DELAY_MS = 20       # Delay between chunked notifications


class BLEComms:
    """BLE GATT server for Solar Simulator communication.

    Manages BLE advertising, connection, and bidirectional communication
    via three characteristics (command, response, status).
    """

    def __init__(self, name="SolarSim-BT", on_command=None):
        """Initialize BLE communications.

        Args:
            name: BLE advertisement device name
            on_command: Callback function(command_string) called when Command char is written
        """
        self.name = name
        self.on_command = on_command

        print("[BLE] Step A: Creating BLE object...")
        self._ble = ubluetooth.BLE()

        print("[BLE] Step B: Activating BLE radio...")
        self._ble.active(True)
        print("[BLE] Step B: BLE radio active.")

        print("[BLE] Step C: Setting IRQ handler...")
        self._ble.irq(self._irq_handler)

        # Set GAP device name and MTU — gap_name is required in
        # MicroPython v1.27+ where custom adv_data name is ignored
        print("[BLE] Step D: Configuring gap_name and MTU...")
        try:
            self._ble.config(gap_name=name, mtu=TARGET_MTU)
        except Exception as e:
            print(f"[BLE] Step D: config warning: {e}")

        # Connection state
        self._connections = set()
        self._conn_handle = None

        # MTU tracking (starts at default BLE 4.0 minimum)
        self._mtu = 23
        self._payload_size = DEFAULT_PAYLOAD

        # Output control
        self._output_paused = False  # True when serial takes priority

        # Command queue: IRQ buffers commands here, main loop polls
        self._cmd_queue = []

        # Notification throttle: minimum ms between gatts_notify calls
        self._last_notify_ms = 0
        self._notify_min_gap_ms = 15

        # Characteristic handles (set during registration)
        self._cmd_handle = None
        self._resp_handle = None
        self._status_handle = None

        # Register GATT services
        print("[BLE] Step E: Registering GATT services...")
        self._register_services()
        print("[BLE] Step E: GATT services registered.")

        # Start advertising
        print("[BLE] Step F: Starting advertising...")
        self._advertise()
        print(f"[BLE] Init complete. Advertising as '{self.name}'.")


    def _register_services(self):
        """Register GATT service with three characteristics."""
        COMMAND_CHAR = (
            COMMAND_CHAR_UUID,
            _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
        )
        RESPONSE_CHAR = (
            RESPONSE_CHAR_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )
        STATUS_CHAR = (
            STATUS_CHAR_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )
        SOLAR_SERVICE = (
            SOLAR_SIM_SERVICE_UUID,
            (COMMAND_CHAR, RESPONSE_CHAR, STATUS_CHAR),
        )

        ((self._cmd_handle, self._resp_handle, self._status_handle),) = \
            self._ble.gatts_register_services((SOLAR_SERVICE,))

        # Set large write buffer for command characteristic
        # (profiles can be sent as large multi-line strings)
        self._ble.gatts_set_buffer(self._cmd_handle, 2048)


    def _irq_handler(self, event, data):
        """BLE interrupt request handler."""
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self._connections.add(conn_handle)
            self._conn_handle = conn_handle
            self._fresh_connect = True  # Signal simulator to skip status debounce
            self._connect_ms = ticks_ms()
            addr_str = ':'.join(['%02X' % b for b in bytes(addr)])
            print(f"[BLE] Connected: {addr_str} (handle={conn_handle})")

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            duration = ticks_diff(ticks_ms(), getattr(self, '_connect_ms', 0))
            self._connections.discard(conn_handle)
            if conn_handle == self._conn_handle:
                self._conn_handle = None
            self._mtu = 23
            self._payload_size = DEFAULT_PAYLOAD
            print(f"[BLE] Disconnected (handle={conn_handle}, {duration/1000:.1f}s)")
            # Re-advertise for reconnection
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._cmd_handle:
                self._handle_incoming_command()

        elif event == _IRQ_MTU_EXCHANGED:
            conn_handle, mtu = data
            self._mtu = mtu
            self._payload_size = mtu - ATT_HEADER_SIZE
            print(f"[BLE] MTU: {mtu} (payload={self._payload_size})")


    def _handle_incoming_command(self):
        """Read command from Command characteristic and buffer it.

        Called from IRQ context — must NOT call gatts_notify or sleep.
        Commands are processed by poll_command() from the main loop.
        """
        try:
            raw = self._ble.gatts_read(self._cmd_handle)
            command = raw.decode('utf-8').strip()
            if command:
                self._cmd_queue.append(command)
        except Exception as e:
            print(f"[BLE] Command parse error: {e}")

    def poll_command(self):
        """Process one buffered command. Call from main loop.

        Returns True if a command was processed, False if queue empty.
        """
        if not self._cmd_queue or not self.on_command:
            return False
        cmd = self._cmd_queue.pop(0)
        try:
            self.on_command(cmd)
        except Exception as e:
            print(f"[BLE] Command error: {e}")
        return True

    # ==========================================================
    # Advertising
    # ==========================================================

    @staticmethod
    def _adv_payload(adv_type, data):
        """Encode a single AD structure: length + type + data."""
        return bytes((len(data) + 1, adv_type)) + data

    def _advertise(self, interval_us=100000):
        """Start BLE advertising with iOS-compatible payloads.

        iOS requires explicit AD flags and the service UUID in
        advertising / scan-response data. Without them the device
        is invisible to CoreBluetooth (Safari, Bluefy, LightBlue…).

        Args:
            interval_us: Advertising interval in microseconds (default 250ms)
        """
        try:
            # --- Primary advertising data ---
            # AD Flags: LE General Discoverable (0x02) | BR/EDR Not Supported (0x04) = 0x06
            adv_data = self._adv_payload(0x01, b'\x06')
            # Complete Local Name (type 0x09)
            adv_data += self._adv_payload(0x09, self.name.encode())

            # --- Scan-response data ---
            # 128-bit service UUID (type 0x07) in little-endian
            # 6E400001-B5A3-F393-E0A9-E50E24DCCA9E reversed:
            _SVC_UUID_LE = b'\x9E\xCA\xDC\x24\x0E\xE5\xA9\xE0\x93\xF3\xA3\xB5\x01\x00\x40\x6E'
            resp_data = self._adv_payload(0x07, _SVC_UUID_LE)

            self._ble.gap_advertise(interval_us, adv_data=adv_data, resp_data=resp_data)

        except Exception as e:
            print(f"[BLE] Advertise error: {e}")

    # ==========================================================
    # Sending Data
    # ==========================================================

    @property
    def connected(self):
        """True if a client is currently connected."""
        return self._conn_handle is not None

    @property
    def output_paused(self):
        """True when serial has taken priority and BLE output should be suppressed."""
        return self._output_paused

    @output_paused.setter
    def output_paused(self, value):
        self._output_paused = bool(value)

    def send_response(self, text):
        """Send text via Response characteristic with auto-chunking.

        Multi-line text is sent as-is; the browser reassembles.
        Large payloads are automatically split into MTU-sized chunks.
        """
        if not self._conn_handle or self._output_paused:
            return False
        return self._send_chunked(self._resp_handle, text)

    def send_status(self, text):
        """Send text via Status characteristic with auto-chunking."""
        if not self._conn_handle or self._output_paused:
            return False
        return self._send_chunked(self._status_handle, text)

    def send_batch(self, lines):
        """Send multiple lines as chunked BLE transmissions.

        Sends lines in small sub-batches (max 10 lines each) with
        gc.collect() between to avoid ENOMEM on memory-constrained
        devices (~143KB free on ESP32-S3 without PSRAM).

        Args:
            lines: list of text strings to send
        Returns:
            True on success, False if not connected or send failed
        """
        if not self._conn_handle or self._output_paused:
            return False
        BATCH_SIZE = 10  # lines per sub-batch
        for start in range(0, len(lines), BATCH_SIZE):
            if not self._conn_handle:
                return False  # disconnected mid-send
            gc.collect()
            sub = lines[start:start + BATCH_SIZE]
            text = '\n'.join(sub) + '\n'
            if not self._send_chunked(self._resp_handle, text):
                return False
            if start + BATCH_SIZE < len(lines):
                sleep_ms(CHUNK_DELAY_MS)  # brief pause between sub-batches
        return True

    def _send_chunked(self, char_handle, text):
        """Send text as chunked BLE notifications.

        Splits data into payload-sized chunks and sends each with
        a small inter-chunk delay to prevent buffer overruns.
        Includes inter-notification throttle and single retry on failure.
        """
        try:
            data = text.encode('utf-8')
            chunk_size = self._payload_size
            gc.collect()
            chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
            t_start = ticks_ms()
            for idx, chunk in enumerate(chunks):
                # Throttle: ensure minimum gap between notifications
                now = ticks_ms()
                gap = ticks_diff(now, self._last_notify_ms)
                if gap < self._notify_min_gap_ms:
                    sleep_ms(self._notify_min_gap_ms - gap)

                try:
                    self._ble.gatts_notify(self._conn_handle, char_handle, chunk)
                except Exception:
                    # Single retry after a brief pause + gc
                    sleep_ms(50)
                    gc.collect()
                    try:
                        self._ble.gatts_notify(self._conn_handle, char_handle, chunk)
                    except Exception as e2:
                        print(f"[BLE] GATT fail chunk {idx+1}/{len(chunks)}: {e2}")
                        return False

                self._last_notify_ms = ticks_ms()
                if idx < len(chunks) - 1:
                    sleep_ms(CHUNK_DELAY_MS)
            # Send complete
            return True
        except Exception as e:
            print(f"[BLE] Send error: {e}")
            return False

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def stop(self):
        """Stop BLE and clean up."""
        try:
            self._ble.gap_advertise(None)
            self._ble.active(False)
            print("[BLE] Stopped")
        except Exception as e:
            print(f"[BLE] Stop error: {e}")

    def is_connected(self):
        """Check if any client is connected."""
        return len(self._connections) > 0
