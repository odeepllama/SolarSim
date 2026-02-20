# SPDX-License-Identifier: GPL-3.0-or-later
"""
program_engine.py — Program Step Engine & Profile Management
==============================================================
Solar Simulator for ESP32-S3

Manages:
  - Program steps (RUN/JUMP/HOLD transitions)
  - Step advancement, repeats, and program repeats
  - Profile loading, saving, listing, deletion
  - Auto-load of latest profile at startup
"""

import gc
import os
from time import ticks_ms, ticks_diff

try:
    import ujson as json
except ImportError:
    import json

from hardware import clamp


# ======================================================
# Profile validation rules
# ======================================================
# Maps profile keys to their validator functions.
# Each validator returns the validated value or raises ValueError.

def _validate_hhmm(v_str):
    v = int(v_str)
    if not (0 <= v <= 2359 and v % 100 < 60):
        raise ValueError("invalid HHMM format")
    return v

def _validate_positive_int(v_str):
    v = int(v_str)
    if v <= 0:
        raise ValueError("must be > 0")
    return v

def _validate_nonneg_int(v_str):
    v = int(v_str)
    if v < 0:
        raise ValueError("must be >= 0")
    return v

def _validate_nonneg_float(v_str):
    v = float(v_str)
    if v < 0:
        raise ValueError("must be non-negative")
    return v

def _validate_positive_float(v_str):
    v = float(v_str)
    if v <= 0:
        raise ValueError("must be > 0")
    return v

def _validate_bool(v_str):
    if v_str.lower() not in ('true', 'false'):
        raise ValueError("must be True or False")
    return v_str.lower() == 'true'

def _validate_string(v_str):
    return v_str.strip('"')

def _validate_latitude(v_str):
    v = float(v_str)
    if not (-90 <= v <= 90):
        raise ValueError("must be -90 to 90")
    return v

def _validate_date(v_str):
    v = int(v_str)
    if not (20000101 <= v <= 21001231):
        raise ValueError("out of range")
    return v

def _validate_color(v_str):
    return clamp(int(v_str))

def _validate_images_per_rotation(v_str):
    v = int(v_str)
    if v < 2 or v > 360:
        raise ValueError("must be 2-360")
    return v

def _validate_camera_servo(v_str):
    v = int(v_str)
    if v not in (2, 3):
        raise ValueError("must be 2 or 3")
    return v


# Mapping from profile key name to validation function
PROFILE_VALIDATORS = {
    "START_TIME_HHMM": _validate_hhmm,
    "TIME_SCALE": lambda v: float(v),
    "INTENSITY_SCALE": _validate_nonneg_float,
    "SIMULATION_DATE": _validate_date,
    "LATITUDE": _validate_latitude,
    "SOLAR_MODE": _validate_string,
    "SUN_COLOR_MODE": _validate_string,
    "ROTATION_CAPTURE_MODE": _validate_string,
    "DUAL_SUN_ENABLED": _validate_bool,
    "PROGRAM_ENABLED": _validate_bool,
    "ROTATION_ENABLED": _validate_bool,
    "RESTART_AFTER_LOAD": _validate_bool,
    "ROTATION_AT_NIGHT": _validate_bool,
    "ROTATION_CYCLE_INTERVAL_MINUTES": _validate_positive_int,
    "SERVO2_INTERVAL_DAY_SEC": _validate_nonneg_int,
    "SERVO2_INTERVAL_NIGHT_SEC": _validate_nonneg_int,
    "SERVO3_INTERVAL_DAY_SEC": _validate_nonneg_int,
    "SERVO3_INTERVAL_NIGHT_SEC": _validate_nonneg_int,
    "STILLS_IMAGING_INTERVAL_SEC": _validate_positive_float,
    "ROTATION_CAMERA_SERVO": _validate_camera_servo,
    "CAMERA_TRIGGER_HOLD_MS": _validate_positive_int,
    "ROTATION_INCREMENT_DEGREES": _validate_positive_float,
    "ROTATION_STEP_INTERVAL_MS": _validate_positive_int,
    "IMAGES_PER_ROTATION": _validate_images_per_rotation,
    "PROGRAM_REPEATS": lambda v: int(v),
    "CUSTOM_SUN_R": _validate_color,
    "CUSTOM_SUN_G": _validate_color,
    "CUSTOM_SUN_B": _validate_color,
}

# Legacy fields to silently ignore during loading
LEGACY_FIELDS = {
    "IMAGE_AT_NIGHT", "SERVO2_STANDALONE_ENABLED", "SERVO3_STANDALONE_ENABLED",
    "SERVO2_INTERVAL_SEC", "SERVO3_INTERVAL_SEC", "DEGREES_PER_IMAGE", "NOTE",
}

# Rotation speed preset table (must match simulator.py)
ROTATION_SPEED_PRESET_TABLE = {
    "slow": 180.0,
    "medium": 60.0,
    "fast": 7.0,
}


class ProgramEngine:
    """Manages program step execution and profile file operations."""

    def __init__(self, output_fn=None):
        """Initialize program engine.

        Args:
            output_fn: Callable(text) for output (print + BLE). Falls back to print().
        """
        self.output = output_fn or print

        # --- Program configuration ---
        self.program_enabled = True
        self.program_steps = [
            {"sim_time_hhmm": 1200, "speed": 1, "intensity_scale": 1.0, "dual_sun": False}
        ]
        self.program_repeats = -1
        self.stop_after_program = False

        # --- Program runtime state ---
        self.program_running = False
        self.current_step = 0
        self.current_step_repeat = 0
        self.current_program_repeat = 0
        self.step_start_sim_time = 0
        self.last_printed_minute = 0
        self.hold_step_start_ms = 0
        self.has_completed_all_repeats = False

    # ==========================================================
    # Program Control
    # ==========================================================

    def start(self):
        """Start or restart program execution."""
        self.program_running = True
        self.current_step = 0
        self.current_step_repeat = 0
        self.current_program_repeat = 0
        self.step_start_sim_time = 0
        self.last_printed_minute = 0
        self.has_completed_all_repeats = False
        self.output("[PROGRAM] Started")

    def stop(self):
        """Stop program execution."""
        self.program_running = False
        self.output("[PROGRAM] Stopped")

    def get_current_step_dict(self):
        """Return the current step's dictionary, or None if invalid."""
        if 0 <= self.current_step < len(self.program_steps):
            return self.program_steps[self.current_step]
        return None

    # ==========================================================
    # Step Settings Application (returns values for simulator to apply)
    # ==========================================================

    def get_step_settings(self, step=None):
        """Extract settings from a program step.

        Returns dict with keys: speed, intensity_scale, dual_sun.
        """
        if step is None:
            step = self.get_current_step_dict()
        if step is None:
            return {}
        return {
            "speed": step.get("speed", 1),
            "intensity_scale": step.get("intensity_scale", None),
            "dual_sun": step.get("dual_sun", None),
        }

    # ==========================================================
    # Step Advancement
    # ==========================================================

    def advance(self, start_real_time_ms_ref, frozen_sim_time_minutes, time_scale,
                start_time_hhmm, reanchor_fn):
        """Advance program step/repeat (reverse-aware).

        Args:
            start_real_time_ms_ref: Current start reference time
            frozen_sim_time_minutes: Current frozen sim time (for HOLD→RUN transitions)
            time_scale: Current TIME_SCALE
            start_time_hhmm: Current START_TIME_HHMM
            reanchor_fn: Callable(preserved_minutes, new_speed, now_ms, start_hhmm, old_start_ms) -> new_start_ms

        Returns:
            dict with keys:
                'start_real_time_ms': updated start time (or None if no change)
                'done': True if program completed all repeats
        """
        result = {'start_real_time_ms': None, 'done': False}
        previous_step = self.program_steps[self.current_step]
        previous_was_hold = previous_step.get("speed", 1) == 0

        step = self.program_steps[self.current_step]
        repeat_limit = step.get("repeat", 1)

        if self.current_step_repeat < repeat_limit - 1:
            # Repeat current step
            self.current_step_repeat += 1
            self.output(f"[PROGRAM] Repeating step ({self.current_step_repeat + 1}/{repeat_limit})")
            self.step_start_sim_time = 0

            # Jump sim time back to step's start time
            step_time_hhmm = step["sim_time_hhmm"]
            step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
            now_ms = ticks_ms()
            result['start_real_time_ms'] = reanchor_fn(
                step_time_minutes, time_scale, now_ms, start_time_hhmm, start_real_time_ms_ref)
        else:
            # Move to next step
            self.current_step_repeat = 0
            self.current_step += 1

            if self.current_step >= len(self.program_steps):
                if self.program_repeats == -1:
                    self.current_program_repeat += 1
                    self.current_step = 0
                    self.output(f"[PROGRAM] Repeating program (cycle {self.current_program_repeat + 1})")
                elif self.current_program_repeat < self.program_repeats - 1:
                    self.current_program_repeat += 1
                    self.current_step = 0
                    self.output(f"[PROGRAM] Repeating program ({self.current_program_repeat + 1}/{self.program_repeats})")
                else:
                    self.output("[PROGRAM] Complete - holding final configuration")
                    self.stop()
                    self.has_completed_all_repeats = True
                    result['done'] = True
                    return result

        # Handle HOLD→RUN transition
        if self.program_running and self.current_step < len(self.program_steps):
            current_step = self.program_steps[self.current_step]
            if previous_was_hold and current_step.get("speed", 1) != 0:
                now_ms = ticks_ms()
                result['start_real_time_ms'] = reanchor_fn(
                    frozen_sim_time_minutes, current_step.get("speed", 1),
                    now_ms, start_time_hhmm, start_real_time_ms_ref)

        self.step_start_sim_time = 0
        return result

    # ==========================================================
    # Program State Update (called each main loop iteration)
    # ==========================================================

    def update(self, now_ms, sim_time_minutes, time_scale, intensity_scale,
               frozen_sim_time_minutes, start_real_time_ms, start_time_hhmm,
               get_sim_time_fn, reanchor_fn, apply_step_fn):
        """Update program logic. Called from main loop.

        Args:
            now_ms: Current ticks_ms()
            sim_time_minutes: Current simulation time of day in minutes
            time_scale: Current TIME_SCALE
            intensity_scale: Current INTENSITY_SCALE
            frozen_sim_time_minutes: Current frozen sim time
            start_real_time_ms: Current start reference
            start_time_hhmm: Current START_TIME_HHMM
            get_sim_time_fn: Callable(start_hhmm, elapsed_ms, scale) -> (abs, tod)
            reanchor_fn: Time reanchoring function
            apply_step_fn: Callable(step_settings_dict) for applying step changes

        Returns:
            dict with possible keys:
                'time_scale': new time scale if changed
                'start_real_time_ms': new start ref if changed
                'frozen_sim_time_minutes': new frozen time if changed
                'intensity_scale': new intensity if changed
                'dual_sun': new dual sun state if changed
        """
        result = {}
        if not self.program_running:
            return result

        # Print status once per sim minute
        if int(sim_time_minutes) > self.last_printed_minute:
            self._print_status(now_ms, sim_time_minutes, time_scale, intensity_scale)
            self.last_printed_minute = int(sim_time_minutes)

        step = self.program_steps[self.current_step]
        step_time_hhmm = step["sim_time_hhmm"]
        step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
        transition_type = step.get("transition", "RUN")

        # Initialize step on first encounter
        if self.step_start_sim_time == 0:
            self.step_start_sim_time = sim_time_minutes

            # Apply step settings
            settings = self.get_step_settings(step)
            apply_step_fn(settings)
            new_speed = settings.get("speed", 1)

            if settings.get("intensity_scale") is not None:
                result['intensity_scale'] = settings['intensity_scale']
            if settings.get("dual_sun") is not None:
                result['dual_sun'] = settings['dual_sun']

            if new_speed != time_scale:
                result['time_scale'] = new_speed
                time_scale = new_speed

            if time_scale == 0:
                result['frozen_sim_time_minutes'] = sim_time_minutes
                if "hold_minutes" in step:
                    self.hold_step_start_ms = now_ms
                    self.output(f"[PROGRAM] Holding for {step['hold_minutes']} minutes")
                else:
                    # Calculate hold duration from next step
                    if self.current_step < len(self.program_steps) - 1:
                        next_step = self.program_steps[self.current_step + 1]
                        if "sim_time_hhmm" in next_step:
                            next_m = (next_step["sim_time_hhmm"] // 100) * 60 + (next_step["sim_time_hhmm"] % 100)
                            hold_dur = (next_m - int(sim_time_minutes)) % 1440
                            step["hold_minutes"] = hold_dur
                            self.hold_step_start_ms = now_ms
                            self.output(f"[PROGRAM] Holding for {hold_dur} minutes")

                self._print_status(now_ms, sim_time_minutes, time_scale, intensity_scale)

            if transition_type == "JUMP" and time_scale != 0:
                start_m = (start_time_hhmm // 100) * 60 + (start_time_hhmm % 100)
                if time_scale > 0:
                    mins = (step_time_minutes - start_m) % 1440
                else:
                    mins = (start_m - step_time_minutes) % 1440
                new_start = now_ms - int((mins * 60000) / max(0.0001, abs(time_scale)))
                result['start_real_time_ms'] = new_start

        # Check if target reached
        is_hold = time_scale == 0
        target_reached = False

        if is_hold and "hold_minutes" in step and self.hold_step_start_ms > 0:
            if (ticks_diff(now_ms, self.hold_step_start_ms) // 60000) >= step["hold_minutes"]:
                # Transition from HOLD: jump to next step's time
                if self.current_step < len(self.program_steps) - 1:
                    next_step = self.program_steps[self.current_step + 1]
                    if "sim_time_hhmm" in next_step:
                        next_m = (next_step["sim_time_hhmm"] // 100) * 60 + (next_step["sim_time_hhmm"] % 100)
                        result['frozen_sim_time_minutes'] = next_m
                    else:
                        fm = frozen_sim_time_minutes
                        result['frozen_sim_time_minutes'] = (fm + step["hold_minutes"]) % 1440
                else:
                    fm = frozen_sim_time_minutes
                    result['frozen_sim_time_minutes'] = (fm + step["hold_minutes"]) % 1440
                target_reached = True

        elif transition_type == "RUN":
            # Check against next step's time
            if self.current_step < len(self.program_steps) - 1:
                next_hhmm = self.program_steps[self.current_step + 1]["sim_time_hhmm"]
                target_minutes = (next_hhmm // 100) * 60 + (next_hhmm % 100)
            else:
                target_minutes = step_time_minutes

            step_speed = step.get("speed", time_scale)
            direction = 1 if step_speed > 0 else (-1 if step_speed < 0 else 0)
            speed_mag = abs(step_speed) if step_speed != 0 else 1
            tolerance = 0.2 if speed_mag <= 1 else min(3.0, speed_mag / 200)

            if direction >= 0:
                cur = sim_time_minutes
                tgt = target_minutes
                if target_minutes < self.step_start_sim_time:
                    if sim_time_minutes < self.step_start_sim_time:
                        cur += 1440
                    tgt += 1440
                if cur >= (tgt - tolerance):
                    target_reached = True
            else:
                start_tod = self.step_start_sim_time
                tgt = target_minutes
                if target_minutes > start_tod:
                    tgt -= 1440
                cur = sim_time_minutes
                if sim_time_minutes > start_tod:
                    cur -= 1440
                if cur <= (tgt + tolerance):
                    target_reached = True

        elif transition_type == "JUMP":
            target_reached = True

        if target_reached:
            adv = self.advance(start_real_time_ms,
                               result.get('frozen_sim_time_minutes', frozen_sim_time_minutes),
                               time_scale, start_time_hhmm, reanchor_fn)
            if adv.get('start_real_time_ms') is not None:
                result['start_real_time_ms'] = adv['start_real_time_ms']

        return result

    # ==========================================================
    # Status Printing
    # ==========================================================

    def _print_status(self, now_ms, sim_time_minutes, time_scale, intensity_scale):
        """Print program status line."""
        if not self.program_running:
            return

        step = self.program_steps[self.current_step]

        # Calculate target time
        if self.step_start_sim_time == 0:
            t_hhmm = step["sim_time_hhmm"]
        elif self.current_step < len(self.program_steps) - 1:
            t_hhmm = self.program_steps[self.current_step + 1]["sim_time_hhmm"]
        else:
            t_hhmm = None

        target_time = f"{t_hhmm // 100:02d}:{t_hhmm % 100:02d}" if t_hhmm else "N/A"
        t_minutes = (t_hhmm // 100) * 60 + (t_hhmm % 100) if t_hhmm else None

        # HOLD with timer
        if time_scale == 0 and "hold_minutes" in step and self.hold_step_start_ms > 0:
            elapsed = ticks_diff(now_ms, self.hold_step_start_ms)
            remaining = max(0, step["hold_minutes"] - (elapsed // 60000))
            self.output(
                f"[PROGRAM] Step {self.current_step + 1}/{len(self.program_steps)} "
                f"(Rep {self.current_step_repeat + 1}/{step.get('repeat', 1)}) | "
                f"Target: {target_time} | HOLD | "
                f"Intensity: {step.get('intensity_scale', intensity_scale):.2f} | "
                f"Remaining: {remaining} minutes | "
                f"Sim Time: {int(sim_time_minutes) // 60:02d}:{int(sim_time_minutes) % 60:02d}")
            return

        # Progress calculation for RUN steps
        progress = "N/A"
        if step.get("transition", "RUN") == "RUN" and self.step_start_sim_time > 0 and t_minutes is not None:
            step_speed = step.get("speed", time_scale)
            direction = 1 if step_speed > 0 else (-1 if step_speed < 0 else 0)

            if direction >= 0 and t_minutes > self.step_start_sim_time:
                denom = t_minutes - self.step_start_sim_time
                if denom > 0:
                    pct = (sim_time_minutes - self.step_start_sim_time) / denom * 100
                    progress = f"{max(0, min(100, pct)):.0f}%"
            elif direction < 0:
                start_eval = self.step_start_sim_time
                tgt = t_minutes - 1440 if t_minutes > start_eval else t_minutes
                cur = sim_time_minutes - 1440 if sim_time_minutes > start_eval else sim_time_minutes
                denom = start_eval - tgt
                if denom > 0:
                    pct = (start_eval - cur) / denom * 100
                    progress = f"{max(0, min(100, pct)):.0f}%"

        sim_h = int(sim_time_minutes // 60) % 24
        sim_m = int(sim_time_minutes % 60)
        self.output(
            f"[PROGRAM] Step {self.current_step + 1}/{len(self.program_steps)} "
            f"(Rep {self.current_step_repeat + 1}/{step.get('repeat', 1)}) | "
            f"Target: {target_time} | Speed: {time_scale}X | "
            f"Intensity: {step.get('intensity_scale', intensity_scale):.2f} | "
            f"Progress: {progress} | Sim Time: {sim_h:02d}:{sim_m:02d}")

    # ==========================================================
    # Profile Operations
    # ==========================================================

    def save_profile(self, filename, settings_dict, note=""):
        """Save current settings to a profile file.

        Args:
            filename: Profile filename (without .txt extension)
            settings_dict: Dict of all configurable settings to save
            note: Optional note string
        """
        fname = f"{filename}.txt"
        try:
            with open(fname, "w") as f:
                if note:
                    f.write(f"NOTE = {note}\n")
                for key, value in settings_dict.items():
                    if key == "PROGRAM_STEPS":
                        f.write(f"PROGRAM_STEPS = {json.dumps(value)}\n")
                    elif isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    elif isinstance(value, float):
                        f.write(f"{key} = {value:.2f}\n")
                    else:
                        f.write(f"{key} = {value}\n")
            self.output(f"[SERIAL CMD] Profile '{fname}' saved successfully.")
            return True
        except Exception as e:
            self.output(f"[SERIAL CMD] Error saving profile: {e}")
            return False

    def load_profile(self, filename):
        """Load and validate a profile file.

        Args:
            filename: Profile name (without .txt extension)

        Returns:
            Dict of validated settings, or None on error.
        """
        fname = f"{filename}.txt"
        try:
            os.stat(fname)
        except OSError:
            self.output(f"[SERIAL CMD] Error: Profile '{fname}' not found.")
            return None

        validated = {}
        try:
            with open(fname, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    key, value_str = line.split('=', 1)
                    key = key.strip()
                    value_str = value_str.strip()

                    if key in LEGACY_FIELDS:
                        continue

                    if key == "PROGRAM_STEPS":
                        validated[key] = json.loads(value_str)
                    elif key == "ROTATION_SPEED_PRESET":
                        preset = value_str.strip('"').lower()
                        if preset in ROTATION_SPEED_PRESET_TABLE:
                            validated[key] = preset
                        else:
                            raise ValueError(f"invalid ROTATION_SPEED_PRESET: {preset}")
                    elif key in PROFILE_VALIDATORS:
                        validated[key] = PROFILE_VALIDATORS[key](value_str)
                    # Unknown keys are silently ignored

        except Exception as e:
            self.output(f"[SERIAL CMD] Load cancelled. Error in '{fname}': {e}")
            return None

        self.output(f"[SERIAL CMD] Profile '{fname}' validated. Applying settings...")
        return validated

    def list_profiles(self):
        """List available profile files."""
        try:
            files = os.listdir()
            profiles = [f for f in files if f.endswith(".txt")]
            if profiles:
                self.output("[SERIAL CMD] Available profiles:")
                for pf in profiles:
                    note = ""
                    try:
                        with open(pf, "r") as f:
                            first = f.readline()
                            if first.startswith("NOTE ="):
                                note = first[len("NOTE ="):].strip()
                    except Exception:
                        pass
                    if note:
                        self.output(f"  {pf} - {note}")
                    else:
                        self.output(f"  {pf}")
            else:
                self.output("[SERIAL CMD] No profile files found.")
        except Exception as e:
            self.output(f"[SERIAL CMD] Error listing profiles: {e}")

    def delete_profile(self, filename):
        """Delete a profile file."""
        if not filename.endswith(".txt"):
            filename += ".txt"
        try:
            files = os.listdir()
            if filename not in files:
                self.output(f"[SERIAL CMD] Error: Profile '{filename}' not found.")
                return False
            os.remove(filename)
            self.output(f"[SERIAL CMD] Profile '{filename}' deleted successfully.")
            return True
        except Exception as e:
            self.output(f"[SERIAL CMD] Error deleting profile: {e}")
            return False

    # ==========================================================
    # Auto-load Logic
    # ==========================================================

    @staticmethod
    def find_latest_profile(prefix="profile_"):
        """Find the latest timestamped profile file.

        Returns (base_name, full_filename) or (None, None).
        """
        try:
            files = [f for f in os.listdir() if f.endswith('.txt') and prefix in f]
            candidates = []
            for f in files:
                if len(f) >= 17 and f[0:8].isdigit() and f[8] == '_' and f[9:13].isdigit():
                    candidates.append(f)
            if not candidates:
                return (None, None)
            latest = sorted(candidates)[-1]
            base = latest[:-4] if latest.lower().endswith('.txt') else latest
            return (base, latest)
        except Exception as e:
            print(f"[AUTOLOAD] Error scanning profiles: {e}")
            return (None, None)

    @staticmethod
    def load_autoload_preference():
        """Load persisted autoload preference from autoload.cfg.

        Returns True/False/None (None = no preference file found).
        """
        try:
            with open('autoload.cfg', 'r') as f:
                val = f.read().strip()
                if val in ('0', '1'):
                    result = (val == '1')
                    print(f"[AUTOLOAD] Persisted preference loaded: {result}")
                    return result
        except OSError:
            pass  # No file yet
        except Exception as e:
            print(f"[AUTOLOAD] Error reading autoload.cfg: {e}")
        return None

    @staticmethod
    def save_autoload_preference(enabled):
        """Save autoload preference to autoload.cfg."""
        try:
            with open('autoload.cfg', 'w') as f:
                f.write('1' if enabled else '0')
        except Exception as e:
            print(f"[AUTOLOAD] Error saving autoload.cfg: {e}")
