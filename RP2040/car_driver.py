# SPDX-License-Identifier: GPL-3.0-or-later
"""
car_driver.py — Continuous-Rotation Servo Car Driver
=====================================================
Drives a plant car along a linear track using a continuous-rotation servo.
Movement is time-based (spin at a known speed for a set duration) with
optional reed-switch endstops for hardware-defined east/west limits.

When reed switches are wired, the duration acts as a safety timeout and the
reed switch is the normal stop condition. On closure, the servo is stopped
immediately and the most-recently-confirmed end is recorded in `at_end`.

Usage:
    from car_driver import CarDriver
    car = CarDriver(pin=11, reed_west_pin=12, reed_east_pin=13)
    car.move("RIGHT", duration_ms=8000)   # stops early when east reed closes
    while not car.tick(): pass            # tick() returns True on completion
    print(car.at_end)                     # "EAST"
"""

from machine import Pin, PWM
from time import ticks_ms, ticks_diff, sleep_ms


# Continuous-rotation servo duty cycles (16-bit PWM at 50Hz).
# Calibrated via servo_tune.py sweep — dead zone is 4710–5100.
# These constants embed the physical drivetrain wiring: assign each value
# to the *desired travel direction*, so move("RIGHT") drives the car right.
# If wiring is ever reversed, swap the two values here (no host-side flip).
DEFAULT_DUTY_RIGHT = 3300    # Whichever duty physically drives the car right
DEFAULT_DUTY_LEFT = 6400     # Whichever duty physically drives the car left
DEFAULT_DUTY_STOP = 4900     # Neutral / stopped (midpoint of 4710–5100 dead zone)
PWM_FREQ = 50

# Reed-switch debounce — mechanical reeds can chatter for a few hundred
# microseconds on closure. 5 ms is well clear of that without delaying
# stop response perceptibly.
DEFAULT_REED_DEBOUNCE_MS = 5


class Endstops:
    """Two normally-open reed switches with internal pull-ups (pin → GND when
    a magnet is near). Debounced; emits an event ONCE per stable closure.

    `at_end` records the most-recently-confirmed end (`"WEST"`, `"EAST"`, or
    `None` if neither has fired yet) — it sticks until the other reed fires,
    so it can be used as "last known location" even while the car is
    mid-rail with both switches open.

    The directional convention (LEFT = west, RIGHT = east) is enforced by
    `CarDriver`; this class is direction-agnostic.
    """

    def __init__(self, west_pin, east_pin, debounce_ms=DEFAULT_REED_DEBOUNCE_MS,
                 output_fn=print):
        self._pin_west = Pin(west_pin, Pin.IN, Pin.PULL_UP)
        self._pin_east = Pin(east_pin, Pin.IN, Pin.PULL_UP)
        self.debounce_ms = debounce_ms
        self.output = output_fn

        # Debounce state (per side): when the raw line went LOW; None if HIGH.
        self._w_low_since = None
        self._e_low_since = None
        # Latched-stable state (per side): True only after debounce_ms of LOW.
        self._w_stable = False
        self._e_stable = False

        self.at_end = None  # "WEST", "EAST", or None

    def tick(self):
        """Sample both reed pins and update debounced state.

        Returns:
            "WEST" or "EAST" on the FIRST tick after a closure becomes stable,
            None otherwise (including all subsequent ticks while still closed).
        """
        now = ticks_ms()
        event = None

        # West reed
        if self._pin_west.value() == 0:                # raw LOW = reed closed
            if self._w_low_since is None:
                self._w_low_since = now
            elif (not self._w_stable
                  and ticks_diff(now, self._w_low_since) >= self.debounce_ms):
                self._w_stable = True
                self.at_end = "WEST"
                event = "WEST"
        else:                                          # raw HIGH = reed open
            self._w_low_since = None
            self._w_stable = False

        # East reed
        if self._pin_east.value() == 0:
            if self._e_low_since is None:
                self._e_low_since = now
            elif (not self._e_stable
                  and ticks_diff(now, self._e_low_since) >= self.debounce_ms):
                self._e_stable = True
                self.at_end = "EAST"
                # If both fired in the same tick window (shouldn't normally
                # happen — only one magnet near at a time), keep "WEST" if
                # it was logged first; emit the second as a follow-up event.
                event = "EAST" if event is None else event
        else:
            self._e_low_since = None
            self._e_stable = False

        return event

    @property
    def west_closed(self):
        return self._w_stable

    @property
    def east_closed(self):
        return self._e_stable


class CarDriver:
    """Controls a continuous-rotation servo for linear plant car movement.

    Args:
        pin: GPIO pin number for servo PWM signal.
        duty_right / duty_left / duty_stop: 16-bit duty cycle constants.
        reed_west_pin / reed_east_pin: Optional GPIO pin numbers for two
            normally-open reed switches. Both must be supplied to enable
            endstop tracking; if either is None, the car runs in pure
            time-based mode (legacy behaviour).
        output_fn: Output function for log lines (default print).
    """

    def __init__(self, pin, duty_right=DEFAULT_DUTY_RIGHT, duty_left=DEFAULT_DUTY_LEFT,
                 duty_stop=DEFAULT_DUTY_STOP,
                 reed_west_pin=None, reed_east_pin=None,
                 output_fn=print):
        self._pwm = PWM(Pin(pin), freq=PWM_FREQ)
        self._duty_right = duty_right
        self._duty_left = duty_left
        self._duty_stop = duty_stop
        self._moving = False
        self._move_end_ms = 0
        self._move_dir = None  # "LEFT" / "RIGHT" / None — direction of active move
        self.output = output_fn

        # Optional endstops
        self.endstops = None
        if reed_west_pin is not None and reed_east_pin is not None:
            self.endstops = Endstops(reed_west_pin, reed_east_pin, output_fn=output_fn)

        self.stop()
        self.output("[CAR] Initialized on GPIO {} (endstops={})".format(
            pin, "on (W=GP{}, E=GP{})".format(reed_west_pin, reed_east_pin)
                  if self.endstops else "off"))

    def set_output(self, output_fn):
        """Re-route log output. Useful when the caller wires a shared
        output function after construction (e.g. sim.output)."""
        self.output = output_fn or print
        if self.endstops is not None:
            self.endstops.output = self.output

    def move(self, direction, duration_ms, speed=0.5):
        """Start moving the car in the given direction for duration_ms.

        With endstops fitted, the matching reed switch will normally end the
        move early; `duration_ms` is the safety timeout. If the car is
        already at the requested end (reed currently closed), the move is
        refused with a log line and the servo is not driven.

        Args:
            direction: "LEFT" or "RIGHT" (logical travel direction).
            duration_ms: Safety timeout / unconditional stop time in ms.
            speed: 0.0 (stopped) to 1.0 (full speed), default 0.5.
        """
        speed = max(0.0, min(1.0, speed))
        if direction == "RIGHT":
            if self.endstops and self.endstops.west_closed:
                self.output("[CAR] Refusing RIGHT — already at WEST endstop")
                return
            duty = int(self._duty_stop + (self._duty_right - self._duty_stop) * speed)
        elif direction == "LEFT":
            if self.endstops and self.endstops.east_closed:
                self.output("[CAR] Refusing LEFT — already at EAST endstop")
                return
            duty = int(self._duty_stop + (self._duty_left - self._duty_stop) * speed)
        else:
            self.output("[CAR] Invalid direction: {}".format(direction))
            return

        self._pwm.duty_u16(duty)
        self._moving = True
        self._move_dir = direction
        self._move_end_ms = ticks_ms() + duration_ms
        self.output("[CAR] Moving {} for up to {}ms (speed={:.0%}, duty={})".format(
            direction, duration_ms, speed, duty))

    def tick(self):
        """Call from main loop. Returns True ONCE when an active move ends —
        whether by reed-switch closure or duration timeout. Endstop state is
        also updated when the car is idle (so manual repositioning is tracked).

        Returns:
            True if a move just completed this tick, False otherwise.
        """
        # Sample endstops every tick — reed events are authoritative whether
        # we initiated the move or the car was bumped manually.
        event = None
        if self.endstops is not None:
            event = self.endstops.tick()

        if event is not None:
            # Reed just closed. Stop the servo unconditionally; log the event.
            was_moving = self._moving
            if was_moving:
                self.output("[CAR-END] hit={} during {} — stopping".format(
                    event, self._move_dir))
                self.stop()
                return True
            else:
                # Manual repositioning detected — just log, don't touch the servo.
                self.output("[CAR-END] hit={} (idle)".format(event))

        # Duration safety timeout
        if self._moving and ticks_diff(ticks_ms(), self._move_end_ms) >= 0:
            self.output("[CAR] Duration timeout ({}) — stopping".format(self._move_dir))
            self.stop()
            return True
        return False

    def stop(self):
        """Immediately stop the car."""
        self._pwm.duty_u16(self._duty_stop)
        if self._moving:
            self.output("[CAR] Stopped")
        self._moving = False
        self._move_dir = None

    @property
    def is_moving(self):
        """True if the car is currently in motion."""
        return self._moving

    @property
    def at_end(self):
        """Most-recently-confirmed endstop: "WEST", "EAST", or None (never hit one)."""
        return self.endstops.at_end if self.endstops else None

    def deinit(self):
        """Release PWM resources."""
        self.stop()
        self._pwm.deinit()
