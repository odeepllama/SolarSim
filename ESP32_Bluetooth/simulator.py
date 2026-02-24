# SPDX-License-Identifier: GPL-3.0-or-later
"""
simulator.py — Core Solar Simulator Engine for ESP32-S3
========================================================
Manages simulation state, solar calculations, command processing,
servo state machines, and the main loop.
"""

import gc
import math
import sys
import os
from time import ticks_ms, ticks_diff, sleep_ms

try:
    import ujson as json
except ImportError:
    import json

from hardware import Hardware, clamp, MAX_BRIGHTNESS, CAMERA_SERVO_REST_ANGLE, CAMERA_SERVO_TRIGGER_ANGLE
from program_engine import ProgramEngine, ROTATION_SPEED_PRESET_TABLE

# ======================================================
# Default Simulation Parameters
# ======================================================
START_TIME_HHMM = 600
TIME_SCALE = 1                 # Time scaling factor (0=HOLD, 1=Real Time, 60, 600, etc.)
INTENSITY_SCALE = 1.0
SIMULATION_DATE = 20250621
LATITUDE = 0
SOLAR_MODE = "BASIC"
SUN_COLOR_MODE = "BLUE"
DUAL_SUN_ENABLED = False

# Rotation / Camera defaults
ROTATION_ENABLED = False
ROTATION_CYCLE_INTERVAL_MINUTES = 60
ROTATION_CAPTURE_MODE = "STILLS"
ROTATION_CAMERA_SERVO = 2
ROTATION_AT_NIGHT = False
SERVO2_INTERVAL_DAY_SEC = 120
SERVO2_INTERVAL_NIGHT_SEC = 0
SERVO3_INTERVAL_DAY_SEC = 0
SERVO3_INTERVAL_NIGHT_SEC = 0
STILLS_IMAGING_INTERVAL_SEC = 2.0
CAMERA_TRIGGER_HOLD_MS = 1500
SERVO2_TRIGGER_HOLD_MS = 1500
SERVO3_TRIGGER_HOLD_MS = 1500
ROTATION_SPEED_PRESET = "fast"
IMAGES_PER_ROTATION = 8
DEGREES_PER_IMAGE = 45.0
ROTATION_INCREMENT_DEGREES = 1.0
ROTATION_STEP_INTERVAL_MS = 20
ROTATION_CAMERA_ENABLED = True
ROTATION_LIGHTING_ENABLED = True
DWELL_TIME_MS = 1500
RETURN_STEP_DEGREES = 2
RETURN_STEP_INTERVAL_MS = 30
FINE_ROTATION_INCREMENT_DEGREES = 0.3
FINE_ROTATION_STEP_INTERVAL_MS = 90
MIN_FINE_ROTATION_STEP_INTERVAL_MS = 40
RESTART_AFTER_LOAD = True
SERVO_1TO1_RATIO = False
AUTO_LOAD_LATEST_PROFILE = True

# Lighting defaults
CAMERA_LIGHTING_ENABLED = True
SERVO3_LIGHTING_ENABLED = True
CAMERA_LIGHT_HOLD_MS = 1000
CAMERA_LIGHTING_PANELS = "ALL"
CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B = 30, 30, 30
ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B = 30, 30, 30
CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B = 255, 0, 0

# Scientific solar model cache
SOLAR_NOON_MINUTES = 720
SUNRISE_MINUTES = 360
SUNSET_MINUTES = 1080
DAY_DECLINATION = 0.0
DAY_EQT = 0.0


def get_speed_name(scale):
    if scale == 0: return "HOLD"
    r = "Reverse " if scale < 0 else ""
    m = abs(scale)
    if m == 1: return f"{r}Real Time"
    if m == 60: return f"{r}1 Min/Sec"
    if m == 600: return f"{r}10 Min/Sec"
    return f"{r}{m}x Speed"


def reanchor_start_time(preserved_minutes, new_scale, now_ms, start_hhmm, current_start):
    if new_scale == 0: return current_start
    sm = (start_hhmm // 100) * 60 + (start_hhmm % 100)
    if new_scale > 0:
        mss = (preserved_minutes - sm) % 1440
    else:
        mss = (sm - preserved_minutes) % 1440
    return now_ms - int((mss * 60000) / max(0.0001, abs(new_scale)))


# ======================================================
# Solar Calculation Functions
# ======================================================

def date_to_day_number(yyyymmdd):
    y = yyyymmdd // 10000
    m = (yyyymmdd // 100) % 100
    d = yyyymmdd % 100
    days_in_month = [0,31,28,31,30,31,30,31,31,30,31,30,31]
    if (y%4==0 and y%100!=0) or y%400==0: days_in_month[2] = 29
    return sum(days_in_month[1:m]) + d


def calculate_declination(day_number):
    return 23.45 * math.sin(math.radians((360/365) * (day_number - 81)))


def equation_of_time(day_number):
    b = math.radians((360/365) * (day_number - 81))
    return 9.87*math.sin(2*b) - 7.53*math.cos(b) - 1.5*math.sin(b)


def init_solar_day():
    global SOLAR_NOON_MINUTES, SUNRISE_MINUTES, SUNSET_MINUTES
    global DAY_DECLINATION, DAY_EQT
    dn = date_to_day_number(SIMULATION_DATE)
    DAY_DECLINATION = calculate_declination(dn)
    DAY_EQT = equation_of_time(dn)
    SOLAR_NOON_MINUTES = 720 - DAY_EQT
    lat_r = math.radians(LATITUDE)
    dec_r = math.radians(DAY_DECLINATION)
    cos_ha = -math.tan(lat_r) * math.tan(dec_r)
    if cos_ha < -1:
        SUNRISE_MINUTES, SUNSET_MINUTES = 0, 1440
    elif cos_ha > 1:
        SUNRISE_MINUTES, SUNSET_MINUTES = 720, 720
    else:
        ha = math.degrees(math.acos(cos_ha))
        SUNRISE_MINUTES = SOLAR_NOON_MINUTES - (ha * 4)
        SUNSET_MINUTES = SOLAR_NOON_MINUTES + (ha * 4)
    # In BASIC mode, override with fixed 06:00–18:00 to match get_basic_sun_position()
    if SOLAR_MODE == "BASIC":
        SUNRISE_MINUTES = 360
        SUNSET_MINUTES = 1080
        SOLAR_NOON_MINUTES = 720
    print(f"[SOLAR] Date={SIMULATION_DATE} Lat={LATITUDE} Dec={DAY_DECLINATION:.1f}"
          f" Noon={int(SOLAR_NOON_MINUTES//60):02d}:{int(SOLAR_NOON_MINUTES%60):02d}"
          f" Rise={int(max(0,SUNRISE_MINUTES)//60):02d}:{int(max(0,SUNRISE_MINUTES)%60):02d}"
          f" Set={int(min(1439,SUNSET_MINUTES)//60):02d}:{int(min(1439,SUNSET_MINUTES)%60):02d}")


def get_sim_time(start_hhmm, elapsed_ms, scale):
    start_m = (start_hhmm // 100) * 60 + (start_hhmm % 100)
    sim_elapsed = (elapsed_ms * scale) / 60000.0
    tod = (start_m + sim_elapsed) % 1440
    if tod < 0: tod += 1440
    return sim_elapsed, tod


def get_scientific_sun_position(minute):
    if minute < SUNRISE_MINUTES or minute > SUNSET_MINUTES:
        return 0, 0, 0, 0, 0, 0
    day_length = max(1, SUNSET_MINUTES - SUNRISE_MINUTES)
    progress = (minute - SUNRISE_MINUTES) / day_length
    # Symmetrical x path from 0.5 to 54.5
    x = 0.5 + progress * 54
    lat_r = math.radians(LATITUDE)
    dec_r = math.radians(DAY_DECLINATION)
    hour_angle = (minute - SOLAR_NOON_MINUTES) * 0.25
    ha_r = math.radians(hour_angle)
    sin_alt = (math.sin(lat_r)*math.sin(dec_r) +
               math.cos(lat_r)*math.cos(dec_r)*math.cos(ha_r))
    altitude = math.degrees(math.asin(max(-1, min(1, sin_alt))))
    if altitude <= 0:
        return 0, 0, 0, 0, 0, 0
    max_alt = math.degrees(math.asin(max(-1, min(1,
        math.sin(lat_r)*math.sin(dec_r) + math.cos(lat_r)*math.cos(dec_r)))))
    if max_alt <= 0: max_alt = 45
    # Sun size based on elevation: 2-8 pixels, rounded to even
    size = 2 + 6 * min(1, altitude / 45)
    size = round(size / 2) * 2  # round to even (2, 4, 6, 8)
    # Vertically centered on the 8-pixel panel
    y = (8 - size) // 2 + size // 2
    brightness = min(1.0, altitude / max_alt) * INTENSITY_SCALE
    if SUN_COLOR_MODE == "NATURAL":
        if altitude < 10:
            r = int(255 * brightness)
            g = int(120 * brightness)
            b = int(30 * brightness)
        elif altitude < 25:
            f = (altitude - 10) / 15
            r = int((255 - 20*f) * brightness)
            g = int((120 + 110*f) * brightness)
            b = int((30 + 170*f) * brightness)
        else:
            r = int(235 * brightness)
            g = int(230 * brightness)
            b = int(200 * brightness)
    elif SUN_COLOR_MODE == "BLUE":
        r = 0
        g = 0
        b = int(255 * brightness)
    else:
        r = int(CUSTOM_SUN_R * brightness)
        g = int(CUSTOM_SUN_G * brightness)
        b = int(CUSTOM_SUN_B * brightness)
    return x, y, size, clamp(r), clamp(g), clamp(b)


def get_basic_sun_position(minute):
    """Calculate sun position using the basic model with constant 8x8 square."""
    # Default values for nighttime
    x, y = -10, 0  # Off-screen
    size = 8        # Always 8x8 when visible

    # Basic RGB values (255, 255, 255)
    r = 255
    g = 255
    b = 255

    # Apply intensity scaling and cap at MAX_BRIGHTNESS
    r = clamp(int(r * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)
    g = clamp(int(g * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)
    b = clamp(int(b * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)

    # Fixed sunrise at 6:00 AM (360 min), sunset at 6:00 PM (1080 min)
    sunrise_time = 360
    sunset_complete_time = 1080
    total_day_minutes = 720  # 12 hours

    minutes_since_sunrise = minute - sunrise_time

    if sunrise_time <= minute <= sunset_complete_time:
        # Position sun from x=-4 (sunrise) to x=59 (sunset)
        # Total travel: 63 positions over 720 minutes
        travel_range = 63
        x = -4 + (minutes_since_sunrise / (total_day_minutes - 1)) * travel_range

    if SUN_COLOR_MODE == "CUSTOM":
        r, g, b = CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B
    if SUN_COLOR_MODE == "BLUE":
        r = 0
        g = 0
        # Keep the calculated b value unchanged
    return x, y, size, r, g, b


def get_sun_position(minute):
    if SOLAR_MODE == "SCIENTIFIC":
        return get_scientific_sun_position(minute)
    return get_basic_sun_position(minute)


def update_rotation_parameters():
    global DEGREES_PER_IMAGE, ROTATION_INCREMENT_DEGREES, ROTATION_STEP_INTERVAL_MS
    global FINE_ROTATION_INCREMENT_DEGREES, FINE_ROTATION_STEP_INTERVAL_MS
    global STILLS_IMAGING_INTERVAL_SEC
    DEGREES_PER_IMAGE = 360.0 / max(1, IMAGES_PER_ROTATION)
    total_time = ROTATION_SPEED_PRESET_TABLE.get(ROTATION_SPEED_PRESET, 60.0)
    # Fine-grained rotation for smooth movement
    num_fine_steps = int(360.0 / FINE_ROTATION_INCREMENT_DEGREES)
    fine_step_interval = (total_time * 1000) / num_fine_steps
    if fine_step_interval < MIN_FINE_ROTATION_STEP_INTERVAL_MS:
        fine_step_interval = MIN_FINE_ROTATION_STEP_INTERVAL_MS
        FINE_ROTATION_INCREMENT_DEGREES = 360.0 / (total_time * 1000 / fine_step_interval)
    FINE_ROTATION_STEP_INTERVAL_MS = int(fine_step_interval)
    # Legacy coarse parameters
    ROTATION_INCREMENT_DEGREES = DEGREES_PER_IMAGE
    ROTATION_STEP_INTERVAL_MS = int((total_time / max(1, IMAGES_PER_ROTATION)) * 1000)
    STILLS_IMAGING_INTERVAL_SEC = ROTATION_STEP_INTERVAL_MS / 1000.0


# ======================================================
# SolarSimulator Class
# ======================================================

class SolarSimulator:
    """Main simulation orchestrator."""

    def __init__(self, hw, ble=None):
        self.hw = hw
        self.ble = ble
        self.program = ProgramEngine(output_fn=self.output)

        # Time state
        self.start_real_time_ms = ticks_ms()
        self.frozen_sim_time_minutes = 0
        self.frozen_abs_sim_time = 0
        self.frozen_time_initialized = False
        self.last_printed_minute = -1

        # Servo state machines
        self.servo2_state = 'IDLE'
        self.servo2_trigger_start_ms = 0
        self.last_servo2_trigger_ms = 0
        self.servo2_controlled_by_rotation = False
        self.servo2_using_lighting = False

        self.servo3_state = 'IDLE'
        self.servo3_trigger_start_ms = 0
        self.last_servo3_trigger_ms = 0
        self.servo3_using_lighting = False

        # Rotation state
        self.rotation_state = 'IDLE'
        self.rotation_in_progress = False
        self.current_rotation_angle = 0.0
        self.last_rotation_absolute_time = 0
        self.last_rotation_real_ms = 0           # Real-time tracking for cycle scheduling
        self.manual_rotation_triggered = False
        self.last_rotation_step_time_ms = 0
        self.camera_trigger_started_ms = 0
        self.return_angle = 0.0
        self.last_stills_trigger_ms = 0

        # Lighting state
        self.camera_lighting_active = False
        self.rotation_lighting_active = False
        self.camera_light_hold_until_ms = 0

        # Panel override
        self.manual_panel_override_active = False
        self.manual_panel_override_until_ms = 0

        # Profile tracking
        self.loaded_profile_name = None

        # Serial input buffer
        self.serial_buffer = ""

    def output(self, text):
        """Route output to print and optionally BLE."""
        print(text)
        if self.ble and self.ble.connected and not self.ble.output_paused:
            try:
                self.ble.send_response(text + '\n')
            except Exception:
                pass

    def get_settings_dict(self):
        """Build dict of all saveable settings from current globals."""
        return {
            "START_TIME_HHMM": START_TIME_HHMM,
            "TIME_SCALE": TIME_SCALE,
            "INTENSITY_SCALE": INTENSITY_SCALE,
            "SIMULATION_DATE": SIMULATION_DATE,
            "LATITUDE": LATITUDE,
            "SOLAR_MODE": SOLAR_MODE,
            "SUN_COLOR_MODE": SUN_COLOR_MODE,
            "DUAL_SUN_ENABLED": DUAL_SUN_ENABLED,
            "ROTATION_ENABLED": ROTATION_ENABLED,
            "ROTATION_CAPTURE_MODE": ROTATION_CAPTURE_MODE,
            "ROTATION_CYCLE_INTERVAL_MINUTES": ROTATION_CYCLE_INTERVAL_MINUTES,
            "SERVO2_INTERVAL_DAY_SEC": SERVO2_INTERVAL_DAY_SEC,
            "SERVO2_INTERVAL_NIGHT_SEC": SERVO2_INTERVAL_NIGHT_SEC,
            "SERVO3_INTERVAL_DAY_SEC": SERVO3_INTERVAL_DAY_SEC,
            "SERVO3_INTERVAL_NIGHT_SEC": SERVO3_INTERVAL_NIGHT_SEC,
            "ROTATION_CAMERA_SERVO": ROTATION_CAMERA_SERVO,
            "RESTART_AFTER_LOAD": RESTART_AFTER_LOAD,
            "STILLS_IMAGING_INTERVAL_SEC": STILLS_IMAGING_INTERVAL_SEC,
            "CAMERA_TRIGGER_HOLD_MS": CAMERA_TRIGGER_HOLD_MS,
            "ROTATION_SPEED_PRESET": ROTATION_SPEED_PRESET,
            "IMAGES_PER_ROTATION": IMAGES_PER_ROTATION,
            "DEGREES_PER_IMAGE": DEGREES_PER_IMAGE,
            "ROTATION_INCREMENT_DEGREES": ROTATION_INCREMENT_DEGREES,
            "ROTATION_STEP_INTERVAL_MS": ROTATION_STEP_INTERVAL_MS,
            "ROTATION_AT_NIGHT": ROTATION_AT_NIGHT,
            "CUSTOM_SUN_R": CUSTOM_SUN_R,
            "CUSTOM_SUN_G": CUSTOM_SUN_G,
            "CUSTOM_SUN_B": CUSTOM_SUN_B,
            "PROGRAM_ENABLED": self.program.program_enabled,
            "PROGRAM_REPEATS": self.program.program_repeats,
            "PROGRAM_STEPS": self.program.program_steps,
        }

    def print_status(self):
        """Print full status report (RP2040-compatible format for HTML parser).

        Collects all lines and sends as a single BLE batch to avoid
        fragmenting ~30 lines into individual notifications.
        """
        now = ticks_ms()
        et, tod = get_sim_time(START_TIME_HHMM, ticks_diff(now, self.start_real_time_ms), TIME_SCALE)
        if TIME_SCALE == 0:
            tod = self.frozen_sim_time_minutes
        h = int(tod // 60) % 24
        m = int(tod % 60)

        lines = []
        def o(text):
            print(text)
            lines.append(text)

        o("--- System Status ---")

        o("-- Simulation & Time --")
        o(f"  (Re)Start Time: {START_TIME_HHMM:04d}")
        o(f"  Sim Time: {h:02d}:{m:02d}")
        o(f"  Time Scale: {TIME_SCALE}x")
        try:
            speed_name = get_speed_name(TIME_SCALE)
        except Exception:
            speed_name = "Unknown"
        o(f"  Speed Name: {speed_name}")
        o(f"  Program Enabled: {self.program.program_enabled}")
        o(f"  Restart After Profile Load: {RESTART_AFTER_LOAD}")
        o(f"  Auto-Load Latest Profile: {AUTO_LOAD_LATEST_PROFILE}")
        o(f"  Loaded Profile: {self.loaded_profile_name if self.loaded_profile_name else '(none - using defaults)'}")

        o("-- Environment & Sun --")
        o(f"  Solar Mode: {SOLAR_MODE}")
        o(f"  Intensity Scale: {INTENSITY_SCALE}")
        o(f"  Sun Color Mode: {SUN_COLOR_MODE}")
        o(f"  Dual Sun Enabled: {DUAL_SUN_ENABLED}")
        if SUN_COLOR_MODE == "CUSTOM":
            o(f"  Custom Sun RGB: ({CUSTOM_SUN_R}, {CUSTOM_SUN_G}, {CUSTOM_SUN_B})")

        # Sunrise/sunset for sun arc visualisation
        rise_h = int(max(0, SUNRISE_MINUTES) // 60)
        rise_m = int(max(0, SUNRISE_MINUTES) % 60)
        set_h = int(min(1439, SUNSET_MINUTES) // 60)
        set_m = int(min(1439, SUNSET_MINUTES) % 60)
        o(f"  sunrise: {rise_h:02d}:{rise_m:02d}, sunset: {set_h:02d}:{set_m:02d}")

        o("-- Hardware & Imaging --")
        # Determine active period (day/night)
        sun_x, _, sun_size, _, _, _ = get_sun_position(tod)
        half = sun_size // 2
        sun_visible = (sun_x + half > 0) and (sun_x - half < 56)
        active = "DAY" if sun_visible else "NIGHT"

        s2d = f"{SERVO2_INTERVAL_DAY_SEC}s" if SERVO2_INTERVAL_DAY_SEC > 0 else "disabled"
        s2n = f"{SERVO2_INTERVAL_NIGHT_SEC}s" if SERVO2_INTERVAL_NIGHT_SEC > 0 else "disabled"
        o(f"  Servo 2: Day {s2d} | Night {s2n} [{active} ACTIVE]")

        s3d = f"{SERVO3_INTERVAL_DAY_SEC}s" if SERVO3_INTERVAL_DAY_SEC > 0 else "disabled"
        s3n = f"{SERVO3_INTERVAL_NIGHT_SEC}s" if SERVO3_INTERVAL_NIGHT_SEC > 0 else "disabled"
        o(f"  Servo 3: Day {s3d} | Night {s3n} [{active} ACTIVE]")

        o("-- -- -- -- -- -- -- --")
        o(f"  Rotation Enabled: {ROTATION_ENABLED}")
        o(f"  Rotation Imaging Servo: {ROTATION_CAMERA_SERVO}")
        o(f"  Rotation Interval: {ROTATION_CYCLE_INTERVAL_MINUTES} sim min")
        o(f"  Images per Rotation: {IMAGES_PER_ROTATION}")
        o(f"  Degrees per Image: {DEGREES_PER_IMAGE:.2f}")
        o(f"  Rotation at Night: {ROTATION_AT_NIGHT}")
        o(f"  Rotation Speed Preset: {ROTATION_SPEED_PRESET} ({ROTATION_SPEED_PRESET_TABLE[ROTATION_SPEED_PRESET]}s/360deg)")
        o(f"  Rotation Imaging Mode: {ROTATION_CAPTURE_MODE}")
        o(f"  Camera Lighting Panels: {CAMERA_LIGHTING_PANELS}")
        o(f"  Camera Light RGB: ({CAMERA_LIGHT_R}, {CAMERA_LIGHT_G}, {CAMERA_LIGHT_B})")
        o(f"  Rotation Light RGB: ({ROTATION_LIGHT_R}, {ROTATION_LIGHT_G}, {ROTATION_LIGHT_B})")
        o(f"  1:1 Servo-to-sample rotation ratio: {SERVO_1TO1_RATIO}")
        o(f"  Rotation Trigger Hold: {CAMERA_TRIGGER_HOLD_MS} ms")
        o("-----------------------")

        # Program configuration
        if self.program.program_enabled:
            o("-- Program Configuration --")
            o(f"  Program Repeats: {self.program.program_repeats}")
            o(f"  Program Running: {self.program.program_running}")
            if self.program.program_running:
                o(f"  Program Current Step: {self.program.current_step + 1}/{len(self.program.program_steps)}")
            o(f"  Number of Steps: {len(self.program.program_steps)}")
            if self.program.program_steps:
                try:
                    chunk_size = 5
                    steps = self.program.program_steps
                    for i in range(0, len(steps), chunk_size):
                        chunk = steps[i:i + chunk_size]
                        s = i + 1
                        e = min(i + chunk_size, len(steps))
                        o(f"  Program Steps ({s}-{e}): {json.dumps(chunk)}")
                except Exception:
                    o("  Program Steps: (error serializing)")
        else:
            o("-- Program Configuration --")
            o(f"  Program Repeats: {self.program.program_repeats}")
            o("  Program Steps: (none - program disabled)")
        o("-----------------------")


        # Send entire status dump as a single BLE batch
        if self.ble and self.ble.connected and not self.ble.output_paused:
            try:
                self.ble.send_batch(lines)
            except Exception:
                pass

    # ==========================================================
    # Command Handler
    # ==========================================================

    def handle_command(self, command_str):
        global TIME_SCALE, INTENSITY_SCALE, DUAL_SUN_ENABLED, SOLAR_MODE
        global SUN_COLOR_MODE, SIMULATION_DATE, LATITUDE, START_TIME_HHMM
        global ROTATION_ENABLED, ROTATION_CYCLE_INTERVAL_MINUTES, ROTATION_CAPTURE_MODE
        global SERVO2_INTERVAL_DAY_SEC, SERVO2_INTERVAL_NIGHT_SEC
        global SERVO3_INTERVAL_DAY_SEC, SERVO3_INTERVAL_NIGHT_SEC
        global RESTART_AFTER_LOAD, AUTO_LOAD_LATEST_PROFILE, SERVO_1TO1_RATIO
        global STILLS_IMAGING_INTERVAL_SEC, CAMERA_TRIGGER_HOLD_MS
        global ROTATION_INCREMENT_DEGREES, ROTATION_STEP_INTERVAL_MS
        global IMAGES_PER_ROTATION, DEGREES_PER_IMAGE, ROTATION_SPEED_PRESET
        global ROTATION_CAMERA_SERVO, ROTATION_AT_NIGHT
        global CAMERA_LIGHTING_PANELS, CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B
        global ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B
        global CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B

        # Fast path for profile upload data lines (avoid lowering/splitting large data)
        if command_str.startswith('WP:'):
            if hasattr(self, '_wp_lines') and self._wp_lines is not None:
                self._wp_lines.append(command_str[3:])
            return
        # Continuation chunk for long lines split across BLE writes (>480 bytes)
        if command_str.startswith('WPC:'):
            if hasattr(self, '_wp_lines') and self._wp_lines is not None and len(self._wp_lines) > 0:
                self._wp_lines[-1] += command_str[4:]
            return

        parts = command_str.lower().strip().split()
        if not parts:
            return
        command = parts[0]

        try:
            # === SET commands ===
            if command == "set" and len(parts) >= 3:
                param, value = parts[1], parts[2]
                self._handle_set(param, value, parts)

            # === JUMP commands ===
            elif command == "jump" and len(parts) >= 2:
                self._handle_jump(parts)

            # === TOGGLE commands ===
            elif command == "toggle" and len(parts) == 2:
                self._handle_toggle(parts[1])

            # === TRIGGER commands ===
            elif command == "trigger" and len(parts) == 2:
                self._handle_trigger(parts[1])

            # === PROGRAM STATUS ===
            elif command == "program" and len(parts) == 2 and parts[1] == "status":
                self.output(f"PROGRAM_ENABLED: {self.program.program_enabled}")
                self.output(f"PROGRAM_REPEATS: {self.program.program_repeats}")
                self.output("PROGRAM_STEPS:")
                for i, step in enumerate(self.program.program_steps):
                    self.output(f"  Step {i+1}: {step}")

            # === STATUS ===
            elif command == "status":
                # Debounce: the browser polls every 1-4s but each response is
                # ~35 lines of BLE notifications.  If responses stack up faster
                # than they can be sent, the BLE notification pipeline overflows.
                now_cmd = ticks_ms()
                if not hasattr(self, '_last_status_ms') or ticks_diff(now_cmd, self._last_status_ms) > 5000:
                    self._last_status_ms = now_cmd
                    self.print_status()

            # === FILL PANEL ===
            elif command == "fillpanel" and len(parts) >= 4:
                r, g, b = clamp(int(parts[1])), clamp(int(parts[2])), clamp(int(parts[3]))
                dur = float(parts[4]) if len(parts) >= 5 else 30
                self.manual_panel_override_until_ms = self.hw.fill_panel(r, g, b, dur)
                self.manual_panel_override_active = True
                self.output(f"[SERIAL CMD] Panel filled RGB({r},{g},{b}) for {dur}s")

            # === LIGHTING ===
            elif command == "light":
                self._handle_light(parts)

            # === PROFILES ===
            elif command == "saveprofile":
                if len(parts) >= 2:
                    note = " ".join(parts[2:]) if len(parts) > 2 else ""
                    self.program.save_profile(parts[1], self.get_settings_dict(), note)
                else:
                    self.output("[SERIAL CMD] Usage: saveprofile <name> [note]")

            elif command == "loadprofile":
                if len(parts) == 2:
                    self._do_load_profile(parts[1])
                else:
                    self.output("[SERIAL CMD] Usage: loadprofile <name>")

            elif command == "listprofiles":
                self.program.list_profiles()

            elif command == "profiledelete":
                if len(parts) >= 2:
                    self.program.delete_profile(parts[1])
                else:
                    self.output("[SERIAL CMD] Usage: profiledelete <name>")

            elif command == "writeprofile":
                if len(parts) >= 2 and parts[1] == "commit":
                    self._writeprofile_commit()
                elif len(parts) >= 2 and parts[1] == "abort":
                    self._writeprofile_abort()
                elif len(parts) >= 2:
                    self._writeprofile_begin(command_str.strip().split()[1])
                else:
                    self.output("[SERIAL CMD] Usage: writeprofile <name> | commit | abort")

            elif command == "savelog":
                self._handle_savelog(parts)

            # === RESTART / RESET ===
            elif command == "restart":
                self.output("[SERIAL CMD] Restarting simulation logic...")
                init_solar_day()
                self.start_real_time_ms = ticks_ms()
                self.output("[SERIAL CMD] Simulation restarted. Time anchor reset.")

            elif command == "reset":
                self.output("[SERIAL CMD] Performing hard reset...")
                sleep_ms(100)
                import machine
                machine.reset()

            # === HELP ===
            elif command == "help" and len(parts) > 1 and parts[1] == "all":
                self.output("--- Command Summary ---")
                self.output("Set: time, speed, intensity, date, latitude, solarmode, suncolor, starttime, autoload, ...")
                self.output("Toggle: dualsun, program, rotation, restartafterload, 1to1ratio")
                self.output("Program: jump nextstep, jump step <n>, listprofiles, loadprofile, saveprofile, profiledelete")
                self.output("Utility: fillpanel, light camera/rotation on/off, trigger servo2/servo3/rotation, status, restart, reset")
                self.output("-----------------------")

            else:
                self.output(f"[SERIAL CMD] Error: Unknown command '{command_str}'")

        except (ValueError, IndexError) as e:
            self.output(f"[SERIAL CMD] Error processing '{command_str}': {e}")

    # --- SET handler ---
    def _handle_set(self, param, value, parts):
        global TIME_SCALE, INTENSITY_SCALE, SOLAR_MODE, SUN_COLOR_MODE
        global SIMULATION_DATE, LATITUDE, START_TIME_HHMM
        global ROTATION_CYCLE_INTERVAL_MINUTES, ROTATION_CAPTURE_MODE
        global SERVO2_INTERVAL_DAY_SEC, SERVO2_INTERVAL_NIGHT_SEC
        global SERVO3_INTERVAL_DAY_SEC, SERVO3_INTERVAL_NIGHT_SEC
        global AUTO_LOAD_LATEST_PROFILE, ROTATION_CAMERA_SERVO, ROTATION_AT_NIGHT
        global STILLS_IMAGING_INTERVAL_SEC, CAMERA_TRIGGER_HOLD_MS
        global ROTATION_INCREMENT_DEGREES, ROTATION_STEP_INTERVAL_MS
        global IMAGES_PER_ROTATION, ROTATION_SPEED_PRESET
        global CAMERA_LIGHTING_PANELS
        global CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B
        global ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B
        global CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B

        if param == "speed":
            new_speed = float(value)
            now = ticks_ms()
            _, tod = get_sim_time(START_TIME_HHMM, ticks_diff(now, self.start_real_time_ms), TIME_SCALE)
            old = TIME_SCALE
            TIME_SCALE = new_speed
            if TIME_SCALE == 0:
                self.frozen_sim_time_minutes = tod
            else:
                preserved = self.frozen_sim_time_minutes if old == 0 else tod
                self.start_real_time_ms = reanchor_start_time(preserved, TIME_SCALE, now, START_TIME_HHMM, self.start_real_time_ms)
            self.output(f"[SERIAL CMD] Time scale set to {get_speed_name(TIME_SCALE)}")

        elif param == "time":
            t = int(value)
            tm = (t // 100) * 60 + (t % 100)
            if not 0 <= tm < 1440:
                self.output("[SERIAL CMD] Error: Invalid time.")
                return
            now = ticks_ms()
            if TIME_SCALE == 0:
                self.frozen_sim_time_minutes = tm
            else:
                self.start_real_time_ms = reanchor_start_time(tm, TIME_SCALE, now, START_TIME_HHMM, self.start_real_time_ms)
            self.output(f"[SERIAL CMD] Time jumped to {tm//60:02d}:{tm%60:02d}")

        elif param == "starttime":
            t = int(value)
            if not (0 <= t <= 2359 and t % 100 < 60):
                self.output("[SERIAL CMD] Error: Invalid time.")
                return
            now = ticks_ms()
            _, tod = get_sim_time(START_TIME_HHMM, ticks_diff(now, self.start_real_time_ms), TIME_SCALE)
            START_TIME_HHMM = t
            if TIME_SCALE > 0:
                self.start_real_time_ms = reanchor_start_time(tod, TIME_SCALE, now, START_TIME_HHMM, self.start_real_time_ms)
            self.output(f"[SERIAL CMD] Start time set to {START_TIME_HHMM:04d}")

        elif param == "intensity":
            v = float(value)
            if v >= 0:
                INTENSITY_SCALE = v
                self.output(f"[SERIAL CMD] Global intensity set to {INTENSITY_SCALE}")

        elif param == "date":
            v = int(value)
            if 20000101 <= v <= 21001231:
                SIMULATION_DATE = v
                init_solar_day()
                self.output(f"[SERIAL CMD] Simulation date set to {SIMULATION_DATE}")

        elif param == "latitude":
            v = float(value)
            if -90 <= v <= 90:
                LATITUDE = v
                init_solar_day()
                self.output(f"[SERIAL CMD] Latitude set to {LATITUDE}")

        elif param == "solarmode":
            if value in ("basic", "scientific"):
                SOLAR_MODE = value.upper()
                init_solar_day()
                self.output(f"[SERIAL CMD] Solar mode set to {SOLAR_MODE}")

        elif param == "suncolor":
            if value in ("natural", "blue"):
                SUN_COLOR_MODE = value.upper()
                init_solar_day()
                self.output(f"[SERIAL CMD] Sun color mode set to {SUN_COLOR_MODE}")
            elif value == "custom" and len(parts) == 6:
                CUSTOM_SUN_R = clamp(int(parts[3]))
                CUSTOM_SUN_G = clamp(int(parts[4]))
                CUSTOM_SUN_B = clamp(int(parts[5]))
                SUN_COLOR_MODE = "CUSTOM"
                init_solar_day()
                self.output(f"[SERIAL CMD] Sun color: CUSTOM RGB({CUSTOM_SUN_R},{CUSTOM_SUN_G},{CUSTOM_SUN_B})")

        elif param == "rotationmode":
            if value in ("stills", "video"):
                ROTATION_CAPTURE_MODE = value.upper()
                self.output(f"[SERIAL CMD] Rotation capture mode set to {ROTATION_CAPTURE_MODE}")

        elif param == "rotationinterval":
            v = int(value)
            if v > 0:
                ROTATION_CYCLE_INTERVAL_MINUTES = v
                self.output(f"[SERIAL CMD] Rotation interval set to {v} sim minutes")

        elif param == "rotationatnight":
            ROTATION_AT_NIGHT = value.lower() in ("true", "on", "1")
            self.output(f"[SERIAL CMD] ROTATION_AT_NIGHT set to {ROTATION_AT_NIGHT}")

        elif param == "rotationcameraservo":
            if value in ("2", "3"):
                ROTATION_CAMERA_SERVO = int(value)
                self.output(f"[SERIAL CMD] Rotation camera servo set to {ROTATION_CAMERA_SERVO}")

        elif param == "autoload":
            v = value.lower()
            if v in ("on", "true", "1"):
                AUTO_LOAD_LATEST_PROFILE = True
            elif v in ("off", "false", "0"):
                AUTO_LOAD_LATEST_PROFILE = False
            else:
                self.output("[SERIAL CMD] Error: autoload must be on/off")
                return
            ProgramEngine.save_autoload_preference(AUTO_LOAD_LATEST_PROFILE)
            self.output(f"[SERIAL CMD] Auto-load set to {AUTO_LOAD_LATEST_PROFILE} (persisted)")

        elif param in ("servo2dayinterval", "servo2nightinterval", "servo3dayinterval", "servo3nightinterval"):
            v = int(value)
            if v >= 0:
                gn = {"servo2dayinterval": "SERVO2_INTERVAL_DAY_SEC",
                      "servo2nightinterval": "SERVO2_INTERVAL_NIGHT_SEC",
                      "servo3dayinterval": "SERVO3_INTERVAL_DAY_SEC",
                      "servo3nightinterval": "SERVO3_INTERVAL_NIGHT_SEC"}[param]
                globals()[gn] = v
                self.output(f"[SERIAL CMD] {gn} set to {v}s")

        elif param == "rot_speed":
            if value in ROTATION_SPEED_PRESET_TABLE:
                ROTATION_SPEED_PRESET = value
                update_rotation_parameters()
                self.output(f"[SERIAL CMD] Rotation speed preset: {ROTATION_SPEED_PRESET}")

        elif param == "images_per_rotation":
            v = int(value)
            if 2 <= v <= 360:
                IMAGES_PER_ROTATION = v
                update_rotation_parameters()
                self.output(f"[SERIAL CMD] Images/rotation: {IMAGES_PER_ROTATION}")

        elif param == "rot_stills_intv":
            v = float(value)
            if v > 0:
                STILLS_IMAGING_INTERVAL_SEC = v
                self.output(f"[SERIAL CMD] Stills interval: {v}s")

        elif param == "rot_trig_hold":
            v = int(value)
            if v > 0:
                CAMERA_TRIGGER_HOLD_MS = v
                self.output(f"[SERIAL CMD] Trigger hold: {v}ms")

        elif param == "rot_inc_deg":
            v = float(value)
            if v > 0:
                ROTATION_INCREMENT_DEGREES = v
                self.output(f"[SERIAL CMD] Rotation increment: {v}°")

        elif param == "rot_step_intv":
            v = int(value)
            if v > 0:
                ROTATION_STEP_INTERVAL_MS = v
                self.output(f"[SERIAL CMD] Rotation step interval: {v}ms")

        elif param == "cameralightingpanels":
            allowed = ["ALL", "MIDDLE5", "MIDDLE3", "OUTER2", "OUTER4"]
            if value.upper() in allowed:
                CAMERA_LIGHTING_PANELS = value.upper()
                self.output(f"[SERIAL CMD] Camera lighting panels: {CAMERA_LIGHTING_PANELS}")

        elif param == "cameralightrgb" and len(parts) >= 5:
            CAMERA_LIGHT_R = clamp(int(parts[2]))
            CAMERA_LIGHT_G = clamp(int(parts[3]))
            CAMERA_LIGHT_B = clamp(int(parts[4]))
            self.output(f"[SERIAL CMD] Camera light RGB: ({CAMERA_LIGHT_R},{CAMERA_LIGHT_G},{CAMERA_LIGHT_B})")

        elif param == "rotationlightrgb" and len(parts) >= 5:
            ROTATION_LIGHT_R = clamp(int(parts[2]))
            ROTATION_LIGHT_G = clamp(int(parts[3]))
            ROTATION_LIGHT_B = clamp(int(parts[4]))
            self.output(f"[SERIAL CMD] Rotation light RGB: ({ROTATION_LIGHT_R},{ROTATION_LIGHT_G},{ROTATION_LIGHT_B})")

        elif param == "programenabled":
            self.program.program_enabled = value.lower() in ("on", "true", "1")
            self.output(f"[SERIAL CMD] Program enabled: {self.program.program_enabled}")

        elif param == "programrepeats":
            self.program.program_repeats = int(value)
            self.output(f"[SERIAL CMD] Program repeats: {self.program.program_repeats}")

        else:
            self.output(f"[SERIAL CMD] Error: Unknown parameter '{param}'")

    # --- TOGGLE handler ---
    def _handle_toggle(self, target):
        global DUAL_SUN_ENABLED, ROTATION_ENABLED, RESTART_AFTER_LOAD, SERVO_1TO1_RATIO
        if target == "dualsun":
            DUAL_SUN_ENABLED = not DUAL_SUN_ENABLED
            self.output(f"[SERIAL CMD] Dual sun: {DUAL_SUN_ENABLED}")
        elif target == "program":
            self.program.program_enabled = not self.program.program_enabled
            self.output(f"[SERIAL CMD] Program: {self.program.program_enabled}")
        elif target == "rotation":
            ROTATION_ENABLED = not ROTATION_ENABLED
            self.output(f"[SERIAL CMD] Rotation: {ROTATION_ENABLED}")
        elif target == "restartafterload":
            RESTART_AFTER_LOAD = not RESTART_AFTER_LOAD
            self.output(f"[SERIAL CMD] Restart after load: {RESTART_AFTER_LOAD}")
        elif target == "1to1ratio":
            SERVO_1TO1_RATIO = not SERVO_1TO1_RATIO
            self.output(f"[SERIAL CMD] 1:1 ratio: {SERVO_1TO1_RATIO}")
        else:
            self.output(f"[SERIAL CMD] Error: Unknown toggle '{target}'")

    # --- JUMP handler ---
    def _handle_jump(self, parts):
        global TIME_SCALE
        if not self.program.program_running:
            if self.program.program_enabled and self.program.program_steps:
                self.program.start()
                self.output("[SERIAL CMD] Program auto-started for jump command.")
            else:
                self.output("[SERIAL CMD] Error: Program not running.")
                return
        target = parts[1]
        if target == "nextstep":
            idx = (self.program.current_step + 1) % len(self.program.program_steps)
            self._jump_to_step(idx)
        elif target == "step" and len(parts) == 3:
            n = int(parts[2])
            if 1 <= n <= len(self.program.program_steps):
                self._jump_to_step(n - 1)
            else:
                self.output(f"[SERIAL CMD] Error: Step must be 1-{len(self.program.program_steps)}")
        else:
            self.output("[SERIAL CMD] Error: Use 'jump nextstep' or 'jump step <n>'")

    def _jump_to_step(self, idx):
        global TIME_SCALE
        self.program.current_step = idx
        self.program.current_step_repeat = 0
        step = self.program.program_steps[idx]
        t_hhmm = step["sim_time_hhmm"]
        t_min = (t_hhmm // 100) * 60 + (t_hhmm % 100)
        now = ticks_ms()
        new_speed = step.get("speed", 1)
        if new_speed == 0:
            self.frozen_sim_time_minutes = t_min
        else:
            TIME_SCALE = new_speed
            self.start_real_time_ms = reanchor_start_time(t_min, new_speed, now, START_TIME_HHMM, self.start_real_time_ms)
        self.program.step_start_sim_time = 0
        self.output(f"[SERIAL CMD] Jumped to step {idx+1} at {t_hhmm:04d}")

    # --- TRIGGER handler ---
    def _handle_trigger(self, target):
        now = ticks_ms()
        if target == "servo2":
            if self.servo2_state != 'IDLE' or self.servo2_controlled_by_rotation:
                self.output("[SERIAL CMD] Error: Servo 2 is currently busy.")
                return
            self.servo2_state = 'TRIGGERED'
            self.servo2_trigger_start_ms = now
            self.last_servo2_trigger_ms = now
            # Activate camera lighting before trigger
            if CAMERA_LIGHTING_ENABLED and not self.rotation_lighting_active:
                self.camera_lighting_active = True
                self.servo2_using_lighting = True
                self.hw.apply_lighting(CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B, CAMERA_LIGHTING_PANELS)
            self.hw.set_servo_angle(self.hw.servo_pwm_2, CAMERA_SERVO_TRIGGER_ANGLE)
            self.output("[SERIAL CMD] Manually triggering photo with Servo 2.")
        elif target == "servo3":
            if self.servo3_state != 'IDLE':
                self.output("[SERIAL CMD] Error: Servo 3 is currently busy.")
                return
            self.servo3_state = 'TRIGGERED'
            self.servo3_trigger_start_ms = now
            self.last_servo3_trigger_ms = now
            # Activate camera lighting before trigger
            if SERVO3_LIGHTING_ENABLED and not self.rotation_lighting_active:
                self.servo3_using_lighting = True
                self.camera_lighting_active = True
                self.hw.apply_lighting(CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B, CAMERA_LIGHTING_PANELS)
            self.hw.set_servo_angle(self.hw.servo_pwm_3, CAMERA_SERVO_TRIGGER_ANGLE)
            self.output("[SERIAL CMD] Manually triggering photo with Servo 3.")
        elif target == "rotation":
            if self.rotation_in_progress:
                self.output("[SERIAL CMD] Error: Rotation cycle is already in progress.")
                return
            self.last_rotation_real_ms = 0  # Reset real-time scheduler so cycle starts immediately
            self.rotation_state = 'IDLE'
            self.manual_rotation_triggered = True
            self.output("[SERIAL CMD] Manual rotation imaging cycle triggered.")
        else:
            self.output(f"[SERIAL CMD] Error: Unknown target '{target}'")

    # --- LIGHT handler ---
    def _handle_light(self, parts):
        if len(parts) >= 3:
            target, state = parts[1], parts[2]
            if target == "camera":
                if state == "on":
                    self.camera_lighting_active = True
                    panels = self.hw.apply_lighting(CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B, CAMERA_LIGHTING_PANELS)
                    self.output(f"[SERIAL CMD] Camera lighting ON on panels {panels}")
                elif state == "off":
                    self.camera_lighting_active = False
                    if not self.rotation_lighting_active:
                        self.hw.deactivate_lighting()
                    self.output("[SERIAL CMD] Camera lighting OFF")
            elif target == "rotation":
                if state == "on":
                    self.rotation_lighting_active = True
                    panels = self.hw.apply_lighting(ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B, CAMERA_LIGHTING_PANELS)
                    self.output(f"[SERIAL CMD] Rotation lighting ON on panels {panels}")
                elif state == "off":
                    self.rotation_lighting_active = False
                    self.hw.deactivate_lighting()
                    self.output("[SERIAL CMD] Rotation lighting OFF")

    # --- LOAD PROFILE ---
    def _do_load_profile(self, name):
        global TIME_SCALE, INTENSITY_SCALE, DUAL_SUN_ENABLED, SOLAR_MODE
        global SUN_COLOR_MODE, SIMULATION_DATE, LATITUDE, START_TIME_HHMM
        global ROTATION_ENABLED, ROTATION_CYCLE_INTERVAL_MINUTES, ROTATION_CAPTURE_MODE
        global SERVO2_INTERVAL_DAY_SEC, SERVO2_INTERVAL_NIGHT_SEC
        global SERVO3_INTERVAL_DAY_SEC, SERVO3_INTERVAL_NIGHT_SEC
        global RESTART_AFTER_LOAD, ROTATION_CAMERA_SERVO, ROTATION_AT_NIGHT
        global CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B

        validated = self.program.load_profile(name)
        if validated is None:
            return
        g = globals()
        for key, value in validated.items():
            if key == "PROGRAM_STEPS":
                self.program.program_steps = value
            elif key == "PROGRAM_REPEATS":
                self.program.program_repeats = value
            elif key == "PROGRAM_ENABLED":
                self.program.program_enabled = value
            else:
                g[key] = value
        update_rotation_parameters()
        self.output("[SERIAL CMD] Settings applied.")
        self.loaded_profile_name = f"{name}.txt"

        if RESTART_AFTER_LOAD:
            self.output("[SERIAL CMD] Restarting simulation...")
            init_solar_day()
            self.start_real_time_ms = ticks_ms()
            self.output("[SERIAL CMD] Simulation restarted.")

    # --- WRITEPROFILE (BLE profile upload) ---
    def _writeprofile_begin(self, filename):
        """Start a profile write session. Initialises line buffer."""
        import re
        fn = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        if not fn.lower().endswith('.txt'):
            fn += '.txt'
        self._wp_filename = fn
        self._wp_lines = []
        # Pause BLE output during write session to prevent outgoing
        # notifications (status dumps, SimTime) from colliding with
        # incoming WP: writes and crashing the BLE stack.
        if self.ble:
            self.ble.output_paused = True
        self.output(f"[SERIAL CMD] writeprofile: ready for '{fn}'")

    def _writeprofile_commit(self):
        """Write buffered profile lines to file, then load in-place."""
        global AUTO_LOAD_LATEST_PROFILE
        if not hasattr(self, '_wp_lines') or self._wp_lines is None:
            self.output("[SERIAL CMD] writeprofile: no active session")
            return
        fn = self._wp_filename
        lines = self._wp_lines
        self._wp_lines = None
        self._wp_filename = None
        try:
            n_lines = len(lines)
            with open(fn, 'w') as f:
                for line in lines:
                    f.write(line + '\n')
            del lines
            gc.collect()
            # Briefly resume BLE output to send WRITE_OK, then re-pause
            # during profile load to prevent notification burst that crashes BLE.
            if self.ble:
                self.ble.output_paused = False
            self.output(f"[SERIAL CMD] WRITE_OK {fn} {n_lines}")
            if self.ble:
                self.ble.output_paused = True
            # Re-enable auto-load so this profile persists across reboots
            AUTO_LOAD_LATEST_PROFILE = True
            ProgramEngine.save_autoload_preference(True)
            # Load the new profile in-place (BLE output suppressed)
            base = fn[:-4] if fn.endswith('.txt') else fn
            self._do_load_profile(base)
            gc.collect()
            # Let BLE stack settle before resuming normal output
            sleep_ms(500)
            if self.ble:
                self.ble.output_paused = False
        except Exception as e:
            if self.ble:
                self.ble.output_paused = False
            self.output(f"[SERIAL CMD] writeprofile error: {e}")
            gc.collect()

    def _writeprofile_abort(self):
        """Cancel an active profile write session."""
        self._wp_lines = None
        self._wp_filename = None
        if self.ble:
            self.ble.output_paused = False
        gc.collect()
        self.output("[SERIAL CMD] writeprofile: aborted")

    # --- SAVELOG ---
    def _handle_savelog(self, parts):
        if len(parts) != 2 or len(parts[1]) != 8 or not parts[1].isdigit():
            self.output("[SERIAL CMD] Usage: savelog <yyyymmdd>")
            return
        datecode = parts[1]
        now = ticks_ms()
        _, tod = get_sim_time(START_TIME_HHMM, ticks_diff(now, self.start_real_time_ms), TIME_SCALE)
        h, m = int(tod // 60) % 24, int(tod % 60)
        fname = f"settings_{datecode}.txt"
        try:
            with open(fname, "a") as f:
                f.write(f"--- Settings {datecode} at {h:02d}:{m:02d} ---\n")
                for k, v in self.get_settings_dict().items():
                    if k in ("PROGRAM_STEPS", "PROGRAM_REPEATS", "PROGRAM_ENABLED"):
                        continue
                    f.write(f"{k} = {v}\n")
                f.write("-" * 20 + "\n\n")
            self.output(f"[SERIAL CMD] Settings logged to {fname}")
        except Exception as e:
            self.output(f"[SERIAL CMD] Error saving log: {e}")

    # ==========================================================
    # Serial Input Processing
    # ==========================================================

    def process_serial_input(self):
        """Non-blocking serial command processing using select.poll (ESP32 compatible)."""
        try:
            if not hasattr(self, '_stdin_poller'):
                import select
                self._stdin_poller = select.poll()
                self._stdin_poller.register(sys.stdin, select.POLLIN)
            while self._stdin_poller.poll(0):
                char = sys.stdin.read(1)
                if char in ('\n', '\r'):
                    if self.serial_buffer:
                        self.handle_command(self.serial_buffer)
                        self.serial_buffer = ""
                elif char is not None:
                    self.serial_buffer += char
        except Exception:
            pass
    # ==========================================================
    # Rotation Imaging State Machine
    # ==========================================================

    def update_rotation(self, now_ms, display_minutes):
        """Update the rotation cycle state machine.

        Drives a 360° imaging cycle: camera trigger → smooth rotation
        with periodic stills → dwell → smooth return.

        Cycle scheduling uses real-time intervals (ROTATION_CYCLE_INTERVAL_MINUTES
        converted to ms), so cycles start regardless of simulation speed.
        """
        # Skip if rotation disabled and not mid-cycle and no manual trigger
        if not ROTATION_ENABLED and self.rotation_state == 'IDLE' and not self.manual_rotation_triggered:
            return

        # --- Check if it's time for a new cycle (real-time based) ---
        interval_ms = ROTATION_CYCLE_INTERVAL_MINUTES * 60 * 1000
        time_for_new = (ticks_diff(now_ms, self.last_rotation_real_ms) >= interval_ms
                        or self.last_rotation_real_ms == 0)  # First run

        if self.rotation_state == 'IDLE' and time_for_new:
            # Night check
            sun_x, _, sun_size, _, _, _ = get_sun_position(display_minutes)
            half = sun_size // 2
            sun_visible = (sun_x + half > 0) and (sun_x - half < 56)
            if not sun_visible and not ROTATION_AT_NIGHT:
                self.output("Skipping rotation cycle - nighttime and ROTATION_AT_NIGHT is False")
                self.last_rotation_real_ms = now_ms
                return

            self.output(f"Starting new 360° imaging cycle")
            self.manual_rotation_triggered = False
            self.rotation_state = 'INITIAL_CAMERA_TRIGGER' if ROTATION_CAMERA_ENABLED else 'ROTATING'
            self.rotation_in_progress = True
            self.current_rotation_angle = 0

            if ROTATION_CAPTURE_MODE == "STILLS":
                self.last_stills_trigger_ms = now_ms

            if ROTATION_CAMERA_ENABLED:
                self.servo2_controlled_by_rotation = (ROTATION_CAMERA_SERVO == 2)
                self.camera_trigger_started_ms = now_ms
                cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_TRIGGER_ANGLE)
                self.output("Camera triggered")
                if ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_LIGHTING_ENABLED and not self.rotation_lighting_active:
                    self.rotation_lighting_active = True
                    self.hw.apply_lighting(ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B, CAMERA_LIGHTING_PANELS)
            else:
                self.last_rotation_step_time_ms = now_ms
                self.hw.set_servo1_angle(0, SERVO_1TO1_RATIO)
                self.output("Starting rotation (camera trigger disabled)")
                if ROTATION_LIGHTING_ENABLED and not self.rotation_lighting_active:
                    self.rotation_lighting_active = True
                    self.hw.apply_lighting(ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B, CAMERA_LIGHTING_PANELS)

        # --- State handlers ---
        if self.rotation_state == 'INITIAL_CAMERA_TRIGGER':
            if ticks_diff(now_ms, self.camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
                cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_REST_ANGLE)
                self.output("Initial camera trigger released")
                self.hw.trigger_camera_shutter(ROTATION_CAPTURE_MODE)
                self.rotation_state = 'ROTATING'
                self.last_rotation_step_time_ms = now_ms
                self.hw.set_servo1_angle(self.current_rotation_angle, SERVO_1TO1_RATIO)
                if ROTATION_CAPTURE_MODE == "VIDEO" and ROTATION_LIGHTING_ENABLED and not self.rotation_lighting_active:
                    self.rotation_lighting_active = True
                    self.hw.apply_lighting(ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B, CAMERA_LIGHTING_PANELS)

        elif self.rotation_state == 'ROTATING':
            image_angle = DEGREES_PER_IMAGE
            next_trigger_idx = int(self.current_rotation_angle // image_angle)
            next_trigger_angle = (next_trigger_idx + 1) * image_angle

            if self.current_rotation_angle < 360:
                next_angle = self.current_rotation_angle + FINE_ROTATION_INCREMENT_DEGREES
                if next_angle > next_trigger_angle - 1e-6:
                    self.current_rotation_angle = min(next_trigger_angle, 360)
                    self.hw.set_servo1_angle(self.current_rotation_angle, SERVO_1TO1_RATIO)
                    self.output(f"Rotating table to {self.current_rotation_angle:.1f} deg")
                    # STILLS trigger at image angle
                    if (ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_CAMERA_ENABLED
                            and self.current_rotation_angle < 360):
                        if ticks_diff(now_ms, self.last_stills_trigger_ms) >= STILLS_IMAGING_INTERVAL_SEC * 1000:
                            self.last_stills_trigger_ms = now_ms
                            self.last_rotation_step_time_ms = now_ms
                            self.rotation_state = 'ROTATION_CAMERA_TRIGGER'
                            self.camera_trigger_started_ms = now_ms
                            cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                            self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_TRIGGER_ANGLE)
                            self.output(f"STILLS mode: Camera trigger at {self.current_rotation_angle:.1f} deg")
                            return
                elif ticks_diff(now_ms, self.last_rotation_step_time_ms) >= FINE_ROTATION_STEP_INTERVAL_MS:
                    self.current_rotation_angle = min(next_angle, 360)
                    self.hw.set_servo1_angle(self.current_rotation_angle, SERVO_1TO1_RATIO)
                    self.last_rotation_step_time_ms = now_ms

            if self.current_rotation_angle >= 360:
                if ROTATION_CAPTURE_MODE == "VIDEO" and self.rotation_lighting_active:
                    self.rotation_lighting_active = False
                    self.hw.deactivate_lighting()
                if ROTATION_CAMERA_ENABLED and ROTATION_CAPTURE_MODE == "VIDEO":
                    self.rotation_state = 'FINAL_CAMERA_TRIGGER'
                    self.camera_trigger_started_ms = now_ms
                    cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                    self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_TRIGGER_ANGLE)
                    self.output(f"Rotation complete, triggering camera at {CAMERA_SERVO_TRIGGER_ANGLE} deg")
                else:
                    self.rotation_state = 'DWELL'
                    self.last_rotation_step_time_ms = now_ms

        elif self.rotation_state == 'ROTATION_CAMERA_TRIGGER':
            if ticks_diff(now_ms, self.camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
                cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_REST_ANGLE)
                self.output("STILLS mode: Camera trigger released")
                self.hw.trigger_camera_shutter(ROTATION_CAPTURE_MODE)
                self.rotation_state = 'ROTATING'
                self.last_rotation_step_time_ms = now_ms

        elif self.rotation_state == 'FINAL_CAMERA_TRIGGER':
            if ticks_diff(now_ms, self.camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
                cam_pwm = self.hw.get_rotation_camera_pwm(ROTATION_CAMERA_SERVO)
                self.hw.set_servo_angle(cam_pwm, CAMERA_SERVO_REST_ANGLE)
                self.output(f"Final camera trigger released, returning to {CAMERA_SERVO_REST_ANGLE} deg")
                self.hw.trigger_camera_shutter(ROTATION_CAPTURE_MODE)
                self.rotation_state = 'RETURNING'
                self.return_angle = self.current_rotation_angle
                self.last_rotation_step_time_ms = now_ms
                self.output(f"Starting gradual return to start position from {self.return_angle:.0f} deg")

        elif self.rotation_state == 'DWELL':
            if ticks_diff(now_ms, self.last_rotation_step_time_ms) >= DWELL_TIME_MS:
                if ROTATION_CAPTURE_MODE == "STILLS" and self.rotation_lighting_active:
                    self.rotation_lighting_active = False
                    self.hw.deactivate_lighting()
                self.rotation_state = 'RETURNING'
                self.return_angle = self.current_rotation_angle
                self.last_rotation_step_time_ms = now_ms

        elif self.rotation_state == 'RETURNING':
            if ticks_diff(now_ms, self.last_rotation_step_time_ms) >= RETURN_STEP_INTERVAL_MS:
                self.return_angle = max(0, self.return_angle - RETURN_STEP_DEGREES)
                self.hw.set_servo1_angle(self.return_angle, SERVO_1TO1_RATIO)
                self.last_rotation_step_time_ms = now_ms
                if self.return_angle % 90 == 0 or self.return_angle == 0:
                    self.output(f"Returning table to {self.return_angle:.0f} deg")
                if self.return_angle <= 0:
                    self.last_rotation_real_ms = now_ms
                    self.rotation_state = 'IDLE'
                    self.rotation_in_progress = False
                    self.servo2_controlled_by_rotation = False
                    self.output("Imaging cycle complete, table returned to start position")

    # ==========================================================
    # Servo State Machines
    # ==========================================================

    def update_servo2(self, now_ms, is_daytime):
        """Standalone servo 2 state machine (RP2040-compatible).

        Activates camera lighting before trigger, fires shutter on release,
        and holds lighting briefly after release.
        """
        if self.servo2_controlled_by_rotation:
            return

        if self.servo2_state == 'IDLE':
            interval = SERVO2_INTERVAL_DAY_SEC if is_daytime else SERVO2_INTERVAL_NIGHT_SEC
            if interval <= 0:
                return
            if ticks_diff(now_ms, self.last_servo2_trigger_ms) >= interval * 1000:
                self.servo2_state = 'TRIGGERED'
                self.servo2_trigger_start_ms = now_ms
                # Activate camera lighting before trigger
                if CAMERA_LIGHTING_ENABLED and not self.rotation_lighting_active:
                    self.camera_lighting_active = True
                    self.servo2_using_lighting = True
                    self.hw.apply_lighting(CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B, CAMERA_LIGHTING_PANELS)
                sleep_ms(10)  # Brief pause after lighting, before servo move
                self.hw.set_servo_angle(self.hw.servo_pwm_2, CAMERA_SERVO_TRIGGER_ANGLE)
                time_period = "night" if not is_daytime else "day"
                self.output(f"Standalone camera on servo2 trigger activated (using {time_period} interval: {interval}s)")

        elif self.servo2_state == 'TRIGGERED':
            if ticks_diff(now_ms, self.servo2_trigger_start_ms) >= SERVO2_TRIGGER_HOLD_MS:
                self.servo2_state = 'IDLE'
                self.hw.set_servo_angle(self.hw.servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
                self.output("Camera trigger released")
                self.hw.trigger_camera_shutter(ROTATION_CAPTURE_MODE)
                self.last_servo2_trigger_ms = now_ms  # Reset interval timer on release
                if self.camera_lighting_active and self.servo2_using_lighting and not self.rotation_lighting_active:
                    self.servo2_using_lighting = False
                    self.camera_light_hold_until_ms = now_ms + CAMERA_LIGHT_HOLD_MS

    def update_servo3(self, now_ms, is_daytime):
        """Standalone servo 3 state machine (RP2040-compatible).

        Operates independently of rotation and servo2. Activates camera
        lighting before trigger and holds briefly after release.
        Does NOT trigger camera shutter (servo3 is mechanical-only in RP2040).
        """
        if self.servo3_state == 'IDLE':
            interval = SERVO3_INTERVAL_DAY_SEC if is_daytime else SERVO3_INTERVAL_NIGHT_SEC
            if interval <= 0:
                return
            if ticks_diff(now_ms, self.last_servo3_trigger_ms) >= interval * 1000:
                self.servo3_state = 'TRIGGERED'
                self.servo3_trigger_start_ms = now_ms
                # Activate camera lighting if enabled and rotation lighting is not active
                if SERVO3_LIGHTING_ENABLED and not self.rotation_lighting_active:
                    self.servo3_using_lighting = True
                    self.camera_lighting_active = True
                    self.hw.apply_lighting(CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B, CAMERA_LIGHTING_PANELS)
                self.hw.set_servo_angle(self.hw.servo_pwm_3, CAMERA_SERVO_TRIGGER_ANGLE)
                time_period = "night" if not is_daytime else "day"
                self.output(f"Second camera on servo3 trigger activated (using {time_period} interval: {interval}s)")

        elif self.servo3_state == 'TRIGGERED':
            if ticks_diff(now_ms, self.servo3_trigger_start_ms) >= SERVO3_TRIGGER_HOLD_MS:
                self.servo3_state = 'IDLE'
                self.last_servo3_trigger_ms = now_ms  # Reset interval timer on release
                self.hw.set_servo_angle(self.hw.servo_pwm_3, CAMERA_SERVO_REST_ANGLE)
                if self.camera_lighting_active and self.servo3_using_lighting and not self.rotation_lighting_active:
                    self.servo3_using_lighting = False
                    self.camera_light_hold_until_ms = now_ms + CAMERA_LIGHT_HOLD_MS
                else:
                    self.servo3_using_lighting = False

    # ==========================================================
    # Auto-load & Startup
    # ==========================================================

    def attempt_autoload(self):
        global AUTO_LOAD_LATEST_PROFILE
        pref = ProgramEngine.load_autoload_preference()
        if pref is not None:
            AUTO_LOAD_LATEST_PROFILE = pref
        if not AUTO_LOAD_LATEST_PROFILE:
            return
        base, full = ProgramEngine.find_latest_profile()
        if not full:
            self.output("[AUTOLOAD] No matching profiles; using defaults.")
            return
        self.output(f"[AUTOLOAD] Loading '{full}'...")
        self._do_load_profile(base)

    # ==========================================================
    # Main Simulation Loop
    # ==========================================================

    def run(self):
        """Main simulation loop."""
        global TIME_SCALE

        # Init frozen time if starting in HOLD
        if TIME_SCALE == 0 and not self.frozen_time_initialized:
            self.frozen_sim_time_minutes = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
            self.frozen_time_initialized = True

        init_solar_day()
        update_rotation_parameters()  # Compute fine rotation timing from defaults
        self.start_real_time_ms = ticks_ms()
        last_update_ms = self.start_real_time_ms
        update_interval_ms = 1000
        gc_counter = 0  # periodic GC to prevent fragmentation

        self.output("Solar Simulator Starting!   **** Type \"help all\" for commands. ****")

        while True:
            now_ms = ticks_ms()
            elapsed_ms = ticks_diff(now_ms, self.start_real_time_ms)
            abs_sim_time, time_of_day = get_sim_time(START_TIME_HHMM, elapsed_ms, TIME_SCALE)

            # Determine display time
            if TIME_SCALE == 0:
                display_minutes = self.frozen_sim_time_minutes
            else:
                display_minutes = time_of_day

            h = int(display_minutes // 60) % 24
            m = int(display_minutes % 60)
            total_min = int(display_minutes)

            # Print once per simulated minute
            if total_min != self.last_printed_minute:
                self.output(f"Simulation time: \x1b[1m{h:02d}:{m:02d}\x1b[0m (Speed: {TIME_SCALE}x)")
                self.last_printed_minute = total_min

            # Program activation check
            if (self.program.program_enabled and not self.program.program_running
                    and not self.program.has_completed_all_repeats and TIME_SCALE > 0):
                sim_hhmm = h * 100 + m
                steps = self.program.program_steps
                if steps and sim_hhmm >= steps[0].get("sim_time_hhmm", 9999):
                    self.program.start()
                    self.output(f"[PROGRAM] Activated at {h:02d}:{m:02d}")

            # Program update
            if self.program.program_running:
                result = self.program.update(
                    now_ms, time_of_day, TIME_SCALE, INTENSITY_SCALE,
                    self.frozen_sim_time_minutes, self.start_real_time_ms,
                    START_TIME_HHMM, get_sim_time, reanchor_start_time,
                    lambda s: None)  # apply_step_fn handled via result dict
                if 'time_scale' in result:
                    TIME_SCALE = result['time_scale']
                if 'start_real_time_ms' in result:
                    self.start_real_time_ms = result['start_real_time_ms']
                if 'frozen_sim_time_minutes' in result:
                    self.frozen_sim_time_minutes = result['frozen_sim_time_minutes']

            # Periodic display update (every 1 second)
            if ticks_diff(now_ms, last_update_ms) >= update_interval_ms:
                # Auto-disable panel override
                if self.manual_panel_override_active and now_ms > self.manual_panel_override_until_ms:
                    self.manual_panel_override_active = False

                # Update sun display
                if (not self.camera_lighting_active and not self.rotation_lighting_active
                        and not self.manual_panel_override_active):
                    self.hw.update_sun_display(display_minutes, get_sun_position, DUAL_SUN_ENABLED)

                # Update OLED dashboard
                step_cur = self.program.current_step + 1 if self.program.program_running else 0
                step_total = len(self.program.program_steps) if self.program.program_running else 0
                self.hw.display.show_dashboard(h, m, TIME_SCALE, INTENSITY_SCALE, step_cur, step_total)

                last_update_ms = now_ms

            # Daytime check for servo intervals
            is_day = SUNRISE_MINUTES <= display_minutes <= SUNSET_MINUTES

            # Update rotation imaging cycle
            self.update_rotation(now_ms, display_minutes)

            # Update servo state machines
            self.update_servo2(now_ms, is_day)
            self.update_servo3(now_ms, is_day)

            # Camera lighting hold timeout
            if self.camera_light_hold_until_ms > 0 and now_ms >= self.camera_light_hold_until_ms:
                self.camera_light_hold_until_ms = 0
                if not self.rotation_lighting_active:
                    self.hw.deactivate_lighting()
                    self.camera_lighting_active = False

            # Process BLE commands (drain all queued from IRQ buffer)
            if self.ble:
                while self.ble.poll_command():
                    pass

            # Process serial input
            self.process_serial_input()

            # Button handling
            self._handle_buttons(now_ms)

            # Brief sleep to prevent tight loop
            sleep_ms(1)

            # Periodic GC to prevent heap fragmentation
            gc_counter += 1
            if gc_counter >= 30:
                gc.collect()
                gc_counter = 0

    def _handle_buttons(self, now_ms):
        """Process button A and B presses."""
        global TIME_SCALE, AUTO_LOAD_LATEST_PROFILE

        a = self.hw.read_button_a()
        b = self.hw.read_button_b()

        # Simple: button A long press → jump to solar noon
        if a and not hasattr(self, '_btn_a_start'):
            self._btn_a_start = now_ms
        elif a and hasattr(self, '_btn_a_start'):
            if ticks_diff(now_ms, self._btn_a_start) >= 1000:
                noon = SOLAR_NOON_MINUTES
                if TIME_SCALE == 0:
                    self.frozen_sim_time_minutes = noon
                elif TIME_SCALE > 0:
                    self.start_real_time_ms = reanchor_start_time(noon, TIME_SCALE, now_ms, START_TIME_HHMM, self.start_real_time_ms)
                self.output(f"Button A: Jump to solar noon ({int(noon)//60:02d}:{int(noon)%60:02d})")
                self._btn_a_start = now_ms + 99999  # Prevent retriggering
        elif not a and hasattr(self, '_btn_a_start'):
            del self._btn_a_start

        # Button B short press → cycle speed (triggers on release, 300ms debounce)
        if b and not hasattr(self, '_btn_b_down'):
            self._btn_b_down = True
        elif not b and hasattr(self, '_btn_b_down'):
            del self._btn_b_down
            # Debounce: ignore releases within 300ms of last action
            if not hasattr(self, '_btn_b_cooldown') or ticks_diff(now_ms, self._btn_b_cooldown) >= 300:
                self._btn_b_cooldown = now_ms
                speeds = [1, 6, 60, 600, 0]
                try:
                    idx = speeds.index(TIME_SCALE)
                    TIME_SCALE = speeds[(idx + 1) % len(speeds)]
                except ValueError:
                    TIME_SCALE = 1
                self.output(f"Button B: Speed → {get_speed_name(TIME_SCALE)}")
