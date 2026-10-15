# SPDX-License-Identifier: GPL-3.0-or-later
"""
self_driving.py — Self-Driving Plant State Machine
====================================================
Closed-loop phototropism feedback controller.

The plant bends toward light, crossing a threshold (detected by CV on a host
webpage, or by a simple timer fallback). When triggered, the car moves toward
the light, and the simulator jumps to a different sun position.

Sun positions are expressed as sim-time minutes (e.g., 600 = 10:00 = E30°,
840 = 14:00 = W30°). This reuses the existing SolaSim sun position engine —
the NeoPixel panel renders whatever the current sim time dictates.

States:
    IDLE          → Waiting to start
    SUN_EAST      → Sun at position A (east), plant following, waiting for trigger
    SUN_WEST      → Sun at position B (west), plant following, waiting for trigger
    NIGHT         → Night period, plant recovers

Serial commands (handled by main_sdp.py):
    SDP:START                  → Begin experiment
    SDP:STOP                   → Stop and return to IDLE
    SDP:TRIGGER                → CV-detected threshold crossed — transition now
    SDP:STATUS                 → Report current state (verbose multi-line block)
    SDP:STATUS?                → Compact one-line state snapshot for host polling
    SDP:CONFIG key=val,...     → Update configuration parameters
    SDP:CONFIG?                → Report current config (verbose multi-line block)
    SDP:ROTATE DEG=<angle>     → Rotate sample turntable (servo1) to absolute angle
    SDP:ROTATE?                → Report current commanded rotation angle
"""

from time import ticks_ms, ticks_diff


class SelfDrivingPlant:
    """Closed-loop phototropism experiment controller.

    Args:
        car_driver: CarDriver instance for moving the plant car
        output_fn: Function for serial output (print or sim.output)
        jump_time_fn: Callback to jump simulator's sim time to a given
                      minute-of-day value. Signature: jump_time_fn(minutes)
        config: Dict of configuration overrides
    """

    def __init__(self, car_driver, output_fn=print, jump_time_fn=None, config=None):
        self.car = car_driver
        self.output = output_fn
        # Share the same output channel with the car driver so [CAR] lines
        # reach the same stream the host bridge listens on.
        if hasattr(self.car, "set_output"):
            self.car.set_output(output_fn)
        elif hasattr(self.car, "output"):
            self.car.output = output_fn
        self.jump_time = jump_time_fn  # Set by main_sdp.py
        self._pending_sun_minutes = None  # Deferred sun switch after car stops

        # Configuration (overridable via SDP:CONFIG)
        cfg = config or {}
        self.sun_a_minutes = cfg.get("sun_a", 600)    # 10:00 = E30°
        self.sun_b_minutes = cfg.get("sun_b", 840)    # 14:00 = W30°
        self.trigger_delay_h = cfg.get("trigger_delay_h", 3.0)
        self.car_move_duration_ms = cfg.get("car_move_duration_ms", 2000)
        self.car_speed = cfg.get("car_speed", 0.5)  # 0.0-1.0
        self.night_duration_h = cfg.get("night_duration_h", 8.0)
        self.max_cycles = cfg.get("max_cycles", 0)  # 0 = unlimited

        # State
        self.state = "IDLE"
        self.cycle_count = 0
        self._state_start_ms = 0
        self._experiment_start_ms = 0
        self._waiting_for_car = False

    def start(self):
        """Begin experiment: jump to sun_a, state=SUN_EAST."""
        self.state = "SUN_EAST"
        self.cycle_count = 0
        self._state_start_ms = ticks_ms()
        self._experiment_start_ms = self._state_start_ms
        self._waiting_for_car = False
        # Jump simulator to sun position A
        if self.jump_time:
            self.jump_time(self.sun_a_minutes)
        # Single concatenated line to survive USB CDC tx-buffer drops on the
        # RP2040 (multi-line bursts get silently truncated).
        self.output(
            "[SDP] Experiment started — sun {} | sun_a={} sun_b={} "
            "trigger_delay={}h car_move={}ms car_speed={:.0%}".format(
                self._fmt_time(self.sun_a_minutes),
                self._fmt_time(self.sun_a_minutes),
                self._fmt_time(self.sun_b_minutes),
                self.trigger_delay_h,
                self.car_move_duration_ms,
                self.car_speed))

    def stop(self):
        """Stop experiment, return to IDLE."""
        self.car.stop()
        self.state = "IDLE"
        self._waiting_for_car = False
        self.output(f"[SDP] Experiment stopped after {self.cycle_count} cycles")

    def trigger(self):
        """External trigger (from CV dashboard or manual).
        Forces immediate transition regardless of timer.
        """
        if self.state in ("SUN_EAST", "SUN_WEST"):
            self.output("[SDP] Trigger received — transitioning")
            self._do_transition()
        else:
            self.output(f"[SDP] Trigger ignored (state={self.state})")

    def tick(self):
        """Call from main loop. Manages timer-based fallback and car movement."""
        if self.state == "IDLE":
            return

        now = ticks_ms()

        # If car is mid-move, let it finish
        if self._waiting_for_car:
            if self.car.tick():
                # Car move completed — now switch the sun
                self._waiting_for_car = False
                self._state_start_ms = now
                if self._pending_sun_minutes is not None and self.jump_time:
                    self.jump_time(self._pending_sun_minutes)
                    self.output(f"[SDP] Car arrived → sun to {self._fmt_time(self._pending_sun_minutes)}. State={self.state}, Cycle={self.cycle_count}")
                    self._pending_sun_minutes = None
                else:
                    self.output(f"[SDP] Car arrived. State={self.state}, Cycle={self.cycle_count}")
            return

        # Check car tick (safety)
        self.car.tick()

        # Timer-based fallback
        elapsed_h = ticks_diff(now, self._state_start_ms) / 3_600_000
        if self.state in ("SUN_EAST", "SUN_WEST"):
            if elapsed_h >= self.trigger_delay_h:
                self.output(f"[SDP] Timer trigger ({self.trigger_delay_h}h elapsed)")
                self._do_transition()

        elif self.state == "NIGHT":
            if elapsed_h >= self.night_duration_h:
                self.output("[SDP] Night complete — restarting cycle")
                self.state = "SUN_EAST"
                self._state_start_ms = now
                if self.jump_time:
                    self.jump_time(self.sun_a_minutes)

    def _do_transition(self):
        """Flip sun position, move car, advance state.
        Sun switch is deferred until car finishes moving.
        """
        if self.state == "SUN_EAST":
            # Plant bent toward A → move car, defer sun flip to B
            self.car.move("LEFT", self.car_move_duration_ms, speed=self.car_speed)
            self._waiting_for_car = True
            self.state = "SUN_WEST"
            self.cycle_count += 1
            self._pending_sun_minutes = self.sun_b_minutes
            self.output(f"[SDP] → Car EAST, sun will switch to {self._fmt_time(self.sun_b_minutes)} after car stops. Cycle {self.cycle_count}")

        elif self.state == "SUN_WEST":
            # Plant bent toward B → move car, defer sun flip to A
            self.car.move("RIGHT", self.car_move_duration_ms, speed=self.car_speed)
            self._waiting_for_car = True
            self.state = "SUN_EAST"
            self.cycle_count += 1
            self._pending_sun_minutes = self.sun_a_minutes
            self.output(f"[SDP] → Car WEST, sun will switch to {self._fmt_time(self.sun_a_minutes)} after car stops. Cycle {self.cycle_count}")

        # Check max cycles
        if self.max_cycles > 0 and self.cycle_count >= self.max_cycles:
            self.output(f"[SDP] Max cycles ({self.max_cycles}) reached — entering night")
            self.state = "NIGHT"
            self._state_start_ms = ticks_ms()

    def _fmt_time(self, minutes):
        """Format minutes-of-day as HH:MM."""
        return f"{int(minutes)//60:02d}:{int(minutes)%60:02d}"

    def configure(self, config_str):
        """Parse and apply configuration from 'key=val,key=val,...' string.

        Sun positions accept HH:MM (e.g. sun_a=10:00) or raw minutes (sun_a=600).
        """
        try:
            for pair in config_str.split(","):
                key, val = pair.strip().split("=")
                key = key.strip()
                val = val.strip()
                if key == "sun_a":
                    self.sun_a_minutes = self._parse_time(val)
                elif key == "sun_b":
                    self.sun_b_minutes = self._parse_time(val)
                elif key == "trigger_delay_h":
                    self.trigger_delay_h = float(val)
                elif key == "car_move_duration_ms":
                    self.car_move_duration_ms = int(val)
                elif key == "night_duration_h":
                    self.night_duration_h = float(val)
                elif key == "car_speed":
                    self.car_speed = max(0.0, min(1.0, float(val)))
                elif key == "max_cycles":
                    self.max_cycles = int(val)
                else:
                    self.output(f"[SDP] Unknown config key: {key}")
                    continue
                self.output(f"[SDP] Config: {key}={val}")
        except Exception as e:
            self.output(f"[SDP] Config error: {e}")

    def _parse_time(self, val):
        """Parse HHMM or HH:MM to minutes-of-day. e.g. '1000'→600, '10:00'→600."""
        if ':' in val:
            h, m = val.split(':')
            return int(h) * 60 + int(m)
        # HHMM format: '1000' → 10h 00m, '930' → 9h 30m
        v = int(val)
        return (v // 100) * 60 + (v % 100)

    def get_status_str(self):
        """Format full status as a multi-line serial output block.

        Verbose; used for occasional human-readable reporting. For routine
        host polling prefer `get_status_compact()` — a single line that
        survives USB CDC tx-buffer drops.
        """
        now = ticks_ms()
        elapsed_exp = ticks_diff(now, self._experiment_start_ms) / 1000 if self.state != "IDLE" else 0
        elapsed_st = ticks_diff(now, self._state_start_ms) / 1000 if self.state != "IDLE" else 0
        sun = self._fmt_time(self.sun_a_minutes) if self.state in ("SUN_EAST", "NIGHT") else self._fmt_time(self.sun_b_minutes)
        return "\n".join([
            "--- Self-Driving Plant Status ---",
            f"  State: {self.state}",
            f"  Sun: {sun}",
            f"  Cycles: {self.cycle_count}",
            f"  Car Moving: {self.car.is_moving}",
            f"  Experiment: {elapsed_exp:.0f}s",
            f"  State Elapsed: {elapsed_st:.0f}s",
            f"  Sun A: {self._fmt_time(self.sun_a_minutes)} ({self.sun_a_minutes}min)",
            f"  Sun B: {self._fmt_time(self.sun_b_minutes)} ({self.sun_b_minutes}min)",
            f"  Trigger Delay: {self.trigger_delay_h}h",
            f"  Car Duration: {self.car_move_duration_ms}ms",
            f"  Car Speed: {self.car_speed:.0%}",
            f"  Max Cycles: {self.max_cycles} (0=unlimited)",
            "---------------------------------",
        ])

    def get_status_compact(self):
        """Single-line snapshot for routine host polling.

        Format: `[SDP-STATUS] state=… sun=… cycles=… car=… exp=…s elapsed=…s end=…`
        Stays well under one USB CDC frame so it survives reliably. The
        `end=` field is the most recently confirmed reed-switch endpoint
        (`WEST` / `EAST` / `NONE` — `NONE` if no endstop fitted or hit yet).
        """
        now = ticks_ms()
        elapsed_exp = ticks_diff(now, self._experiment_start_ms) / 1000 if self.state != "IDLE" else 0
        elapsed_st = ticks_diff(now, self._state_start_ms) / 1000 if self.state != "IDLE" else 0
        sun = self._fmt_time(self.sun_a_minutes) if self.state in ("SUN_EAST", "NIGHT") else self._fmt_time(self.sun_b_minutes)
        end = getattr(self.car, "at_end", None) or "NONE"
        return ("[SDP-STATUS] state={} sun={} cycles={} car={} exp={:.0f}s "
                "elapsed={:.0f}s end={}").format(
            self.state, sun, self.cycle_count,
            "True" if self.car.is_moving else "False",
            elapsed_exp, elapsed_st, end)

    def get_config_str(self):
        """Static configuration snapshot. Use on connect / after writes —
        not for routine polling. Single line for USB CDC reliability."""
        return ("[SDP-CONFIG] sun_a={} sun_b={} trigger_delay_h={} "
                "car_move_ms={} car_speed={:.0%} night_h={} max_cycles={}").format(
            self._fmt_time(self.sun_a_minutes),
            self._fmt_time(self.sun_b_minutes),
            self.trigger_delay_h,
            self.car_move_duration_ms,
            self.car_speed,
            self.night_duration_h,
            self.max_cycles)
