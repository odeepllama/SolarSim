# SPDX-License-Identifier: GPL-3.0-or-later
"""
hardware.py — ESP32-S3 WROOM Hardware Abstraction Layer
========================================================
Solar Simulator for Phototropism Experiments
Target: ESP32-S3 WROOM module

GPIO Pin Mapping:
  Servo 1 (Platform): GPIO 1     Servo 2 (Camera 1): GPIO 2
  Servo 3 (Camera 2): GPIO 3     NeoPixel Panel:     GPIO 4
  Camera Shutter:     GPIO 5     I2C SDA (Display):  GPIO 6
  I2C SCL (Display):  GPIO 7     Button A:           GPIO 8
  Button B:           GPIO 9

GPIOs 10-18, 21 reserved for future camera DVP module.
"""

import gc
import math
import neopixel
from machine import Pin, PWM, I2C
from time import ticks_ms, sleep_ms, sleep_us, ticks_diff


# ======================================================
# I. PIN CONFIGURATION
# ======================================================
SERVO_1_PIN = 1       # Platform rotation servo
SERVO_2_PIN = 2       # Primary camera trigger servo
SERVO_3_PIN = 3       # Secondary camera trigger servo
NEOPIXEL_PIN = 4      # NeoPixel panel data
CAMERA_SHUTTER_PIN = 5  # Camera shutter trigger (active LOW)
I2C_SDA_PIN = 6       # I2C SDA for SSD1306 display
I2C_SCL_PIN = 7       # I2C SCL for SSD1306 display
BUTTON_A_PIN = 8      # Button A
BUTTON_B_PIN = 9      # Button B

# ======================================================
# II. SERVO CONFIGURATION
# ======================================================
PWM_FREQ = 50               # Standard servo PWM frequency (Hz)
MIN_DUTY = 1400              # Duty cycle for 0 degrees (~0.5ms pulse)
MAX_DUTY = 8352              # Duty cycle for 270 degrees (~2.5ms pulse)
SERVO_ANGLE_RANGE = 273.0    # Full range of motion for the servo

TABLE_SERVO_START_ANGLE = 0       # Starting angle for table servo
CAMERA_SERVO_REST_ANGLE = 45      # Camera servo resting angle
CAMERA_SERVO_TRIGGER_ANGLE = 90   # Camera servo angle when triggered

# Servo1 nonlinear PWM calibration for 3:4 gear ratio
SERVO1_PWM_CALIBRATION_3TO4 = {
    0:   1400,
    90:  3200,
    180: 4900,
    270: 6600,
    360: 8252,
}

# Servo1 nonlinear PWM calibration for 1:1 ratio
SERVO1_PWM_CALIBRATION_1TO1 = {
    0:   1400,
    270: 8252,
}

# ======================================================
# III. NEOPIXEL CONFIGURATION
# ======================================================
NEOPIXEL_COUNT = 448    # 8×56 grid (7 panels of 64 LEDs)
MAX_BRIGHTNESS = 255    # Maximum pixel brightness

# ======================================================
# IV. DISPLAY CONFIGURATION (SSD1306 — stubbed for now)
# ======================================================
I2C_FREQ = 400000            # I2C bus frequency


class Display:
    """Stub display class for future SSD1306 128x64 OLED.

    All methods are no-ops. The simulator calls these at runtime;
    the real SSD1306 driver will be swapped in later.
    """

    def __init__(self, i2c=None):
        self._i2c = i2c
        self._available = False
        if i2c:
            try:
                devices = i2c.scan()
                if devices:
                    self._available = True
                    print(f"[DISPLAY] I2C devices found: {[hex(d) for d in devices]}")
                else:
                    print("[DISPLAY] No I2C devices found (stub mode)")
            except Exception as e:
                print(f"[DISPLAY] I2C scan error: {e}")

    def show_time(self, hours, minutes):
        """Display current simulation time."""
        pass

    def show_speed(self, speed_scale):
        """Display current speed indicator."""
        pass

    def show_status(self, status_dict):
        """Display a status summary (time, speed, intensity, etc.)."""
        pass

    def show_message(self, line1, line2=""):
        """Display a two-line message."""
        pass

    def clear(self):
        """Clear the display."""
        pass


class Hardware:
    """Manages all ESP32-S3 hardware: servos, NeoPixels, display, buttons, shutter."""

    def __init__(self):
        print("[HW] Initializing ESP32-S3 hardware...")

        # --- Servos ---
        self.servo_pwm_1 = PWM(Pin(SERVO_1_PIN), freq=PWM_FREQ)
        self.servo_pwm_2 = PWM(Pin(SERVO_2_PIN), freq=PWM_FREQ)
        self.servo_pwm_3 = PWM(Pin(SERVO_3_PIN), freq=PWM_FREQ)

        self.set_servo_angle(self.servo_pwm_1, TABLE_SERVO_START_ANGLE)
        self.set_servo_angle(self.servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
        self.set_servo_angle(self.servo_pwm_3, CAMERA_SERVO_REST_ANGLE)
        print("[HW] Servos initialized on GPIO 1, 2, 3")

        # --- NeoPixel Panel ---
        self._np_pin = Pin(NEOPIXEL_PIN, Pin.OUT)
        self.pixels = neopixel.NeoPixel(self._np_pin, NEOPIXEL_COUNT)
        # Flat bytearray: 3 bytes per pixel (R,G,B) — ~1.3 KB contiguous
        # vs. old tuple-list which was ~20 KB of fragmented heap objects
        self.panel_buffer = bytearray(NEOPIXEL_COUNT * 3)
        self._next_frame = bytearray(NEOPIXEL_COUNT * 3)  # reusable scratch buffer
        print(f"[HW] NeoPixel panel initialized: {NEOPIXEL_COUNT} LEDs on GPIO {NEOPIXEL_PIN}")

        # --- Camera Shutter ---
        self.camera_shutter_pin = Pin(CAMERA_SHUTTER_PIN, Pin.OUT)
        self.camera_shutter_pin.value(1)  # Idle HIGH (active LOW)
        print(f"[HW] Camera shutter on GPIO {CAMERA_SHUTTER_PIN}")

        # --- Buttons ---
        self.button_a = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
        self.button_b = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
        print(f"[HW] Buttons on GPIO {BUTTON_A_PIN}, {BUTTON_B_PIN}")

        # --- I2C / Display ---
        self._i2c = None
        self.display = Display()  # Stub by default
        try:
            self._i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQ)
            self.display = Display(self._i2c)
            print(f"[HW] I2C initialized on SDA={I2C_SDA_PIN}, SCL={I2C_SCL_PIN}")
        except Exception as e:
            print(f"[HW] I2C init error (display in stub mode): {e}")

        gc.collect()
        print(f"[HW] Init complete. Free mem: {gc.mem_free()} bytes")

    # ==========================================================
    # Servo Control
    # ==========================================================

    @staticmethod
    def set_servo_angle(pwm_obj, angle):
        """Set servo to specific angle (0-270 degrees) using linear interpolation."""
        angle = max(0, min(SERVO_ANGLE_RANGE, angle))
        duty_range = MAX_DUTY - MIN_DUTY
        duty = MIN_DUTY + (angle / SERVO_ANGLE_RANGE) * duty_range
        try:
            pwm_obj.duty_u16(int(duty))
            return True
        except Exception as e:
            print(f"[HW] Servo angle error: {e}")
            return False

    def set_servo1_angle(self, angle, use_1to1=False):
        """Set servo1 to a specific table angle using non-linear calibration.

        Args:
            angle: Target angle in degrees (0-360)
            use_1to1: If True, use 1:1 ratio calibration table
        """
        pwm_val = self._get_servo1_calibrated_pwm(angle, use_1to1)
        try:
            self.servo_pwm_1.duty_u16(pwm_val)
            return True
        except Exception as e:
            print(f"[HW] Servo1 PWM error: {e}")
            return False

    @staticmethod
    def _get_servo1_calibrated_pwm(angle, use_1to1=False):
        """Return calibrated PWM value for a given angle using lookup table."""
        angle = max(0, min(360, angle))
        table = SERVO1_PWM_CALIBRATION_1TO1 if use_1to1 else SERVO1_PWM_CALIBRATION_3TO4
        keys = sorted(table.keys())
        for i in range(len(keys) - 1):
            a0, a1 = keys[i], keys[i + 1]
            if a0 <= angle <= a1:
                pwm0, pwm1 = table[a0], table[a1]
                return int(pwm0 + (pwm1 - pwm0) * (angle - a0) / (a1 - a0))
        return table[keys[-1]]

    def get_rotation_camera_pwm(self, rotation_camera_servo=2):
        """Return the PWM object for the camera servo used during rotation."""
        return self.servo_pwm_2 if rotation_camera_servo == 2 else self.servo_pwm_3

    # ==========================================================
    # Camera Shutter
    # ==========================================================

    def trigger_camera_shutter(self, capture_mode="STILLS"):
        """Pulse camera shutter pin LOW for 10ms (STILLS mode only)."""
        if capture_mode == "STILLS":
            self.camera_shutter_pin.value(0)
            sleep_ms(10)
            self.camera_shutter_pin.value(1)

    # ==========================================================
    # NeoPixel Panel — Coordinate Mapping
    # ==========================================================

    @staticmethod
    def xy_to_index(x, y):
        """Convert (x, y) coordinates to a NeoPixel index.

        The panel is 56×8 (7 physical panels of 64 LEDs each).
        Panels are physically reversed (panel 0 is rightmost).
        Odd rows are serpentine (reversed direction).
        """
        visual_panel = x // 8
        physical_panel = 6 - visual_panel
        panel_x = x % 8
        if y % 2 == 1:
            panel_x = 7 - panel_x
        panel_index = y * 8 + panel_x
        return physical_panel * 64 + panel_index

    # ==========================================================
    # NeoPixel Panel — Fill & Write
    # ==========================================================

    def fill_panel(self, r, g, b, duration_sec=30):
        """Fill the entire panel with a single color.

        Returns the override expiry time in ticks_ms.
        """
        self.pixels.fill((r, g, b))
        self.pixels.write()
        buf = self.panel_buffer
        for i in range(NEOPIXEL_COUNT):
            off = i * 3
            buf[off] = r
            buf[off + 1] = g
            buf[off + 2] = b
        return ticks_ms() + int(duration_sec * 1000)

    def clear_panel(self):
        """Turn off all NeoPixels."""
        self.pixels.fill((0, 0, 0))
        self.pixels.write()
        for i in range(len(self.panel_buffer)):
            self.panel_buffer[i] = 0

    # ==========================================================
    # NeoPixel Panel — Sun Drawing
    # ==========================================================

    def draw_sun_to_buffer(self, buffer, x, y, size, r, g, b):
        """Draw a single square sun onto a bytearray buffer."""
        x_int = int(x + 0.5)
        y_int = int(y)
        size_int = int(size)

        r_base = clamp(r)
        g_base = clamp(g)
        b_base = clamp(b)

        half_size = size_int // 2
        start_x = x_int - half_size
        start_y = max(0, y_int - half_size)
        buf_len = len(buffer) // 3

        for y_offset in range(size_int):
            for x_offset in range(size_int):
                pos_x = start_x + x_offset
                pos_y = start_y + y_offset
                if not (0 <= pos_x < 56 and 0 <= pos_y < 8):
                    continue
                idx = self.xy_to_index(pos_x, pos_y)
                if idx < buf_len:
                    off = idx * 3
                    buffer[off] = r_base
                    buffer[off + 1] = g_base
                    buffer[off + 2] = b_base

    def update_sun_display(self, minute_of_day, get_sun_position_fn, dual_sun_enabled):
        """Calculate sun positions and update only changed pixels using delta-buffer."""
        # Reuse pre-allocated scratch buffer instead of creating new list
        nf = self._next_frame
        for i in range(len(nf)):
            nf[i] = 0

        x, y, size, r, g, b = get_sun_position_fn(minute_of_day)

        if size > 0:
            self.draw_sun_to_buffer(nf, x, y, size, r, g, b)

            if dual_sun_enabled:
                x_int = int(x + 0.5)
                size_int = int(size)
                half_size = size_int // 2
                start_x_primary = x_int - half_size
                end_x_primary = start_x_primary + size_int - 1
                start_x_mirrored = 55 - end_x_primary
                x_mirrored = float(start_x_mirrored + half_size)
                self.draw_sun_to_buffer(nf, x_mirrored, y, size, r, g, b)

        # Delta update: only write changed pixels
        buf = self.panel_buffer
        pixels_changed = False
        for i in range(NEOPIXEL_COUNT):
            off = i * 3
            nr, ng, nb = nf[off], nf[off + 1], nf[off + 2]
            if buf[off] != nr or buf[off + 1] != ng or buf[off + 2] != nb:
                buf[off] = nr
                buf[off + 1] = ng
                buf[off + 2] = nb
                self.pixels[i] = (nr, ng, nb)
                pixels_changed = True

        if pixels_changed:
            self.pixels.write()

    # ==========================================================
    # NeoPixel Panel — Camera & Rotation Lighting
    # ==========================================================

    @staticmethod
    def get_camera_panel_indices(panels_mode="ALL"):
        """Return panel indices (0-6) to illuminate based on mode string."""
        modes = {
            "ALL": list(range(7)),
            "MIDDLE5": [1, 2, 3, 4, 5],
            "MIDDLE3": [2, 3, 4],
            "OUTER2": [0, 6],
            "OUTER4": [0, 1, 5, 6],
        }
        return modes.get(panels_mode, list(range(7)))

    def apply_lighting(self, r, g, b, panels_mode="ALL"):
        """Activate uniform lighting on selected panels."""
        self.pixels.fill((0, 0, 0))
        panel_indices = self.get_camera_panel_indices(panels_mode)
        for panel in panel_indices:
            for y in range(8):
                for x in range(8):
                    idx = self.xy_to_index(panel * 8 + x, y)
                    self.pixels[idx] = (r, g, b)
        self.pixels.write()
        # Sync state buffer
        buf = self.panel_buffer
        for i in range(NEOPIXEL_COUNT):
            c = self.pixels[i]
            off = i * 3
            buf[off] = c[0]
            buf[off + 1] = c[1]
            buf[off + 2] = c[2]
        return panel_indices

    def deactivate_lighting(self):
        """Turn off all panel lighting and sync buffer."""
        self.pixels.fill((0, 0, 0))
        self.pixels.write()
        for i in range(len(self.panel_buffer)):
            self.panel_buffer[i] = 0

    # ==========================================================
    # Button Reading
    # ==========================================================

    def read_button_a(self):
        """Read button A state. Returns True if pressed (active LOW)."""
        return self.button_a.value() == 0

    def read_button_b(self):
        """Read button B state. Returns True if pressed (active LOW)."""
        return self.button_b.value() == 0

    # ==========================================================
    # Cleanup
    # ==========================================================

    def shutdown(self):
        """Safe shutdown: turn off outputs."""
        try:
            self.clear_panel()
            self.servo_pwm_1.deinit()
            self.servo_pwm_2.deinit()
            self.servo_pwm_3.deinit()
            self.camera_shutter_pin.value(1)
            self.display.clear()
            print("[HW] Shutdown complete")
        except Exception as e:
            print(f"[HW] Shutdown error: {e}")


# ======================================================
# Module-level utility functions
# ======================================================

def clamp(value, min_val=0, max_val=255):
    """Clamp a value between min_val and max_val."""
    return max(min_val, min(max_val, value))
