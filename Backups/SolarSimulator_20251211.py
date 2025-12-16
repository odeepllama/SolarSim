"""
Solar Simulator for Phototropism Experiments

This system simulates sun movement and controls imaging hardware
for plant/algae phototropism experiments.

Hardware: RP2040:bit board microcontroller with 3 servos, 1NeoPixel panel, and an internal 5x5 display matrix.
"""
import gc, machine, math, neopixel, os, select, sys
try:
    import ujson as json  # Prefer MicroPython ujson when available
except ImportError:  # Fallback (should not normally happen on target)
    import json

from machine import PWM
from time import ticks_ms, sleep_ms, sleep_us, ticks_diff

# Buffer for accumulating serial input before processing
serial_command_buffer = ""

# ======================================================
# I. CORE SIMULATION PARAMETERS
# ======================================================
# --- Time Configuration ---
START_TIME_HHMM = 500          # 500 used to be distinct from normal sunrise time
SIMULATION_DATE = 20250520     # Date in YYYYMMDD format (May 20, 2025)
TIME_SCALE = 1                 # Time scaling factor (0 (HOLD), 1, 6, 60, or 600X)
CUSTOM_TIME_SCALE = 1.2        # Custom time scale factor (1.2 = 1.2X, etc.)

# Program configuration
PROGRAM_ENABLED = False        # Master switch for program functionality
PROGRAM_STEPS = [              # default speed = 1X, default transition is RUN, if speed = 0, use hold_minutes
    {"sim_time_hhmm": 1200, "speed": 1, "dual_sun": True}, # intensity_scale is also settable, as well as "repeat": x
    {"sim_time_hhmm": 1500, "speed": 2, "dual_sun": True},
    {"sim_time_hhmm": 900, "dual_sun": True, "transition": "JUMP"},
    {"sim_time_hhmm": 1200, "speed": 2, "dual_sun": False},
    {"sim_time_hhmm": 1800, "speed": 2, "dual_sun": False},
]
# e.g."sim_time_hhmm": 900, "speed": 0, "hold_minutes": 10, "intensity_scale": 0.2, "dual_sun": True, "repeat": 2

PROGRAM_REPEATS = -1                   # -1 for indefinite repeats, 0 or 1 for single run, or N for N repeats
STOP_SIMULATION_AFTER_PROGRAM = False  # When True, terminates simulation after program completes

# --- Solar Simulation Mode ---
SOLAR_MODE = "BASIC"               # Choose from "BASIC" or "SCIENTIFIC"
SUN_COLOR_MODE = "BLUE"            # Choose from "NATURAL", "BLUE", or "CUSTOM"
DUAL_SUN_ENABLED = False           # Set to True to enable a mirrored second sun
RED_SHIFT_FACTOR = 0.4             # Red-shift factor for sunrise/sunset (not applied to BASIC mode)
MAX_BRIGHTNESS = 255               # Maximum brightness at solar noon
INTENSITY_SCALE = 1.0              # Global intensity multiplier

# --- Location Parameters ---
LATITUDE = 0                       # Latitude in degrees
LONGITUDE = 0                      # Longitude in degrees
TIME_ZONE_OFFSET = 0               # Time zone offset from UTC in hours
SOLAR_NOON_MINUTES = 12*60         # default (applies to BASIC and SIMPLE solar modes)

# ======================================================
# II. OPERATIONAL BEHAVIOR SETTINGS
# ======================================================
# --- System Behavior ---
RESTART_AFTER_LOAD = True          # When True, automatically re-initializes (soft resets) after loading a profile
AUTO_LOAD_LATEST_PROFILE = True    # Default: attempt to load most recent profile_*.txt on cold start (may be overridden by autoload.cfg)
AUTO_LOAD_PROFILE_PREFIX = "profile_"  # Filename prefix used by HTML builder (timestamp_profile[_tag].txt)
LOADED_PROFILE_NAME = None         # Tracks the filename of the currently loaded profile (None if using defaults)

# --- Day/Night Mode Controls ---
IMAGE_AT_NIGHT = False             # When False, servo2 only triggers during daylight
ROTATION_AT_NIGHT = False          # When False, rotation cycle only happens during daylight

# --- Lighting Configuration ---
# Custom sun color settings
CUSTOM_SUN_R = 255  # Red component (0-255) for custom sun color (removed trailing comma so this is an int, not a 1-tuple)
CUSTOM_SUN_G = 255
CUSTOM_SUN_B = 0

# Standard imaging lighting
CAMERA_LIGHTING_ENABLED = True     # Set to False to disable lighting during camera triggering
SERVO3_LIGHTING_ENABLED = True     # Set to True to enable lighting during Servo3 triggering
CAMERA_LIGHT_R = 30                # Red component (0-255) for camera lighting
CAMERA_LIGHT_G = 30                # Green component (0-255) for camera lighting
CAMERA_LIGHT_B = 30                # Blue component (0-255) for camera lighting
CAMERA_LIGHT_HOLD_MS = 1000        # Duration to hold camera lighting (ms)
CAMERA_LIGHTING_PANELS = "ALL"     # Options: "ALL", "MIDDLE5", "MIDDLE3", "OUTER2", "OUTER4"

# Rotation imaging lighting
ROTATION_LIGHTING_ENABLED = True   # Set to True to enable lighting during rotation
ROTATION_LIGHT_R = 30              # Red component (0-255) for rotation lighting
ROTATION_LIGHT_G = 30              # Green component (0-255) for rotation lighting
ROTATION_LIGHT_B = 30              # Blue component (0-255) for rotation lighting

# This option allows unwanted reflections to be minimized.
# ======================================================
# III. ROTATION SYSTEM CONFIGURATION
# ======================================================
# --- Rotation Cycle Parameters ---
ROTATION_CYCLE_INTERVAL_MINUTES = 3    # How often to perform imaging cycle (sim time)
ROTATION_ENABLED = False               # Flag to enable/disable rotation cycle (default OFF; profile can enable)
ROTATION_CAMERA_ENABLED = True         # Flag to enable/disable camera triggering during rotation
SERVO_1TO1_RATIO = False               # Default: 3:4 ratio
ROTATION_CAMERA_SERVO = 2              # Set to 2 or 3 to select which servo triggers during rotation imaging

# --- Servo2 (Primary Camera - triggers with rotation) Parameters ---
SERVO2_STANDALONE_ENABLED = True      # Set to False to disable independent servo2 triggering
SERVO2_INTERVAL_SEC = 120             # Trigger camera every N seconds (real time)
SERVO2_TRIGGER_HOLD_MS = 1000         # Hold camera trigger for this duration (ms)

# --- Servo3 (Secondary Camera - can capture a wider or closer view, or video) Parameters ---
SERVO3_STANDALONE_ENABLED = False     # Set to False to disable independent servo3 triggering
SERVO3_INTERVAL_SEC = 120             # Trigger camera every 30 minutes (real time)
SERVO3_TRIGGER_HOLD_MS = 1000         # Hold camera trigger for this duration (ms)

# --- Rotation Capture Configuration ---
''' Rotation parameters are set based on the number of images per full rotation (or degress per image)'''
ROTATION_CAPTURE_MODE = "STILLS"      # "VIDEO" = trigger servo2 at start/end, "STILLS" = periodic triggers
STILLS_IMAGING_INTERVAL_SEC = 13.5    # How often to trigger camera in STILLS mode (seconds)
CAMERA_TRIGGER_HOLD_MS = 1500         # Hold camera trigger for this duration (ms) during rotation imaging
ROTATION_INCREMENT_DEGREES = 0.3      # Rotate table degrees per step
ROTATION_STEP_INTERVAL_MS = 90        # Wait time between rotation steps
RETURN_STEP_DEGREES = 2               # Return increment degrees
RETURN_STEP_INTERVAL_MS = 30          # Wait time between return steps
IMAGES_PER_ROTATION = 8               # Default: 36 images per 360°
DEGREES_PER_IMAGE = 360.0 / IMAGES_PER_ROTATION
ROTATION_SPEED_PRESET = "fast"        # "slow", "medium", "fast"
DWELL_TIME_MS = 1500                  # Dwell time after rotation
ROTATION_SPEED_PRESET_TABLE = {
    "slow": 180.0,    # 180 seconds for 360°
    "medium": 60.0,   # 60 seconds for 360°
    "fast": 7.0       # 5 seconds for 360°
}

# --- Fine-grained servo movement for smooth rotation ---
FINE_ROTATION_INCREMENT_DEGREES = 0.3    # Default fine step size for smoothness
MIN_FINE_ROTATION_STEP_INTERVAL_MS = 40  # Minimum safe interval for servo (ms)
FINE_ROTATION_STEP_INTERVAL_MS = 90      # Will be computed based on speed 

# --- Serial logging interval ---
PRINT_INTERVAL_REAL_MS = 1000  # Minimum interval in milliseconds between simulation time prints

# ======================================================
# IV. SYSTEM STATE VARIABLES (Do not modify directly)
# ======================================================
# --- Runtime State Tracking ---
start_real_time_ms = 0                # Will be set at startup
panel_buffer = [(0, 0, 0)] * 448      # State buffer for NeoPixel delta updates

# --- Decoupling of NeoPixel/sun updates from matrix refresh ---
SUN_UPDATE_INTERVAL_MS = 1000  # Update NeoPixels/sun every 1 sec (adjust as needed)
last_sun_update_ms = ticks_ms()

# Program state variables
program_running = False
current_program_step = 0              # Index of current step
current_step_repeat = 0               # Current repetition of step (0-based)
current_program_repeat = 0            # Current repetition of entire program (0-based)
program_step_start_sim_time = 0       # Simulation time when step started
last_program_status_sim_time = 0      # Last time we printed status
hold_step_start_ms = 0                # Time when current hold step started
last_printed_minute = 0               # Last printed simulation minute
program_has_completed_all_repeats = False  # Flag to track program completion

# --- Lighting State Variables ---
rotation_lighting_active = False      # Flag to track if rotation lighting is active
camera_lighting_active = False        # Flag to track if camera lighting is active
manual_panel_override_active = False  # Allows on-demand imaging lights
manual_panel_override_until_ms = 0    # Timing checkpoint
camera_light_hold_until_ms = 0        # Lighting hold timer

# --- Rotation State Variables ---
rotation_in_progress = False          # Flag indicating an active imaging cycle
rotation_state = 'IDLE'               # State machine for rotation cycle
current_rotation_angle = 0            # Current rotation angle of the table (0-360)
last_rotation_step_time_ms = 0        # Timestamp of last rotation step
last_rotation_absolute_time = 0       # Simulation time when last rotation completed
camera_trigger_started_ms = 0         # Timestamp when camera trigger was activated
return_angle = 0                      # Current angle during return movement
last_stills_trigger_ms = 0            # Timestamp of last STILLS mode trigger
manual_rotation_triggered = False     # Flag to indicate manual rotation trigger

# --- Servo2 State Variables ---
servo2_state = 'IDLE'                 # State of standalone servo2 (IDLE or TRIGGERED)
last_servo2_trigger_ms = -999999      # Initialize to trigger immediately
servo2_trigger_start_ms = 0           # When current servo2 trigger started
servo2_controlled_by_rotation = False # Flag to indicate rotation cycle is controlling servo2
servo2_using_lighting = False         # Track if servo2 is using lighting

# --- Servo3 State Variables ---
servo3_state = 'IDLE'                 # State of standalone servo3 (IDLE or TRIGGERED)
last_servo3_trigger_ms = -999999      # Last time servo3 was triggered
servo3_trigger_start_ms = 0           # When current servo3 trigger started
servo3_using_lighting = False         # Track if servo3 is using lighting

# ======================================================
# VI. HARDWARE CONFIGURATION
# ======================================================
# --- Servo Control Parameters ---
SERVO_1_PIN_NUM = 6    # GP6 - Platform rotation servo - pin 3 on Micro:bit breakout board
SERVO_2_PIN_NUM = 10   # GP10 - Primary camera trigger servo  - pin 13 on Micro:bit breakout board
SERVO_3_PIN_NUM = 11   # GP11 - Second camera trigger servo - pin 15 on Microbit:bit breakout board
PWM_FREQ = 50          # Standard servo PWM frequency (Hz)
MIN_DUTY = 1400        # Duty cycle for 0 degrees (approx 0.5ms pulse)
MAX_DUTY = 8352        # Duty cycle for 270 degrees (approx 2.5ms pulse)
SERVO_ANGLE_RANGE = 273.0  # WAS 270 The full range of motion for the servo

# Angle parameters
TABLE_SERVO_START_ANGLE = 0     # Starting angle for table servo
CAMERA_SERVO_REST_ANGLE = 45    # Camera servo resting angle
CAMERA_SERVO_TRIGGER_ANGLE = 90 # Camera servo angle when triggered

# --- Pin Definitions (Based on RP2040:bit mapping) ---
NEOPIXEL_PIN_NUM = 15 # GP15
BUTTON_A_PIN_NUM = 0  # GP0 (Micro:bit Pin0 (P0))
BUTTON_B_PIN_NUM = 1  # GP1 (Micro:bit Pin1 (P1))

# Display timing parameters
DIGIT_DISPLAY_DURATION_MS = 350  # Digit display time
DISPLAY_PAUSE_DURATION_MS = 750  # Pause between time display cycles (tuned for 1 sec/hr at 600X)

# LED matrix pins for RP2040:bit
led_Col = [2, 3, 4, 5, 25, 7, 8, 9, 21, 22]  # Column pins

# --- Setup Hardware ---
# Configure NeoPixel panel: 448 LEDs arranged in an 8×56 grid
np_pin = machine.Pin(NEOPIXEL_PIN_NUM, machine.Pin.OUT)
pixels = neopixel.NeoPixel(np_pin, 448)

# Configure Buttons
button_a = machine.Pin(BUTTON_A_PIN_NUM, machine.Pin.IN, machine.Pin.PULL_UP)
button_b = machine.Pin(BUTTON_B_PIN_NUM, machine.Pin.IN, machine.Pin.PULL_UP)

# Setup LED matrix pins
led_pins = []
for pin_num in led_Col:
    led_pins.append(machine.Pin(pin_num, machine.Pin.OUT))

"""Define column and row pins for clarity based on led_Col"""
# Columns: GPIOs 2, 3, 4, 5, 25 (led_pins[0] to led_pins[4])
# Rows: GPIOs 7, 8, 9, 21, 22 (led_pins[5] to led_pins[9])
matrix_column_pins = [led_pins[0], led_pins[1], led_pins[2], led_pins[3], led_pins[4]]
# Rows for the indicator, ordered bottom-up for easier indexing
indicator_row_pins_bottom_up = [led_pins[9], led_pins[8], led_pins[7], led_pins[6]]
indicator_column_pin = led_pins[4] # GPIO 25

# --- 5x5 Matrix Time Display Setup ---
# Pin objects for the 5x5 matrix display
# Columns (Physical Left to Right): GPIO 25, 2, 3, 4, 5
matrix_display_columns = [led_pins[4], led_pins[0], led_pins[1], led_pins[2], led_pins[3]]
# Rows (Physical Top to Bottom): GPIO 7, 8, 9, 21, 22
matrix_display_rows = [led_pins[5], led_pins[6], led_pins[7], led_pins[8], led_pins[9]]

# 5x5 display buffer (5 rows, 5 columns)
matrix_buffer = [[0] * 5 for _ in range(5)]

# POV display parameters
POV_COL_DELAY_US = 3000  # 3000 microseconds (short = dimmer, but less flicker)

# Initialize servos at startup
# Table rotation servo
servo_pin_1 = machine.Pin(SERVO_1_PIN_NUM)
servo_pwm_1 = PWM(servo_pin_1)
servo_pwm_1.freq(PWM_FREQ)

# Primary camera trigger servo (servo2)
servo_pin_2 = machine.Pin(SERVO_2_PIN_NUM)
servo_pwm_2 = PWM(servo_pin_2)
servo_pwm_2.freq(PWM_FREQ)

# Secondary camera trigger servo 3 (Can also physcially duplicate the servo2 signal)
servo_pin_3 = machine.Pin(SERVO_3_PIN_NUM)
servo_pwm_3 = PWM(servo_pin_3)
servo_pwm_3.freq(PWM_FREQ)

# Set initial servo positions
def set_servo_angle(pwm_obj, angle):
    """Set servo to specific angle (0-270 degrees)."""
    # Constrain angle to valid range
    angle = max(0, min(SERVO_ANGLE_RANGE, angle))
   
    # Calculate duty cycle based on angle
    duty_range = MAX_DUTY - MIN_DUTY
    duty = MIN_DUTY + (angle / SERVO_ANGLE_RANGE) * duty_range
    
    try:
        # Set the duty cycle
        pwm_obj.duty_u16(int(duty))
        return True
    except Exception as e:
        print(f"Error setting servo angle: {e}")
        return False

# Initialize servo positions
set_servo_angle(servo_pwm_1, TABLE_SERVO_START_ANGLE)
set_servo_angle(servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
set_servo_angle(servo_pwm_3, CAMERA_SERVO_REST_ANGLE)

# --- Servo1 Nonlinear PWM Calibration Table ---
SERVO1_PWM_CALIBRATION_3TO4= {
    0:   1400,   # PWM for 0°
    90:  3200,   # PWM for 90°
    180: 4900,   # PWM for 180°
    270: 6600,   # PWM for 270°
    360: 8252    # PWM for 360°
}
SERVO1_PWM_CALIBRATION_1TO1= {
    0:    1400,  # PWM for 0°
    #90:  3400,  # PWM for 90° (Commented out since not needed)
    #180: 5400,  # PWM for 180°
    270:  8252,  # PWM for 270°
    #360:  8352  # PWM for 360°
}

def get_servo1_calibrated_pwm(angle):
    """Return calibrated PWM value for a given angle using the correct lookup table."""
    angle = max(0, min(360, angle))
    if SERVO_1TO1_RATIO:
        table = SERVO1_PWM_CALIBRATION_1TO1
    else:
        table = SERVO1_PWM_CALIBRATION_3TO4
    keys = sorted(table.keys())
    for i in range(len(keys) - 1):
        a0, a1 = keys[i], keys[i+1]
        if a0 <= angle <= a1:
            pwm0, pwm1 = table[a0], table[a1]
            return int(pwm0 + (pwm1 - pwm0) * (angle - a0) / (a1 - a0))
    return table[keys[-1]]

def set_servo1_angle(angle):
    """Set servo1 to a specific table angle using non-linear calibration."""
    pwm_val = get_servo1_calibrated_pwm(angle)
    try:
        servo_pwm_1.duty_u16(pwm_val)
        return True
    except Exception as e:
        print(f"Error setting servo1 PWM: {e}")
        return False

def get_rotation_camera_pwm():
    return servo_pwm_2 if ROTATION_CAMERA_SERVO == 2 else servo_pwm_3

# --- Matrix Display Functions ---
# matrix_display_columns[0] (buffer col 0) = GP25 = rightmost column (as viewed from the front)
# matrix_display_columns[1] (buffer col 1) = GP2 = leftmost column
# matrix_display_columns[2] (buffer col 2) = GP3 = 2nd column from left
# matrix_display_columns[3] (buffer col 3) = GP4 = center column
# matrix_display_columns[4] (buffer col 4) = GP5 = 2nd column from right
# The logical buffer [row][col] uses col=0 as the first entry, but this is mapped to the rightmost LED.
def refresh_pov_matrix_display():
    """Refreshes the 5x5 LED matrix using POV (Persistence Of Vision) with stabilized timing."""
    # Record start time to maintain consistent cycle timing
    cycle_start = ticks_ms()
    
    for col_idx, col_pin in enumerate(matrix_display_columns):
        # Turn off all rows before activating column (prevents ghosting)
        for row_pin in matrix_display_rows:
            row_pin.high()
            
        # Activate the current column
        col_pin.high()

        # Set row pins based on the buffer for this column
        for row_idx, row_pin in enumerate(matrix_display_rows):
            if matrix_buffer[row_idx][col_idx] == 1:
                row_pin.low()  # Turn LED ON
            else:
                row_pin.high() # Turn LED OFF

        # Keep the column active for a precise period
        sleep_us(POV_COL_DELAY_US)

        # Deactivate the current column
        col_pin.low()
    
    # Calculate total cycle time and add delay to stabilize timing
    elapsed = ticks_diff(ticks_ms(), cycle_start)
    if elapsed < 5:  # Aim for ~5ms per complete refresh
        sleep_ms(5 - elapsed)

# Minimal 3-col wide font (5 pixels high). Each character is a list of 3 columns.
# Each column is a list of 5 pixels (top to bottom).
FONT = {
    '0': [[1,1,1,1,1], [1,0,0,0,1], [1,1,1,1,1]],
    '1': [[0,0,0,0,0], [1,1,1,1,1], [0,0,0,0,0]],
    '2': [[1,0,1,1,1], [1,0,1,0,1], [1,1,1,0,1]],
    '3': [[1,0,1,0,1], [1,0,1,0,1], [1,1,1,1,1]],
    '4': [[1,1,1,0,0], [0,0,1,0,0], [1,1,1,1,1]],
    '5': [[1,1,1,0,1], [1,0,1,0,1], [1,0,1,1,1]],
    '6': [[1,1,1,1,1], [1,0,1,0,1], [1,0,1,1,1]],
    '7': [[1,0,0,0,0], [1,0,0,0,0], [1,1,1,1,1]],
    '8': [[1,1,1,1,1], [1,0,1,0,1], [1,1,1,1,1]],
    '9': [[1,1,1,0,1], [1,0,1,0,1], [1,1,1,1,1]],
    ':': [[0,0,0,0,0], [0,1,0,1,0], [0,0,0,0,0]]
}

# Helper function to clear the matrix buffer
def clear_matrix_display_buffer():
    """Clear the 5x5 LED matrix buffer by setting all elements to 0."""
    global matrix_buffer
    for r in range(5):
        for c in range(5):
            matrix_buffer[r][c] = 0

def display_single_char(char_to_display):
    """Helper function to display a character (3x5) in the center of the 5x5 matrix_buffer."""
    global matrix_buffer, FONT
    # Clear relevant part of buffer or whole buffer.
    # Columns 1, 2, 3 will be used for the 3-wide char. Cols 0 and 4 are blank. (UNTRUE!?!)
    for r_idx in range(5):
        matrix_buffer[r_idx][0] = 0 # Clear side column
        matrix_buffer[r_idx][4] = 0 # Clear other side column
        for c_idx in range(1, 4): # Clear center 3 columns
            matrix_buffer[r_idx][c_idx] = 0

    if char_to_display in FONT:
        char_pattern = FONT[char_to_display]
        char_cols = len(char_pattern)
        char_rows = len(char_pattern[0]) # Should be 5

        start_col_matrix = 1 # Display character in columns 1, 2, 3

        for c_idx_char in range(char_cols): # 0, 1, 2 for a 3-wide font
            matrix_col_idx = start_col_matrix + c_idx_char
            if matrix_col_idx < 5:
                for r_idx in range(char_rows):
                    if r_idx < 5:
                        matrix_buffer[r_idx][matrix_col_idx] = char_pattern[c_idx_char][r_idx]

def update_display_character(char_to_display):
    """Update just the character portion of the display (columns 1-3) without touching column 0 (speed indicator)"""
    global matrix_buffer, FONT
    
    # Only clear columns 1-3 (character area), preserve column 0 (speed indicator) and column 4
    for r_idx in range(5):
        for c_idx in range(1, 4):  # Clear center 3 columns only
            matrix_buffer[r_idx][c_idx] = 0

    # Draw the new character
    if char_to_display in FONT:
        char_pattern = FONT[char_to_display]
        char_cols = len(char_pattern)
        char_rows = len(char_pattern[0])
        start_col_matrix = 1  # Display character in columns 1, 2, 3
        
        for c_idx_char in range(char_cols):
            matrix_col_idx = start_col_matrix + c_idx_char
            if matrix_col_idx < 5:
                for r_idx in range(char_rows):
                    if r_idx < 5:
                        matrix_buffer[r_idx][matrix_col_idx] = char_pattern[c_idx_char][r_idx]

def update_rotation_parameters():
    """Derives rotation settings from speed and images per full rotation"""
    global DEGREES_PER_IMAGE, IMAGES_PER_ROTATION
    global ROTATION_INCREMENT_DEGREES, ROTATION_STEP_INTERVAL_MS, STILLS_IMAGING_INTERVAL_SEC
    global FINE_ROTATION_INCREMENT_DEGREES, FINE_ROTATION_STEP_INTERVAL_MS

    DEGREES_PER_IMAGE = 360.0 / IMAGES_PER_ROTATION

    # Calculate fine step interval for smoothness and speed
    total_duration = ROTATION_SPEED_PRESET_TABLE.get(ROTATION_SPEED_PRESET, 180.0)
    num_fine_steps = int(360.0 / FINE_ROTATION_INCREMENT_DEGREES)
    fine_step_interval = (total_duration * 1000) / num_fine_steps

    # If interval would be too small, increase increment to keep interval safe
    if fine_step_interval < MIN_FINE_ROTATION_STEP_INTERVAL_MS:
        fine_step_interval = MIN_FINE_ROTATION_STEP_INTERVAL_MS
        FINE_ROTATION_INCREMENT_DEGREES = 360.0 / (total_duration * 1000 / fine_step_interval)
        num_fine_steps = int(360.0 / FINE_ROTATION_INCREMENT_DEGREES)

    FINE_ROTATION_STEP_INTERVAL_MS = int(fine_step_interval)

    # For legacy/compatibility, set these to the image trigger interval
    ROTATION_INCREMENT_DEGREES = DEGREES_PER_IMAGE
    ROTATION_STEP_INTERVAL_MS = int((total_duration / IMAGES_PER_ROTATION) * 1000)
    STILLS_IMAGING_INTERVAL_SEC = ROTATION_STEP_INTERVAL_MS / 1000.0

update_rotation_parameters()

def start_program():
    """Start or restart the program execution."""
    global program_running, current_program_step, current_step_repeat
    global current_program_repeat, program_step_start_sim_time, hold_step_start_ms
    global last_printed_minute
    
    program_running = True
    current_program_step = 0
    current_step_repeat = 0
    current_program_repeat = 0
    program_step_start_sim_time = 0
    last_printed_minute = 0

    print("[PROGRAM] Started")

def stop_program():
    """Stop the program execution."""
    global program_running
    
    program_running = False
    print("[PROGRAM] Stopped")

def apply_step_settings(step_arg):
    """Apply settings for current program step (supports negative speed)."""
    global TIME_SCALE, hold_step_start_ms, start_real_time_ms, INTENSITY_SCALE, DUAL_SUN_ENABLED
    previous_speed = TIME_SCALE
    now_ms_for_calc = ticks_ms()
    current_sim_time_minutes_before_change = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms_for_calc, start_real_time_ms), previous_speed)[1]
    new_time_scale = step_arg.get("speed", 1)
    TIME_SCALE = new_time_scale
    if "intensity_scale" in step_arg:
        INTENSITY_SCALE = step_arg["intensity_scale"]
    if "dual_sun" in step_arg:
        DUAL_SUN_ENABLED = bool(step_arg["dual_sun"])
        print(f"[PROGRAM] Dual sun mode set to: {DUAL_SUN_ENABLED}")
    if TIME_SCALE != previous_speed:
        if TIME_SCALE == 0:
            # HOLD transition handled by caller freeze logic (no anchor change here)
            pass
        else:
            preserved = current_sim_time_minutes_before_change
            start_real_time_ms = _reanchor_start_time(preserved, TIME_SCALE, now_ms_for_calc, START_TIME_HHMM, start_real_time_ms)

def advance_program():
    """Advance program step/repeat (reverse-aware)."""
    global current_program_step, current_step_repeat, current_program_repeat
    global program_step_start_sim_time, start_real_time_ms, frozen_sim_time_minutes
    global program_has_completed_all_repeats
    previous_step = PROGRAM_STEPS[current_program_step]
    previous_was_hold = previous_step.get("speed", 1) == 0
    step = PROGRAM_STEPS[current_program_step]
    repeat_limit = step.get("repeat", 1)
    if current_step_repeat < repeat_limit - 1:
        current_step_repeat += 1
        print(f"[PROGRAM] Repeating step ({current_step_repeat + 1}/{repeat_limit})")
        program_step_start_sim_time = 0  # Reset to reinitialize the step on next update
        # Jump simulation time back to the step's start time for this repeat
        step_time_hhmm = step["sim_time_hhmm"]
        step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
        now_ms = ticks_ms()
        start_real_time_ms = _reanchor_start_time(step_time_minutes, TIME_SCALE, now_ms, START_TIME_HHMM, start_real_time_ms)
    else:
        current_step_repeat = 0
        current_program_step += 1
        if current_program_step >= len(PROGRAM_STEPS):
            if PROGRAM_REPEATS == -1:
                current_program_repeat += 1
                current_program_step = 0
                print(f"[PROGRAM] Repeating program (cycle {current_program_repeat + 1})")
            elif current_program_repeat < PROGRAM_REPEATS - 1:
                current_program_repeat += 1
                current_program_step = 0
                print(f"[PROGRAM] Repeating program ({current_program_repeat + 1}/{PROGRAM_REPEATS})")
            else:
                print("[PROGRAM] Complete - holding final configuration")
                stop_program()
                program_has_completed_all_repeats = True
                return
    if program_running and current_program_step < len(PROGRAM_STEPS):
        current_step = PROGRAM_STEPS[current_program_step]
        if previous_was_hold and current_step.get("speed",1) != 0:
            now_ms = ticks_ms()
            preserved = frozen_sim_time_minutes
            start_real_time_ms = _reanchor_start_time(preserved, current_step.get("speed",1), now_ms, START_TIME_HHMM, start_real_time_ms)
    program_step_start_sim_time = 0

def print_program_status(now_ms, sim_time_minutes):
    """Print program status (supports reverse progress)."""
    global hold_step_start_ms, TIME_SCALE, INTENSITY_SCALE
    if not program_running:
        return
    step = PROGRAM_STEPS[current_program_step]
    # Target is the next step's start time (where we're heading), or current step's time if not started, or N/A if last step
    if program_step_start_sim_time == 0:
        step_time_hhmm = step["sim_time_hhmm"]
        step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
    elif current_program_step < len(PROGRAM_STEPS) - 1:
        step_time_hhmm = PROGRAM_STEPS[current_program_step + 1]["sim_time_hhmm"]
        step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
    else:
        step_time_hhmm = None
        step_time_minutes = None
    target_time = f"{step_time_hhmm//100:02d}:{step_time_hhmm%100:02d}" if step_time_hhmm else "N/A"
    if TIME_SCALE == 0 and "hold_minutes" in step and hold_step_start_ms > 0:
        hold_elapsed_ms = ticks_diff(now_ms, hold_step_start_ms)
        hold_remaining = max(0, step["hold_minutes"] - (hold_elapsed_ms // 60000))
        print(f"[PROGRAM] Step {current_program_step + 1}/{len(PROGRAM_STEPS)} (Rep {current_step_repeat + 1}/{step.get('repeat', 1)}) | Target: {target_time} | HOLD | Intensity: {step.get('intensity_scale', INTENSITY_SCALE):.2f} | Remaining: {hold_remaining} minutes | Sim Time: {sim_time_minutes//60:02d}:{sim_time_minutes%60:02d}")
        return
    progress = "N/A"
    if step.get("transition", "RUN") == "RUN" and program_step_start_sim_time > 0 and step_time_minutes is not None:
        step_speed = step.get("speed", TIME_SCALE)
        direction = 1 if step_speed > 0 else (-1 if step_speed < 0 else 0)
        if direction >= 0 and step_time_minutes > program_step_start_sim_time:
            denom = step_time_minutes - program_step_start_sim_time
            if denom > 0:
                pct = (sim_time_minutes - program_step_start_sim_time) / denom * 100
                pct = max(0, min(100, pct))
                progress = f"{pct:.0f}%"
        elif direction < 0:
            start_eval = program_step_start_sim_time
            target_eval = step_time_minutes
            if step_time_minutes > start_eval:
                target_eval -= 1440
            sim_eval = sim_time_minutes
            if sim_time_minutes > start_eval:
                sim_eval -= 1440
            denom = start_eval - target_eval
            if denom > 0:
                pct = (start_eval - sim_eval) / denom * 100
                pct = max(0, min(100, pct))
                progress = f"{pct:.0f}%"
    sim_hour = int(sim_time_minutes // 60) % 24
    sim_minute = int(sim_time_minutes % 60)
    time_str = f"\x1b[1m{sim_hour:02d}:{sim_minute:02d}\x1b[0m"
    print(f"[PROGRAM] Step {current_program_step + 1}/{len(PROGRAM_STEPS)} (Rep {current_step_repeat + 1}/{step.get('repeat', 1)}) | Target: {target_time} | Speed: {TIME_SCALE}X | Intensity: {step.get('intensity_scale', INTENSITY_SCALE):.2f} | Progress: {progress} | Sim Time: {time_str}")

def update_program_state(now_ms, sim_time_minutes):
    """Update program logic with reverse-aware RUN/JUMP/HOLD evaluation."""
    global program_running, current_program_step, current_step_repeat, current_program_repeat
    global program_step_start_sim_time, last_program_status_sim_time, TIME_SCALE
    global hold_step_start_ms, last_printed_minute
    global frozen_sim_time_minutes
    if not program_running:
        return
    if int(sim_time_minutes) > last_printed_minute:
        print_program_status(now_ms, sim_time_minutes)
        last_printed_minute = int(sim_time_minutes)
    step = PROGRAM_STEPS[current_program_step]
    step_time_hhmm = step["sim_time_hhmm"]
    step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
    transition_type = step.get("transition", "RUN")
    if program_step_start_sim_time == 0:
        program_step_start_sim_time = sim_time_minutes
        apply_step_settings(step)
        # Always freeze at the current simulation time for HOLD steps, ignore sim_time_hhmm
        if TIME_SCALE == 0:
            global frozen_time_initialized
            frozen_sim_time_minutes = sim_time_minutes
            frozen_time_initialized = True
            if "hold_minutes" in step:
                hold_step_start_ms = now_ms
                print(f"[PROGRAM] Holding for {step['hold_minutes']} minutes")
            else:
                # Calculate hold duration from next step's time
                if current_program_step < len(PROGRAM_STEPS) - 1:
                    next_step = PROGRAM_STEPS[current_program_step + 1]
                    if "sim_time_hhmm" in next_step:
                        next_step_minutes = (next_step["sim_time_hhmm"] // 100) * 60 + (next_step["sim_time_hhmm"] % 100)
                        current_minutes = int(frozen_sim_time_minutes)
                        hold_duration = (next_step_minutes - current_minutes) % 1440
                        # Store calculated duration as if it were hold_minutes
                        step["hold_minutes"] = hold_duration
                        hold_step_start_ms = now_ms
                        print(f"[PROGRAM] Holding for {hold_duration} minutes")
            # Force immediate status print
            print_program_status(now_ms, sim_time_minutes)
        if transition_type == "JUMP":
            if TIME_SCALE != 0:
                start_time_minutes_calc = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
                if TIME_SCALE > 0:
                    minutes_since_start_calc = (step_time_minutes - start_time_minutes_calc) % 1440
                else:
                    minutes_since_start_calc = (start_time_minutes_calc - step_time_minutes) % 1440
                start_real_time_ms = now_ms - int((minutes_since_start_calc * 60000) / max(0.0001, abs(TIME_SCALE)))
                _ , sim_time_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)
            else:
                # Already handled above for HOLD
                pass
    is_hold_step = TIME_SCALE == 0
    target_reached = False
    # If HOLD step has hold_minutes (either explicit or calculated), use timer logic
    if is_hold_step and "hold_minutes" in step and hold_step_start_ms > 0:
        if (ticks_diff(now_ms, hold_step_start_ms) // 60000) >= step["hold_minutes"]:
            # When transitioning from HOLD to next step, jump to the next step's scheduled time
            if current_program_step < len(PROGRAM_STEPS) - 1:
                next_step = PROGRAM_STEPS[current_program_step + 1]
                if "sim_time_hhmm" in next_step:
                    next_step_minutes = (next_step["sim_time_hhmm"] // 100) * 60 + (next_step["sim_time_hhmm"] % 100)
                    frozen_sim_time_minutes = next_step_minutes
                else:
                    # No next step time specified, advance by hold duration
                    frozen_sim_time_minutes = (frozen_sim_time_minutes + step["hold_minutes"]) % 1440
            else:
                # Last step, just advance by hold duration
                frozen_sim_time_minutes = (frozen_sim_time_minutes + step["hold_minutes"]) % 1440
            target_reached = True
    elif transition_type == "RUN":
        # Check against NEXT step's time (or current step's time if last step)
        if current_program_step < len(PROGRAM_STEPS) - 1:
            next_step_hhmm = PROGRAM_STEPS[current_program_step + 1]["sim_time_hhmm"]
            target_time_minutes = (next_step_hhmm // 100) * 60 + (next_step_hhmm % 100)
        else:
            target_time_minutes = step_time_minutes
        step_speed = step.get("speed", TIME_SCALE)
        direction = 1 if step_speed > 0 else (-1 if step_speed < 0 else 0)
        speed_mag = abs(step_speed) if step_speed != 0 else 1
        tolerance = 0.2 if speed_mag <= 1 else min(3.0, speed_mag / 200)
        if direction >= 0:
            current_eval_time = sim_time_minutes
            target_eval_time = target_time_minutes
            if target_time_minutes < program_step_start_sim_time:
                if sim_time_minutes < program_step_start_sim_time:
                    current_eval_time += 1440
                target_eval_time += 1440
            if current_eval_time >= (target_eval_time - tolerance):
                target_reached = True
        else:
            start_tod = program_step_start_sim_time
            target_eval_time = target_time_minutes
            if target_time_minutes > start_tod:
                target_eval_time -= 1440
            current_eval_time = sim_time_minutes
            if sim_time_minutes > start_tod:
                current_eval_time -= 1440
            if current_eval_time <= (target_eval_time + tolerance):
                target_reached = True
    elif transition_type == "JUMP":
        target_reached = True
    if target_reached:
        advance_program()

# --- More helper Functions ---
def clamp(value, min_val=0, max_val=255):
    """Clamp pixel intensity values between min_val and max_val."""
    return max(min_val, min(max_val, value))

def get_camera_panel_indices():
    """Return a list of panel indices (0-6) to illuminate based on CAMERA_LIGHTING_PANELS."""
    if CAMERA_LIGHTING_PANELS == "ALL":
        return list(range(7))
    elif CAMERA_LIGHTING_PANELS == "MIDDLE5":
        return [1,2,3,4,5]
    elif CAMERA_LIGHTING_PANELS == "MIDDLE3":
        return [2,3,4]
    elif CAMERA_LIGHTING_PANELS == "OUTER2":
        return [0,6]
    elif CAMERA_LIGHTING_PANELS == "OUTER4":
        return [0,1,5,6]
    else:
        return list(range(7))  # Default to all

def update_speed_indicator(speed_scale):
    """Update column 0 of matrix display to show current simulation speed."""
    global matrix_buffer

    # Clear the first column (column 0) EXCEPT the top pixel used for HOLD indicator
    for r in range(1, 5):  # Start from row 1 instead of row 0
        matrix_buffer[r][0] = 0

    # HOLD mode (0X) shows no LEDs in speed column (except the topmost slowly blinking LED)
    if speed_scale == 0:
        return
    elif speed_scale == CUSTOM_TIME_SCALE:
        # For custom speed, ONLY show the second pixel from bottom
        matrix_buffer[3][0] = 1
        return
        
    # Standard speeds - determine number of LEDs to light
    num_leds_to_light = 0
    if speed_scale >= 600:
        num_leds_to_light = 4
    elif speed_scale >= 60:
        num_leds_to_light = 3
    elif speed_scale >= 6:
        num_leds_to_light = 2
    elif speed_scale >= 1:
        num_leds_to_light = 1

    # Light up the required LEDs
    if num_leds_to_light >= 1:
        matrix_buffer[4][0] = 1  # Bottom-most LED
    if num_leds_to_light >= 2:
        matrix_buffer[3][0] = 1
    if num_leds_to_light >= 3:
        matrix_buffer[2][0] = 1
    if num_leds_to_light >= 4:
        matrix_buffer[1][0] = 1

def update_mode_indicator(mode):
    """Update column 4 of matrix display to indicate simulation mode (BASIC, SCIENTIFIC)."""
    # Clear the penultimate column (column 4) EXCEPT the top pixel used for the HOLD indicator
    for r in range(1, 5):  # Start from row 1 instead of 0
        matrix_buffer[r][4] = 0

    # Determine number of LEDs to light based on mode
    if mode == "BASIC":
        num_leds = 1
    elif mode == "SCIENTIFIC":
        num_leds = 2
    else:
        num_leds = 0  # Default/error case
        
    # Light up the required LEDs in matrix_buffer (column 4)
    if num_leds >= 1:
        matrix_buffer[4][4] = 1  # Bottom-most LED
    if num_leds >= 2:
        matrix_buffer[3][4] = 1  # Second LED from bottom

def update_hold_indicator(now_ms, is_hold_mode):
    """Update the top-left pixel to blink when in HOLD mode."""
    global matrix_buffer
    
    if not is_hold_mode:
        # Not in HOLD mode, ensure indicator is off
        matrix_buffer[0][0] = 0
        return
        
    # In HOLD mode, blink the top-left pixel at 1Hz (500ms on, 500ms off)
    blink_cycle = (now_ms // 1000) % 2  # 0 or 1
    matrix_buffer[0][0] = blink_cycle

# --- Rotation Cycle State Machine ---
def update_rotation_cycle(now_ms, abs_sim_time, sim_time_scale):
    """Update the rotation cycle state machine.
    This function is called from the main loop to handle the 360° imaging cycle."""
    global rotation_state, rotation_in_progress, current_rotation_angle
    global last_rotation_step_time_ms, last_rotation_absolute_time, camera_trigger_started_ms
    global return_angle, ROTATION_ENABLED, ROTATION_CAMERA_ENABLED
    global servo2_controlled_by_rotation, rotation_lighting_active
    global last_stills_trigger_ms, manual_rotation_triggered
    
    # Skip rotation updates if rotation is disabled and we're not in the middle of a cycle
    if not ROTATION_ENABLED and rotation_state == 'IDLE' and not manual_rotation_triggered:
        return
    
    # Only start a new cycle if we're in 1X mode 
    # (but continue a cycle that's already in progress regardless of speed)
    if sim_time_scale > 1 and rotation_state == 'IDLE':
        return
    
    # Check if we need to initialize a new rotation cycle (at startup or hourly)
    current_sim_minute = int(abs_sim_time)
    last_rotation_minute = int(last_rotation_absolute_time)

    # Calculate the next scheduled rotation time
    next_rotation_time = last_rotation_minute + ROTATION_CYCLE_INTERVAL_MINUTES

    # Only trigger when crossing a scheduled threshold, not just when time has passed
    time_for_new_cycle = (current_sim_minute >= next_rotation_time or
                          last_rotation_absolute_time == 0)  # First run
    
    if rotation_state == 'IDLE' and time_for_new_cycle:
        # Check if it's nighttime and rotation at night is disabled
        current_time = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)[1]
        sun_x, _, sun_size, _, _, _ = get_sun_position(current_time)
        
        # Sun is visible if any part of it is within display area (-8 to 55)
        half_size = sun_size // 2
        sun_visible = (sun_x + half_size > 0) and (sun_x - half_size < 56)
        
        # Skip starting new rotation cycle if it's nighttime and ROTATION_AT_NIGHT is False
        if not sun_visible and not ROTATION_AT_NIGHT:
            print("Skipping rotation cycle - nighttime and ROTATION_AT_NIGHT is False")
            # Update the last rotation time to prevent continuous checking
            last_rotation_absolute_time = abs_sim_time
            return
        print(f"Starting new 360° imaging cycle at sim time {current_sim_minute}m")
        
        manual_rotation_triggered = False  # Reset manual trigger flag
        # Initialize cycle variables
        rotation_state = 'INITIAL_CAMERA_TRIGGER' if ROTATION_CAMERA_ENABLED else 'ROTATING'
        rotation_in_progress = True
        current_rotation_angle = 0
        
        # Initialize STILLS mode timer if in STILLS mode
        if ROTATION_CAPTURE_MODE == "STILLS":
            last_stills_trigger_ms = now_ms
        
        if ROTATION_CAMERA_ENABLED:
            # Only block servo2 if it's being used for rotation imaging
            servo2_controlled_by_rotation = (ROTATION_CAMERA_SERVO == 2)
            camera_trigger_started_ms = now_ms
            set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_TRIGGER_ANGLE)
            print(f"Initial camera trigger at {CAMERA_SERVO_TRIGGER_ANGLE} deg")
            
            # If in STILLS mode, activate lighting for entire rotation now
            if ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                apply_rotation_lighting()
                
        else:
            # Skip camera trigger and go straight to rotation
            last_rotation_step_time_ms = now_ms
            if SERVO_1TO1_RATIO:
                table_servo_angle = current_rotation_angle
            else:
                table_servo_angle = (current_rotation_angle / 360) * SERVO_ANGLE_RANGE
            print(f"Starting rotation (camera trigger disabled)")
            set_servo1_angle(current_rotation_angle)
            # Activate rotation lighting if enabled
            if ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                apply_rotation_lighting()
    
    # Handle the different states of the rotation cycle
    if rotation_state == 'INITIAL_CAMERA_TRIGGER':
        # Check if camera trigger hold time has elapsed
        if ticks_diff(now_ms, camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
            # Release camera trigger
            set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_REST_ANGLE)
            print(f"Initial camera trigger released")
            
            # Move to rotation state
            rotation_state = 'ROTATING'
            last_rotation_step_time_ms = now_ms
            
            # Start the first rotation step immediately
            # Table angle: 0-270° servo maps to 0-360° table in default 3:4 ratio
            if SERVO_1TO1_RATIO:
                table_servo_angle = current_rotation_angle
            else:
                table_servo_angle = (current_rotation_angle / 360) * SERVO_ANGLE_RANGE
            set_servo1_angle(current_rotation_angle)

            # For VIDEO mode, activate lighting now if enabled
            # For STILLS mode, lighting is already activated in the initial trigger
            if ROTATION_CAPTURE_MODE == "VIDEO" and ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                apply_rotation_lighting()
    
    elif rotation_state == 'ROTATING':
        # --- Smooth fine-grained servo movement ---
        # Calculate next imaging angle
        image_angle = 360.0 / IMAGES_PER_ROTATION
        next_trigger_idx = int(current_rotation_angle // image_angle)
        next_trigger_angle = (next_trigger_idx + 1) * image_angle

        # Only move if not at or past 360
        if current_rotation_angle < 360:
            # Calculate what the next step would be
            next_angle = current_rotation_angle + FINE_ROTATION_INCREMENT_DEGREES

            # If the next step would overshoot the next imaging angle, move directly to the imaging angle
            if next_angle > next_trigger_angle - 1e-6:  # small epsilon for float precision
                # Move directly to the exact imaging angle
                current_rotation_angle = next_trigger_angle
                if current_rotation_angle > 360:
                    current_rotation_angle = 360  # Clamp at 360

                table_servo_angle = (current_rotation_angle / 360) * SERVO_ANGLE_RANGE       
                print(f"Rotating table to {current_rotation_angle:.1f} deg (servo angle: {table_servo_angle:.1f} deg)")
                set_servo1_angle(current_rotation_angle)
                
                # Trigger camera at this exact angle if in STILLS mode
                if (ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_CAMERA_ENABLED and current_rotation_angle < 360):
                    if ticks_diff(now_ms, last_stills_trigger_ms) >= STILLS_IMAGING_INTERVAL_SEC * 1000:
                        last_stills_trigger_ms = now_ms
                        last_rotation_step_time_ms = now_ms
                        rotation_state = 'ROTATION_CAMERA_TRIGGER'
                        camera_trigger_started_ms = now_ms
                        set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_TRIGGER_ANGLE)
                        print(f"STILLS mode: Camera trigger at {current_rotation_angle:.1f} deg")
                        return  # Wait for trigger to finish before next move

            # Otherwise, continue smooth stepping
            elif ticks_diff(now_ms, last_rotation_step_time_ms) >= FINE_ROTATION_STEP_INTERVAL_MS:
                current_rotation_angle = next_angle
                if current_rotation_angle > 360:
                    current_rotation_angle = 360  # Clamp at 360

                table_servo_angle = (current_rotation_angle / 360) * SERVO_ANGLE_RANGE
                
                # Only print occasionally to avoid console spam
                #if int(current_rotation_angle) % 10 == 0 or current_rotation_angle == 360:
                set_servo1_angle(current_rotation_angle)
                last_rotation_step_time_ms = now_ms

        # --- End of rotation ---
        if current_rotation_angle >= 360:
            # Turn off rotation lighting for VIDEO mode
            # For STILLS mode, keep lighting on until after DWELL state
            if ROTATION_CAPTURE_MODE == "VIDEO" and rotation_lighting_active:
                deactivate_rotation_lighting()
            
            if ROTATION_CAMERA_ENABLED and ROTATION_CAPTURE_MODE == "VIDEO":
                # Move to camera trigger state (only for VIDEO mode)
                rotation_state = 'FINAL_CAMERA_TRIGGER'
                camera_trigger_started_ms = now_ms
                set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_TRIGGER_ANGLE)
                print(f"Rotation complete, triggering camera at {CAMERA_SERVO_TRIGGER_ANGLE} deg")
            else:
                # Skip camera trigger and go straight to dwell
                rotation_state = 'DWELL'
                last_rotation_step_time_ms = now_ms
                if ROTATION_CAPTURE_MODE == "VIDEO":
                    print("Rotation complete, moving to dwell state")

    # New state for STILLS mode camera triggers during rotation
    elif rotation_state == 'ROTATION_CAMERA_TRIGGER':
        # Check if camera trigger hold time has elapsed
        if ticks_diff(now_ms, camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
            set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_REST_ANGLE)
            print(f"STILLS mode: Camera trigger released")
            rotation_state = 'ROTATING'
            last_rotation_step_time_ms = now_ms  # Reset rotation timing
    
    elif rotation_state == 'FINAL_CAMERA_TRIGGER':
        # Only used in VIDEO mode
        # Check if camera trigger hold time has elapsed
        if ticks_diff(now_ms, camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
            # Release camera trigger
            set_servo_angle(get_rotation_camera_pwm(), CAMERA_SERVO_REST_ANGLE)
            print(f"Final camera trigger released, returning to {CAMERA_SERVO_REST_ANGLE} deg")
            
            rotation_state = 'RETURNING'
            return_angle = current_rotation_angle  # Start returning from current angle (should be 360)
            last_rotation_step_time_ms = now_ms
            print(f"Starting gradual return to start position from {return_angle} deg")
    
    elif rotation_state == 'DWELL':
        # Check if dwell time has elapsed
        if ticks_diff(now_ms, last_rotation_step_time_ms) >= DWELL_TIME_MS:  # 1500ms dwell
            # Turn off STILLS mode lighting after dwell if active
            if ROTATION_CAPTURE_MODE == "STILLS" and rotation_lighting_active:
                deactivate_rotation_lighting()
                
            # Initialize return movement
            rotation_state = 'RETURNING'
            return_angle = current_rotation_angle  # Start from current angle (360°)
            last_rotation_step_time_ms = now_ms
            print(f"Starting gradual return to start position from {return_angle} deg")
    
    elif rotation_state == 'RETURNING':
        # Check if it's time for the next return step
        if ticks_diff(now_ms, last_rotation_step_time_ms) >= RETURN_STEP_INTERVAL_MS:
            # Decrement angle by the step size (but don't go below 0)
            return_angle = max(0, return_angle - RETURN_STEP_DEGREES)
            
            # Set new servo position
            if SERVO_1TO1_RATIO:
                table_servo_angle = return_angle
            else:
                table_servo_angle = (return_angle / 360) * SERVO_ANGLE_RANGE
            
            # Only print occasionally to avoid console spam (every 10 degrees)
            if return_angle % 90 == 0 or return_angle == 0:
                print(f"Returning table to {return_angle} deg (servo angle: {table_servo_angle:.1f} deg)")
            set_servo1_angle(return_angle)

            last_rotation_step_time_ms = now_ms
            
            # Check if we've completed the return movement
            if return_angle <= 0:
                # Record time of completed rotation for hourly tracking
                last_rotation_absolute_time = abs_sim_time
                
                # End the imaging cycle
                rotation_state = 'IDLE'
                rotation_in_progress = False
                servo2_controlled_by_rotation = False  # Release servo2 control
                print("Imaging cycle complete, table smoothly returned to start position")

# --- Standalone Servo2 Control ---
def update_standalone_servo2(now_ms):
    """Updates the standalone servo2 (primary camera trigger) at regular real-time intervals."""
    global servo2_state, last_servo2_trigger_ms, servo2_trigger_start_ms, servo2_controlled_by_rotation
    global camera_lighting_active, servo2_using_lighting, camera_light_hold_until_ms

    # Skip if rotation is in control, or if standalone is disabled AND the servo is idle.
    if servo2_controlled_by_rotation or (not SERVO2_STANDALONE_ENABLED and servo2_state == 'IDLE'):
        return

    # Determine if sun is currently visible on the display
    current_time = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)[1]
    sun_x, _, sun_size, _, _, _ = get_sun_position(current_time)
    half_size = sun_size // 2
    sun_visible = (sun_x + half_size > 0) and (sun_x - half_size < 56)

    # --- Only skip the TRIGGER logic at night, not the RELEASE logic ---
    if servo2_state == 'IDLE':
        if not sun_visible and not IMAGE_AT_NIGHT:
            return
        if ticks_diff(now_ms, last_servo2_trigger_ms) >= (SERVO2_INTERVAL_SEC * 1000):
            # Time to trigger the servo
            servo2_state = 'TRIGGERED'
            servo2_trigger_start_ms = now_ms
            if CAMERA_LIGHTING_ENABLED and not rotation_lighting_active:
                camera_lighting_active = True
                servo2_using_lighting = True
                apply_camera_lighting()
            sleep_ms(10)
            set_servo_angle(servo_pwm_2, CAMERA_SERVO_TRIGGER_ANGLE)
            safe_print(f"Standalone camera on servo2 trigger activated" + (" (night mode)" if not sun_visible else ""))
    elif servo2_state == 'TRIGGERED':
        # Always run this block, even at night
        if ticks_diff(now_ms, servo2_trigger_start_ms) >= SERVO2_TRIGGER_HOLD_MS:
            servo2_state = 'IDLE'
            set_servo_angle(servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
            safe_print("Camera trigger released")
            last_servo2_trigger_ms = now_ms
            if camera_lighting_active and not rotation_lighting_active:
                servo2_using_lighting = False
                # Instead of turning off immediately, set a hold-until time
                camera_light_hold_until_ms = now_ms + CAMERA_LIGHT_HOLD_MS

# --- Standalone Servo3 Control ---
def update_standalone_servo3(now_ms):
    """Updates the standalone servo3 (second camera trigger) at regular real-time intervals.
    This function operates independently of the rotation cycle and servo2."""
    global servo3_state, last_servo3_trigger_ms, servo3_trigger_start_ms
    global servo3_using_lighting, camera_lighting_active, servo2_using_lighting, camera_light_hold_until_ms, rotation_lighting_active

    # Skip if standalone mode is disabled AND the servo is idle.
    # This allows a manual trigger to complete its cycle.
    if not SERVO3_STANDALONE_ENABLED and servo3_state == 'IDLE':
        return

    # Determine if it's nighttime
    current_time = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)[1]
    sun_x, _, sun_size, _, _, _ = get_sun_position(current_time)
    half_size = sun_size // 2
    sun_visible = (sun_x + half_size > 0) and (sun_x - half_size < 56)

    # --- Only skip the TRIGGER logic at night, not the RELEASE logic ---
    if servo3_state == 'IDLE':
        # Night operation check for servo3
        # If it's night, only run servo3 if servo2 would also run at night
        if not sun_visible:
            servo2_runs_at_night = IMAGE_AT_NIGHT and SERVO2_STANDALONE_ENABLED
            if not servo2_runs_at_night:
                return  # Skip servo3 triggering at night if servo2 wouldn't run

        # Check if it's time to trigger servo3 (convert seconds to milliseconds)
        if ticks_diff(now_ms, last_servo3_trigger_ms) >= (SERVO3_INTERVAL_SEC * 1000):
            # Time to trigger the servo
            servo3_state = 'TRIGGERED'
            servo3_trigger_start_ms = now_ms

            # Apply camera lighting if enabled and rotation lighting is not active
            if SERVO3_LIGHTING_ENABLED and not rotation_lighting_active:
                servo3_using_lighting = True
                camera_lighting_active = True
                apply_camera_lighting()

            # Move the servo
            set_servo_angle(servo_pwm_3, CAMERA_SERVO_TRIGGER_ANGLE)
            print(f"Second camera on servo3 trigger activated")
    elif servo3_state == 'TRIGGERED':
        if ticks_diff(now_ms, servo3_trigger_start_ms) >= SERVO3_TRIGGER_HOLD_MS:
            servo3_state = 'IDLE'
            last_servo3_trigger_ms = now_ms  # Reset the timer
            set_servo_angle(servo_pwm_3, CAMERA_SERVO_REST_ANGLE)
            if camera_lighting_active and servo3_using_lighting and not rotation_lighting_active:
                servo3_using_lighting = False
                # Instead of turning off immediately, set a hold-until time
                camera_light_hold_until_ms = now_ms + CAMERA_LIGHT_HOLD_MS
            else:
                servo3_using_lighting = False

# --- Scientific solar calculation helper functions ---
def date_to_day_number(date_yyyymmdd):
    """Convert YYYYMMDD format to day of year (1-366)"""
    year = date_yyyymmdd // 10000
    month = (date_yyyymmdd // 100) % 100
    day = date_yyyymmdd % 100
    
    # Month day counts - index 0 is placeholder
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Leap year adjustment
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_month[2] = 29
    
    day_of_year = sum(days_in_month[:month]) + day
    return day_of_year

def calculate_declination(day_of_year):
    """Calculate solar declination angle for given day of year"""
    # Approximation formula for declination
    angle = 23.45 * math.sin(math.radians(360/365 * (day_of_year - 81)))
    return angle

def equation_of_time(day_of_year):
    """Calculate equation of time adjustment in minutes"""
    # B is the fractional year in radians
    B = 2 * math.pi * (day_of_year - 1) / 365
    # Approximation formula for equation of time
    eot = 229.18 * (0.000075 + 0.001868*math.cos(B) - 0.032077*math.sin(B) 
                    - 0.014615*math.cos(2*B) - 0.040849*math.sin(2*B))
    return eot

# Configure solar cycle
SUNRISE_TIME = 0
SUNSET_TIME = 0
DAY_LENGTH = 0

# --- Functions for time and sun position ---
def init_solar_day():
    """Configure the simulated solar day based on selected model."""
    global SUNRISE_TIME, SUNSET_TIME, DAY_LENGTH, SIMULATION_DATE
    
    if SOLAR_MODE == "SCIENTIFIC":
        # Scientific model - calculate based on date and location
        day_of_year = date_to_day_number(SIMULATION_DATE)
        
        # Calculate solar declination for this day
        declination = calculate_declination(day_of_year)
        
        # Calculate sunrise/sunset hour angle
        latitude_rad = math.radians(LATITUDE)
        declination_rad = math.radians(declination)
        
        # Calculate sunset hour angle in radians
        cos_sunset_angle = -math.tan(latitude_rad) * math.tan(declination_rad)
        
        # Handle special cases (polar day/night)
        if cos_sunset_angle < -1:
            # Polar day (sun never sets)
            SUNRISE_TIME = 0
            SUNSET_TIME = 24 * 60
        elif cos_sunset_angle > 1:
            # Polar night (sun never rises)
            SUNRISE_TIME = 12 * 60
            SUNSET_TIME = 12 * 60
        else:
            # Normal case: sun rises and sets
            sunset_angle = math.acos(cos_sunset_angle)
            sunset_angle_deg = math.degrees(sunset_angle)
            
            # Convert to hours (15° per hour)
            sunset_hour = sunset_angle_deg / 15
            
            # Apply equation of time and longitude corrections
            eot_minutes = equation_of_time(day_of_year)
            longitude_correction = (TIME_ZONE_OFFSET * 15 - LONGITUDE) / 15 * 60
            
            # Calculate sunrise and sunset in minutes from midnight
            solar_noon_minutes = (12 * 60 + 
                                  longitude_correction - 
                                  eot_minutes)
            sunrise_minutes = int(solar_noon_minutes - sunset_hour * 60)
            sunset_minutes = int(solar_noon_minutes + sunset_hour * 60)
            
            # Ensure values are within 0-1440 range
            SUNRISE_TIME = sunrise_minutes % 1440
            SUNSET_TIME = sunset_minutes % 1440
        
        print(f"SCIENTIFIC model: Date: {SIMULATION_DATE}, Day: {day_of_year}")
        print(f"Sun size varies based on elevation angle")
    else:  # BASIC
        # Basic model with fixed sunrise/sunset times and fixed sun size
        SUNRISE_TIME = 6 * 60  # 6:00 AM in minutes
        SUNSET_TIME = 18 * 60  # 6:00 PM in minutes
        print(f"BASIC model: Fixed sunrise/sunset times, constant 8x8 sun size")

        # Add this line to show SUN_COLOR_MODE setting
    print(f"Sun color mode: {SUN_COLOR_MODE}")
    
    # Calculate day length in minutes
    if SUNSET_TIME >= SUNRISE_TIME:
        DAY_LENGTH = SUNSET_TIME - SUNRISE_TIME
    else:
        DAY_LENGTH = (SUNSET_TIME + 1440) - SUNRISE_TIME
    
    print(f"Sunrise: {SUNRISE_TIME//60:02d}:{SUNRISE_TIME%60:02d}, Sunset: {SUNSET_TIME//60:02d}:{SUNSET_TIME%60:02d}")
    print(f"Day length: {DAY_LENGTH//60}h {DAY_LENGTH%60}m")

def get_sim_time(start_time_hhmm, real_time_ms, time_scale):
    """Return (abs_sim_minutes, time_of_day_minutes) with reverse support.
    Forward: abs grows, clock advances. Reverse: abs grows, clock rewinds. HOLD: frozen."""
    if time_scale == 0:
        return frozen_abs_sim_time, frozen_sim_time_minutes
    start_hour = start_time_hhmm // 100
    start_minute = start_time_hhmm % 100
    start_time_minutes = start_hour * 60 + start_minute
    if time_scale > 0:
        sim_minutes_elapsed = (real_time_ms / 60000) * time_scale
        abs_sim_time = sim_minutes_elapsed
        tod = (start_time_minutes + int(sim_minutes_elapsed)) % 1440
        return abs_sim_time, tod
    mag = -time_scale
    sim_minutes_elapsed_pos = (real_time_ms / 60000) * mag
    abs_sim_time = sim_minutes_elapsed_pos
    tod = (start_time_minutes - int(sim_minutes_elapsed_pos)) % 1440
    return abs_sim_time, tod

def time_to_display_chars(minutes):
    """Convert minutes (0-1439) to displayable characters for all digits."""
    hours = minutes // 60
    mins = minutes % 60
    
    # Split hours into tens and ones digits with leading zero
    hour_tens_char = str(hours // 10)  # First digit of hours (0-2)
    hour_ones_char = str(hours % 10)   # Second digit of hours (0-9)
    
    # Split minutes into tens and ones digits
    minute_tens_char = str(mins // 10)
    minute_ones_char = str(mins % 10)
    
    return hour_tens_char, hour_ones_char, minute_tens_char, minute_ones_char

def xy_to_index(x, y):
    """Convert (x, y) coordinates to a NeoPixel index."""
    visual_panel = x // 8
    physical_panel = 6 - visual_panel
    panel_x = x % 8
    if y % 2 == 1:  # For odd rows, reverse direction
        panel_x = 7 - panel_x
    panel_index = y * 8 + panel_x
    return physical_panel * 64 + panel_index

def fill_panel(r, g, b, duration_sec=30):
    """Fill the entire panel with a single color."""
    global panel_buffer, manual_panel_override_active, manual_panel_override_until_ms
    color = (r, g, b)
    pixels.fill(color)
    pixels.write()
    # Update the state buffer to match the physical panel
    panel_buffer = [color] * len(pixels)
    manual_panel_override_active = True
    manual_panel_override_until_ms = ticks_ms() + int(duration_sec * 1000)

def _draw_sun_to_panel(buffer, x, y, size, r, g, b):
    """Draws a single square sun onto a given buffer object without writing."""
    # Convert coordinates and size to integers, rounding x to nearest pixel
    x_int = int(x + 0.5)
    y_int = int(y)
    size_int = int(size)
    
    # Pre-clamp base color components
    r_base = clamp(r)
    g_base = clamp(g)
    b_base = clamp(b)
    
    # Calculate the size in pixels (half-width from center)
    half_size = size_int // 2
    
    # Calculate start position, allowing it to be partially off-screen
    start_x = x_int - half_size
    start_y = max(0, y_int - half_size)
    
    # Calculate and draw the sun pixels directly into the provided buffer object
    for y_offset in range(size_int):
        for x_offset in range(size_int):
            pos_x = start_x + x_offset
            pos_y = start_y + y_offset
            
            # Skip pixels that are off-screen
            if not (0 <= pos_x < 56 and 0 <= pos_y < 8):
                continue
                
            # Get the NeoPixel index for this position
            idx = xy_to_index(pos_x, pos_y)
            
            if idx < len(buffer):
                buffer[idx] = (r_base, g_base, b_base)

def update_sun_display(minute_of_day):
    """Calculates sun positions and updates only the changed pixels on the panel
    using a delta-buffer comparison to prevent flicker and unnecessary writes."""
    global DUAL_SUN_ENABLED, panel_buffer

    # 1. Create a new buffer for the next frame, initialized to black.
    next_frame_buffer = [(0, 0, 0)] * len(pixels)

    # 2. Get primary sun's parameters
    x, y, size, r, g, b = get_sun_position(minute_of_day)

    # 3. Draw the sun(s) into the temporary next_frame_buffer
    if size > 0:
        _draw_sun_to_panel(next_frame_buffer, x, y, size, r, g, b)

        # 4. If dual sun mode is enabled, draw the mirrored sun symmetrically
        if DUAL_SUN_ENABLED:
            # To ensure perfect symmetry, we can't just mirror the float 'x'.
            # We must calculate the integer pixel bounds of the primary sun and mirror those bounds.
            
            # First, determine the integer geometry of the primary sun.
            x_int = int(x + 0.5)
            size_int = int(size)
            half_size = size_int // 2
            start_x_primary = x_int - half_size
            end_x_primary = start_x_primary + size_int - 1
            
            # Second, calculate the start coordinate for a perfectly mirrored sun.
            start_x_mirrored = 55 - end_x_primary
            
            # Third, calculate a "fake" float center 'x' that will produce the
            # correct integer start position when passed to the drawing function.
            x_mirrored_fake = float(start_x_mirrored + half_size)

            _draw_sun_to_panel(next_frame_buffer, x_mirrored_fake, y, size, r, g, b)

    # 5. Compare the new frame with the current state and update only the differences.
    pixels_changed = False
    for i in range(len(pixels)):
        if panel_buffer[i] != next_frame_buffer[i]:
            panel_buffer[i] = next_frame_buffer[i]  # Update our state buffer
            pixels[i] = next_frame_buffer[i]        # Update the hardware buffer
            pixels_changed = True

    # 6. Write to the panel only if something actually changed.
    if pixels_changed:
        pixels.write()

def calculate_solar_elevation(minute_of_day, day_of_year):
    """Calculate solar elevation angle based on time and location"""
    # Convert minute of day to hour angle
    solar_noon_minutes = 12 * 60
    eot_minutes = equation_of_time(day_of_year)
    longitude_correction = (TIME_ZONE_OFFSET * 15 - LONGITUDE) / 15 * 60
    adjusted_minutes = minute_of_day + eot_minutes - longitude_correction
    
    # Hour angle (15° per hour, 0 at solar noon)
    hour_angle = (adjusted_minutes - solar_noon_minutes) * 0.25 # 0.25 degrees per minute
    hour_angle_rad = math.radians(hour_angle)
    
    # Solar declination in radians
    declination = calculate_declination(day_of_year)
    declination_rad = math.radians(declination)
    
    # Latitude in radians
    latitude_rad = math.radians(LATITUDE)
    
    # Calculate solar elevation
    sin_elevation = (math.sin(latitude_rad) * math.sin(declination_rad) + 
                    math.cos(latitude_rad) * math.cos(declination_rad) * 
                    math.cos(hour_angle_rad))
    
    elevation_rad = math.asin(max(-1, min(1, sin_elevation)))
    elevation_deg = math.degrees(elevation_rad)
    
    return elevation_deg

def get_sun_position(minute_of_day):
    """Calculate sun position and intensity based on selected mode."""
    global SOLAR_MODE
    
    if SOLAR_MODE == "SCIENTIFIC":
        return get_scientific_sun_position(minute_of_day)
    else:
        # Default to BASIC
        return get_basic_sun_position(minute_of_day)

def get_scientific_sun_position(minute_of_day):
    """Calculate scientifically accurate sun position and intensity."""
    # Default values for nighttime
    x, y = -10, 4  # Off-screen
    size = 0
    r, g, b = 0, 0, 0
    
    # Get day of year from simulation date
    day_of_year = date_to_day_number(SIMULATION_DATE)
    
    # Calculate solar elevation angle
    elevation = calculate_solar_elevation(minute_of_day, day_of_year)
    
    # Check if it's daytime (elevation > 0)
    if elevation > 0:
        # Calculate position based on time between sunrise and sunset
        if SUNSET_TIME > SUNRISE_TIME:
            day_position = (minute_of_day - SUNRISE_TIME) / DAY_LENGTH
        else:
            # Handle case where sunset is after midnight
            adjusted_minute = minute_of_day
            if minute_of_day < SUNSET_TIME:
                adjusted_minute += 1440
            day_position = (adjusted_minute - SUNRISE_TIME) / DAY_LENGTH
            
        # Ensure day_position is between 0 and 1
        day_position = max(0, min(1, day_position))
        
        # Symmetrical path from 0.5 to 54.5 to ensure symmetrical rendering at edges
        x = 0.5 + day_position * 54
        
        # Calculate sun size based on elevation angle
        # Maximum size (8) at high elevations, smaller at low angles
        size = 2 + 6 * min(1, elevation / 45)  # Full size when sun is 45° or higher
        size = round(size / 2) * 2  # Round to even number (2, 4, 6, 8)
        
        # Calculate vertical center position
        y = (8 - size) // 2 + size //  2
        
        # Sun color calculation (more red at low angles)
        r = 255
        if elevation < 10:  # More red at very low angles
            sunrise_factor = elevation / 10
            g = int(100 + 155 * sunrise_factor)
            b = int(50 + 205 * sunrise_factor)
        else:
            g = 255
            b = 255
        
        # Calculate intensity based on air mass
        # Air mass approximation (Kasten and Young formula)
        air_mass = 1 / (math.sin(math.radians(elevation)) + 0.50572 * 
                      math.pow(elevation + 6.07995, -1.6364))
        
        # Beer-Lambert law for intensity
        extinction = 0.21  # Clear sky extinction coefficient
        rel_intensity = math.exp(-extinction * air_mass)
        
        # Scale brightness
        brightness_factor = rel_intensity * INTENSITY_SCALE
        
        r = clamp(int(r * brightness_factor), 0, MAX_BRIGHTNESS)
        g = clamp(int(g * brightness_factor), 0, MAX_BRIGHTNESS)
        b = clamp(int(b * brightness_factor), 0, MAX_BRIGHTNESS)
    if SUN_COLOR_MODE == "CUSTOM":
        if SOLAR_MODE == "BASIC":
            r, g, b = CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B
        else:
            r = clamp(int(CUSTOM_SUN_R * brightness_factor), 0, MAX_BRIGHTNESS)
            g = clamp(int(CUSTOM_SUN_G * brightness_factor), 0, MAX_BRIGHTNESS)
            b = clamp(int(CUSTOM_SUN_B * brightness_factor), 0, MAX_BRIGHTNESS)
    # Override with blue-only if that mode is selected
    if SUN_COLOR_MODE == "BLUE":
        r = 0
        g = 0
        # Keep the calculated b value unchanged for intensity simulation
    return x, y, size, r, g, b



def get_basic_sun_position(minute_of_day):
    """Calculate sun position using the basic model with constant 8x8 square."""
    # Default values for nighttime
    x, y = -10, 0  # Off-screen
    size = 8       # Always 8×8 when visible
    
    # Basic RGB values (225, 225, 255) as specified
    r = 225
    g = 225
    b = 255
    
    # Apply intensity scaling and cap at 255
    r = clamp(int(r * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)
    g = clamp(int(g * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)
    b = clamp(int(b * INTENSITY_SCALE), 0, MAX_BRIGHTNESS)
    
    # Fixed sunrise at 6:00 AM
    sunrise_time = 6 * 60   # 6:00 AM in minutes
    
    # The sun should completely disappear at 6:00 PM (18:00)
    sunset_complete_time = 18 * 60  # 6:00 PM in minutes
    
    # Total visible time should be exactly 12 hours (720 minutes)
    total_day_minutes = 720  # 12 hours
    
    # Calculate minutes since sunrise
    minutes_since_sunrise = minute_of_day - sunrise_time
    
    # Check if it's during the visible period (sunrise to complete sunset)
    # Include exactly sunset time (<=)
    if sunrise_time <= minute_of_day <= sunset_complete_time:
        # Position sun at x=-4 at exactly 6:00 AM, then move across screen to x=59 by 6:00 PM
        # Total travel distance: 63 positions over 720 minutes
        travel_range = 63  # From -4 to 59 inclusive
        
        # Use (total_day_minutes - 1) to ensure we hit exactly x=59 at sunset
        raw_position = -4 + (minutes_since_sunrise / (total_day_minutes - 1)) * travel_range
        
        # Return the raw float position for accurate rounding later
        x = raw_position
    if SUN_COLOR_MODE == "CUSTOM":
        r, g, b = CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B
    # Override with blue-only if that mode is selected
    if SUN_COLOR_MODE == "BLUE":
        r = 0
        g = 0
        # Keep the calculated b value unchanged for intensity simulation
    return x, y, size, r, g, b

def apply_camera_lighting():
    """Activate lighting for camera operation using CAMERA_LIGHTING_PANELS selection."""
    global panel_buffer
    color = (CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B)
    pixels.fill((0,0,0))
    panel_indices = get_camera_panel_indices()
    for panel in panel_indices:
        for y in range(8):
            for x in range(8):
                idx = xy_to_index(panel*8 + x, y)
                pixels[idx] = color
    pixels.write()
    for i in range(len(panel_buffer)):
        panel_buffer[i] = pixels[i]
    print(f"Camera lighting activated on panels {panel_indices}: RGB({CAMERA_LIGHT_R},{CAMERA_LIGHT_G},{CAMERA_LIGHT_B})")

def deactivate_camera_lighting():
    """Turn off camera lighting if no servo is currently using it."""
    global camera_lighting_active, servo2_using_lighting, servo3_using_lighting, rotation_lighting_active, panel_buffer
    
    # Only deactivate if neither servo is using the lighting
    if not servo2_using_lighting and not servo3_using_lighting:
        camera_lighting_active = False
        
        # If rotation lighting is also not active, turn off the panel.
        # Otherwise, let the rotation lighting take precedence.
        if not rotation_lighting_active:
            color = (0, 0, 0)
            pixels.fill(color)
            pixels.write()
            panel_buffer = [color] * len(pixels) # Sync state buffer

def apply_rotation_lighting():
    """Activate uniform lighting for rotation cycle, overriding normal display."""
    global rotation_lighting_active, panel_buffer

    color = (ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B)
    # First, turn off all pixels
    pixels.fill((0,0,0))
    # Light up only the selected panels
    panel_indices = get_camera_panel_indices()
    for panel in panel_indices:
        for y in range(8):
            for x in range(8):
                idx = xy_to_index(panel*8 + x, y)
                pixels[idx] = color
    pixels.write()
    # Update the state buffer to match
    for i in range(len(panel_buffer)):
        panel_buffer[i] = pixels[i]
    rotation_lighting_active = True
    print(f"Rotation lighting activated on panels {panel_indices}: RGB({ROTATION_LIGHT_R},{ROTATION_LIGHT_G},{ROTATION_LIGHT_B})")

def deactivate_rotation_lighting():
    """Turn off rotation lighting and reset display variables."""
    global rotation_lighting_active, panel_buffer
    
    rotation_lighting_active = False
    
    color = (0, 0, 0)
    pixels.fill(color)
    pixels.write()
    panel_buffer = [color] * len(pixels) # Sync state buffer

# =================================================

#         # Sun quick info (x & size only to minimize payload)
#         sun_x, _sun_y, sun_size, _sr, _sg, _sb = get_sun_position(time_of_day_minutes)

#         status = {
#             "type": "status",            # Allows filtering if other JSON types added later
#             "ts": now_ms,                 # Ticks ms (monotonic)
#             "sim": sim_hhmm,              # HHMM integer
#             "scale": TIME_SCALE,          # Time scale factor (can be negative / 0)
#             "speed": get_speed_name(TIME_SCALE),
#             "solar": SOLAR_MODE,
#             "sunColor": SUN_COLOR_MODE,
#             "intensity": INTENSITY_SCALE,
#             "dualSun": DUAL_SUN_ENABLED,
#             "rotation": ROTATION_ENABLED,
#             "rotState": rotation_state,
#             "rotAng": round(current_rotation_angle, 1),
#             "rotInProg": rotation_in_progress,
#             "servo2": servo2_state,
#             "servo3": servo3_state,
#             "imgAtNight": IMAGE_AT_NIGHT,
#             "rotAtNight": ROTATION_AT_NIGHT,
#             "progRun": program_running,
#             "progStep": (current_program_step + 1) if program_running else 0,
#             "progStepTarget": (PROGRAM_STEPS[current_program_step].get("sim_time_hhmm") if (program_running and PROGRAM_STEPS) else None),
#             "progStepRep": (current_step_repeat + 1) if program_running else 0,
#             "progRep": (current_program_repeat + 1) if program_running else 0,
#             "sunX": round(sun_x, 1),
#             "sunSize": sun_size,
#             "memFree": gc.mem_free(),
#         }
#         # Single-line JSON
#         print(json.dumps(status))
#     except Exception as e:
#         # Fail silently except for a concise note to avoid spamming; avoid nested f-string braces complexity
#         try:
#             print('{"jsonError":"' + str(e).replace('"','\"') + '"}')
#         except Exception:
#             pass

def handle_command(command_str):
    """Parses and executes a command received over serial."""
    global TIME_SCALE, start_real_time_ms, frozen_sim_time_minutes, frozen_abs_sim_time
    global program_running, current_program_step, PROGRAM_STEPS, START_TIME_HHMM
    global servo2_state, servo2_controlled_by_rotation, servo2_trigger_start_ms, last_servo2_trigger_ms
    global servo3_state, servo3_trigger_start_ms, last_servo3_trigger_ms, servo3_using_lighting
    global camera_lighting_active, rotation_lighting_active, INTENSITY_SCALE, DUAL_SUN_ENABLED
    global PROGRAM_ENABLED, ROTATION_ENABLED, SERVO2_STANDALONE_ENABLED, SERVO3_STANDALONE_ENABLED, RESTART_AFTER_LOAD, AUTO_LOAD_LATEST_PROFILE
    global SERVO2_INTERVAL_SEC, SERVO3_INTERVAL_SEC, ROTATION_CYCLE_INTERVAL_MINUTES
    global SUN_COLOR_MODE, ROTATION_CAPTURE_MODE, SIMULATION_DATE, LATITUDE, SOLAR_MODE
    global current_step_repeat, program_step_start_sim_time, program_has_completed_all_repeats
    global STILLS_IMAGING_INTERVAL_SEC, CAMERA_TRIGGER_HOLD_MS, ROTATION_INCREMENT_DEGREES
    global ROTATION_STEP_INTERVAL_MS, IMAGES_PER_ROTATION, DEGREES_PER_IMAGE
    global ROTATION_SPEED_PRESET, ROTATION_SPEED_PRESET_TABLE
    global FINE_ROTATION_INCREMENT_DEGREES, FINE_ROTATION_STEP_INTERVAL_MS, SERVO_1TO1_RATIO
    global PROGRAM_ENABLED, PROGRAM_STEPS, PROGRAM_REPEATS, ROTATION_CAMERA_SERVO
    parts = command_str.lower().strip().split()
    if not parts:
        return

    command = parts[0]
    
    try:
        if command == "set" and len(parts) >= 3:
            param = parts[1]
            value = parts[2]

            if param == "imageatnight":
                if value.lower() in ("true", "on", "1"):
                    global IMAGE_AT_NIGHT
                    IMAGE_AT_NIGHT = True
                    print("[SERIAL CMD] IMAGE_AT_NIGHT set to True")
                elif value.lower() in ("false", "off", "0"):
                    IMAGE_AT_NIGHT = False
                    print("[SERIAL CMD] IMAGE_AT_NIGHT set to False")
                else:
                    print("[SERIAL CMD] Error: imageatnight must be true/on/1 or false/off/0.")
                return
            elif param == "rotationatnight":
                if value.lower() in ("true", "on", "1"):
                    global ROTATION_AT_NIGHT
                    ROTATION_AT_NIGHT = True
                    print("[SERIAL CMD] ROTATION_AT_NIGHT set to True")
                elif value.lower() in ("false", "off", "0"):
                    ROTATION_AT_NIGHT = False
                    print("[SERIAL CMD] ROTATION_AT_NIGHT set to False")
                else:
                    print("[SERIAL CMD] Error: rotationatnight must be true/on/1 or false/off/0.")
                return
            elif param == "rotationcameraservo":
                if value in ("2", "3"):
                    ROTATION_CAMERA_SERVO = int(value)
                    print(f"[SERIAL CMD] Rotation imaging will use servo {ROTATION_CAMERA_SERVO}")
                else:
                    print("[SERIAL CMD] Error: rotationcameraservo must be 2 or 3.")
                return

            if param == "rot_speed":
                preset = value.lower()
                if preset in ROTATION_SPEED_PRESET_TABLE:
                    ROTATION_SPEED_PRESET = preset
                    update_rotation_parameters()
                    print(f"[SERIAL CMD] Rotation speed preset set to '{ROTATION_SPEED_PRESET}' ({ROTATION_SPEED_PRESET_TABLE[ROTATION_SPEED_PRESET]}s per 360°)")
                else:
                    print("[SERIAL CMD] Error: Invalid rot_speed. Use 'slow', 'medium', or 'fast'.")
                return
            elif param == "images_per_rotation":
                try:
                    n = int(value)
                    if 2 <= n <= 360:
                        IMAGES_PER_ROTATION = n
                        update_rotation_parameters()
                        print(f"[SERIAL CMD] Images per rotation set to {IMAGES_PER_ROTATION} (every {DEGREES_PER_IMAGE:.2f}°)")
                    else:
                        print("[SERIAL CMD] Error: images_per_rotation must be 2-360.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid images_per_rotation '{value}'. Must be integer.")
                return
            elif param == "degrees_per_image":
                try:
                    deg = float(value)
                    if 0 < deg <= 180:
                        IMAGES_PER_ROTATION = int(round(360.0 / deg))
                        update_rotation_parameters()
                        print(f"[SERIAL CMD] Degrees per image set to {DEGREES_PER_IMAGE:.2f}° ({IMAGES_PER_ROTATION} images per rotation)")
                    else:
                        print("[SERIAL CMD] Error: degrees_per_image must be >0 and <=180.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid degrees_per_image '{value}'. Must be float.")
                return
            elif param == "cameralightingpanels":
                global CAMERA_LIGHTING_PANELS
                allowed = ["ALL", "MIDDLE5", "MIDDLE3", "OUTER2", "OUTER4"]
                if value.upper() in allowed:
                    CAMERA_LIGHTING_PANELS = value.upper()
                    print(f"[SERIAL CMD] Camera lighting panels set to {CAMERA_LIGHTING_PANELS}")
                else:
                    print(f"[SERIAL CMD] Error: cameralightingpanels must be one of {allowed}")
                return
            elif param == "cameralightrgb" and len(parts) >= 5:
                try:
                    global CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B
                    r = int(parts[2])
                    g = int(parts[3])
                    b = int(parts[4])
                    CAMERA_LIGHT_R = clamp(r)
                    CAMERA_LIGHT_G = clamp(g)
                    CAMERA_LIGHT_B = clamp(b)
                    print(f"[SERIAL CMD] Camera light RGB set to ({CAMERA_LIGHT_R}, {CAMERA_LIGHT_G}, {CAMERA_LIGHT_B})")
                except (ValueError, IndexError):
                    print("[SERIAL CMD] Error: cameralightrgb requires 3 integer values (0-255)")
                return
            elif param == "rotationlightrgb" and len(parts) >= 5:
                try:
                    global ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B
                    r = int(parts[2])
                    g = int(parts[3])
                    b = int(parts[4])
                    ROTATION_LIGHT_R = clamp(r)
                    ROTATION_LIGHT_G = clamp(g)
                    ROTATION_LIGHT_B = clamp(b)
                    print(f"[SERIAL CMD] Rotation light RGB set to ({ROTATION_LIGHT_R}, {ROTATION_LIGHT_G}, {ROTATION_LIGHT_B})")
                except (ValueError, IndexError):
                    print("[SERIAL CMD] Error: rotationlightrgb requires 3 integer values (0-255)")
                return
            if param == "speed":
                new_speed = float(value)
                now_ms = ticks_ms()
                abs_sim_time, current_time_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)
                old_time_scale = TIME_SCALE
                TIME_SCALE = new_speed
                if TIME_SCALE == 0:
                    frozen_sim_time_minutes = current_time_minutes
                    frozen_abs_sim_time = abs_sim_time
                else:
                    preserved = frozen_sim_time_minutes if old_time_scale == 0 else current_time_minutes
                    start_real_time_ms = _reanchor_start_time(preserved, TIME_SCALE, now_ms, START_TIME_HHMM, start_real_time_ms)
                print(f"[SERIAL CMD] Time scale set to {get_speed_name(TIME_SCALE)}")
                update_speed_indicator(TIME_SCALE)  # Update matrix display
            elif param == "autoload":
                # Explicit on/off to persist AUTO_LOAD_LATEST_PROFILE
                val = value.lower()
                if val in ("on","true","1"):
                    AUTO_LOAD_LATEST_PROFILE = True
                elif val in ("off","false","0"):
                    AUTO_LOAD_LATEST_PROFILE = False
                else:
                    print("[SERIAL CMD] Error: autoload must be on/off/true/false/1/0")
                    return
                try:
                    with open('autoload.cfg','w') as f:
                        f.write('1' if AUTO_LOAD_LATEST_PROFILE else '0')
                    print(f"[SERIAL CMD] Auto-load latest profile set to: {AUTO_LOAD_LATEST_PROFILE} (persisted)")
                except Exception as e:
                    print(f"[SERIAL CMD] Auto-load latest profile set to: {AUTO_LOAD_LATEST_PROFILE} (NOT persisted: {e})")
                return
            
            elif param == "time":
                try:
                    target_hhmm = int(value)
                    target_minutes = (target_hhmm // 100) * 60 + (target_hhmm % 100)

                    if not (0 <= target_minutes < 1440):
                        print("[SERIAL CMD] Error: Invalid time. Must be between 0000 and 2359.")
                        return

                    now_ms = ticks_ms()
                    if TIME_SCALE == 0: # HOLD mode
                        frozen_sim_time_minutes = target_minutes
                        print(f"[SERIAL CMD] HOLD mode: Time set to {target_minutes//60:02d}:{target_minutes%60:02d}")
                    else: # RUNNING mode (forward or reverse)
                        start_time_minutes = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
                        if TIME_SCALE > 0:
                            minutes_since_start = (target_minutes - start_time_minutes) % 1440
                        else: # reverse anchor calculation: distance backward from start to target
                            minutes_since_start = (start_time_minutes - target_minutes) % 1440
                        start_real_time_ms = now_ms - int((minutes_since_start * 60000) / max(0.0001, abs(TIME_SCALE)))
                        print(f"[SERIAL CMD] Time jumped to {target_minutes//60:02d}:{target_minutes%60:02d}")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid time value '{value}'. Must be integer HHMM.")

            elif param == "starttime":
                try:
                    new_start_time = int(value)
                    if not (0 <= new_start_time <= 2359 and new_start_time % 100 < 60):
                        print("[SERIAL CMD] Error: Invalid time. Must be between 0000 and 2359.")
                        return
                    
                    now_ms = ticks_ms()
                    _, current_time_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)

                    START_TIME_HHMM = new_start_time
                    print(f"[SERIAL CMD] Start time anchor set to {START_TIME_HHMM:04d}")

                    if TIME_SCALE > 0:
                        start_time_minutes = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
                        minutes_since_start = (current_time_minutes - start_time_minutes) % 1440
                        start_real_time_ms = now_ms - int((minutes_since_start * 60000) / TIME_SCALE)
                        print("[SERIAL CMD] Time anchor reset to preserve current simulation time.")
                    else:
                        print("[SERIAL CMD] In HOLD mode. New start time will be used when simulation resumes.")

                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid start time value '{value}'. Must be an integer HHMM.")

            elif param == "intensity":
                try:
                    new_intensity = float(value)
                    if new_intensity >= 0:
                        INTENSITY_SCALE = new_intensity
                        print(f"[SERIAL CMD] Global intensity scale set to {INTENSITY_SCALE}")
                    else:
                        print("[SERIAL CMD] Error: Intensity must be a non-negative number.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid intensity value '{value}'. Must be a number.")

            elif param == "servo2interval":
                try:
                    new_interval = int(value)
                    if new_interval > 0:
                        SERVO2_INTERVAL_SEC = new_interval
                        print(f"[SERIAL CMD] Servo 2 standalone interval set to {SERVO2_INTERVAL_SEC}s")
                    else:
                        print("[SERIAL CMD] Error: Interval must be a positive number.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid interval value '{value}'. Must be an integer.")

            elif param == "servo3interval":
                try:
                    new_interval = int(value)
                    if new_interval > 0:
                        SERVO3_INTERVAL_SEC = new_interval
                        print(f"[SERIAL CMD] Servo 3 standalone interval set to {SERVO3_INTERVAL_SEC}s")
                    else:
                        print("[SERIAL CMD] Error: Interval must be a positive number.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid interval value '{value}'. Must be an integer.")

            elif param == "rotationinterval":
                try:
                    new_interval = int(value)
                    if new_interval > 0:
                        ROTATION_CYCLE_INTERVAL_MINUTES = new_interval
                        print(f"[SERIAL CMD] Rotation cycle interval set to {ROTATION_CYCLE_INTERVAL_MINUTES} sim minutes")
                    else:
                        print("[SERIAL CMD] Error: Interval must be a positive number.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid interval value '{value}'. Must be an integer.")

            elif param == "suncolor":
                if value in ("natural", "blue"):
                    SUN_COLOR_MODE = value.upper()
                    print(f"[SERIAL CMD] Sun color mode set to {SUN_COLOR_MODE}")
                    init_solar_day()
                elif value == "custom" and len(parts) == 6:
                    try:
                        r = int(parts[3])
                        g = int(parts[4])
                        b = int(parts[5])
                        # Clamp and warn if needed
                        for name, v in zip(('R','G','B'), (r,g,b)):
                            if v < 0 or v > 255:
                                print(f"[SERIAL CMD] Warning: {name} value {v} out of range, clamped to 0-255.")
                        r = clamp(r)
                        g = clamp(g)
                        b = clamp(b)
                        global CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B
                        CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B = r, g, b
                        SUN_COLOR_MODE = "CUSTOM"
                        print(f"[SERIAL CMD] Sun color mode set to CUSTOM: RGB({r},{g},{b})")
                        init_solar_day()
                    except Exception as e:
                        print("[SERIAL CMD] Error: Usage is set suncolor custom <r> <g> <b>")
                else:
                    print("[SERIAL CMD] Error: Invalid suncolor. Use 'natural', 'blue', or 'custom <r> <g> <b>'.")
            elif param == "rotationmode":
                if value in ("stills", "video"):
                    ROTATION_CAPTURE_MODE = value.upper()
                    print(f"[SERIAL CMD] Rotation capture mode set to {ROTATION_CAPTURE_MODE}")
                else:
                    print("[SERIAL CMD] Error: Invalid rotationmode. Use 'stills' or 'video'.")

            elif param == "date":
                try:
                    new_date = int(value)
                    if 20000101 <= new_date <= 21001231:
                        SIMULATION_DATE = new_date
                        print(f"[SERIAL CMD] Simulation date set to {SIMULATION_DATE}")
                        init_solar_day() # Recalculate solar parameters
                    else:
                        print("[SERIAL CMD] Error: Invalid date format. Use YYYYMMDD.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid date value '{value}'. Must be a number.")

            elif param == "latitude":
                try:
                    new_lat = float(value)
                    if -90 <= new_lat <= 90:
                        LATITUDE = new_lat
                        print(f"[SERIAL CMD] Latitude set to {LATITUDE} degrees")
                        init_solar_day() # Recalculate solar parameters
                    else:
                        print("[SERIAL CMD] Error: Latitude must be between -90 and 90.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid latitude value '{value}'. Must be a number.")

            elif param == "solarmode":
                if value in ("basic", "scientific"):
                    SOLAR_MODE = value.upper()
                    print(f"[SERIAL CMD] Solar mode set to {SOLAR_MODE}")
                    init_solar_day() # Recalculate and print new settings
                    update_mode_indicator(SOLAR_MODE) # Update matrix display
                else:
                    print("[SERIAL CMD] Error: Invalid solar mode. Use 'basic' or 'scientific'.")

            # --- Rotation Imaging Parameter Short Names ---
            elif param == "rot_stills_intv":
                try:
                    new_val = float(value)
                    if new_val > 0:
                        STILLS_IMAGING_INTERVAL_SEC = new_val
                        print(f"[SERIAL CMD] STILLS imaging interval set to {STILLS_IMAGING_INTERVAL_SEC} sec")
                    else:
                        print("[SERIAL CMD] Error: Interval must be > 0.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid value '{value}'. Must be a float.")
            elif param == "rot_trig_hold":
                try:
                    new_val = int(value)
                    if new_val > 0:
                        CAMERA_TRIGGER_HOLD_MS = new_val
                        print(f"[SERIAL CMD] Camera trigger hold set to {CAMERA_TRIGGER_HOLD_MS} ms")
                    else:
                        print("[SERIAL CMD] Error: Hold time must be > 0.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid value '{value}'. Must be an integer.")
            elif param == "rot_inc_deg":
                try:
                    new_val = float(value)
                    if new_val > 0:
                        ROTATION_INCREMENT_DEGREES = new_val
                        print(f"[SERIAL CMD] Rotation increment set to {ROTATION_INCREMENT_DEGREES} deg")
                    else:
                        print("[SERIAL CMD] Error: Increment must be > 0.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid value '{value}'. Must be a float.")
            elif param == "rot_step_intv":
                try:
                    new_val = int(value)
                    if new_val > 0:
                        ROTATION_STEP_INTERVAL_MS = new_val
                        print(f"[SERIAL CMD] Rotation step interval set to {ROTATION_STEP_INTERVAL_MS} ms")
                    else:
                        print("[SERIAL CMD] Error: Step interval must be > 0.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid value '{value}'. Must be an integer.")
            else:
                print(f"[SERIAL CMD] Error: Unknown parameter '{param}' for 'set' command.")
                return
        elif command == "jump" and len(parts) >= 2:
            target = parts[1]
            if not program_running:
                print("[SERIAL CMD] Error: Cannot jump, program is not running.")
                return

            if target == "nextstep":
                current_program_step = (current_program_step + 1) % len(PROGRAM_STEPS)
                current_step_repeat = 0

                # Immediately update sim time to match the new step's target time
                new_step = PROGRAM_STEPS[current_program_step]
                target_hhmm = new_step["sim_time_hhmm"]
                target_minutes = (target_hhmm // 100) * 60 + (target_hhmm % 100)

                # Re-anchor the time system to the new step's time
                now_ms = ticks_ms()
                new_speed = new_step.get("speed", 1)

                if new_speed == 0:
                    # HOLD mode: freeze at target time
                    frozen_sim_time_minutes = target_minutes
                else:
                    # Running mode: update TIME_SCALE and re-anchor so we're at target_minutes right now
                    TIME_SCALE = new_speed
                    start_real_time_ms = _reanchor_start_time(target_minutes, new_speed, now_ms, START_TIME_HHMM, start_real_time_ms)

                program_step_start_sim_time = 0  # This triggers the step logic in the main loop
                print(f"[SERIAL CMD] Jumping program to step {current_program_step + 1} at {target_hhmm:04d}.")

            elif target == "step" and len(parts) == 3:
                try:
                    step_num = int(parts[2])
                    if 1 <= step_num <= len(PROGRAM_STEPS):
                        step_index = step_num - 1
                        current_program_step = step_index
                        current_step_repeat = 0

                        # Immediately update sim time to match the new step's target time
                        new_step = PROGRAM_STEPS[current_program_step]
                        target_hhmm = new_step["sim_time_hhmm"]
                        target_minutes = (target_hhmm // 100) * 60 + (target_hhmm % 100)

                        # Re-anchor the time system to the new step's time
                        now_ms = ticks_ms()
                        new_speed = new_step.get("speed", 1)

                        if new_speed == 0:
                            # HOLD mode: freeze at target time
                            frozen_sim_time_minutes = target_minutes
                        else:
                            # Running mode: update TIME_SCALE and re-anchor so we're at target_minutes right now
                            TIME_SCALE = new_speed
                            start_real_time_ms = _reanchor_start_time(target_minutes, new_speed, now_ms, START_TIME_HHMM, start_real_time_ms)

                        program_step_start_sim_time = 0  # This triggers the step logic in the main loop
                        print(f"[SERIAL CMD] Jumping program to step {step_num} at {target_hhmm:04d}.")
                    else:
                        print(f"[SERIAL CMD] Error: Invalid step number. Must be between 1 and {len(PROGRAM_STEPS)}.")
                except ValueError:
                    print(f"[SERIAL CMD] Error: Invalid step number '{parts[2]}'. Must be an integer.")
            else:
                print(f"[SERIAL CMD] Error: Unknown jump command. Use 'jump nextstep' or 'jump step <n>'.")

        elif command == "toggle" and len(parts) == 2:
            target = parts[1]
            if target == "dualsun":
                DUAL_SUN_ENABLED = not DUAL_SUN_ENABLED
                print(f"[SERIAL CMD] Dual sun mode set to: {DUAL_SUN_ENABLED}")
            elif target == "program":
                PROGRAM_ENABLED = not PROGRAM_ENABLED
                print(f"[SERIAL CMD] Program execution set to: {PROGRAM_ENABLED}")
            elif target == "rotation":
                ROTATION_ENABLED = not ROTATION_ENABLED
                print(f"[SERIAL CMD] Rotation cycle set to: {ROTATION_ENABLED}")
            elif target == "servo2":
                SERVO2_STANDALONE_ENABLED = not SERVO2_STANDALONE_ENABLED
                print(f"[SERIAL CMD] Servo 2 standalone trigger set to: {SERVO2_STANDALONE_ENABLED}")
            elif target == "servo3":
                SERVO3_STANDALONE_ENABLED = not SERVO3_STANDALONE_ENABLED
                print(f"[SERIAL CMD] Servo 3 standalone trigger set to: {SERVO3_STANDALONE_ENABLED}")
            elif target == "restartafterload":
                RESTART_AFTER_LOAD = not RESTART_AFTER_LOAD
                print(f"[SERIAL CMD] Restart after load set to: {RESTART_AFTER_LOAD}")
            elif target == "1to1ratio":
                SERVO_1TO1_RATIO = not SERVO_1TO1_RATIO
                print(f"[SERIAL CMD] Servo-to-table 1:1 ratio set to: {SERVO_1TO1_RATIO}")
            else:
                if target == "autoload":
                    print("[SERIAL CMD] Error: 'toggle autoload' removed. Use 'set autoload on|off'.")
                else:
                    print(f"[SERIAL CMD] Error: Unknown toggle target '{target}'.")

        elif command == "program" and len(parts) == 2 and parts[1] == "status":
            print(f"PROGRAM_ENABLED: {PROGRAM_ENABLED}")
            print(f"PROGRAM_REPEATS: {PROGRAM_REPEATS}")
            print("PROGRAM_STEPS:")
            for i, step in enumerate(PROGRAM_STEPS):
                print(f"  Step {i+1}: {step}")
            return

        elif command == "trigger" and len(parts) == 2:
            target_servo = parts[1]
            now_ms = ticks_ms()

            if target_servo == "servo2":
                if servo2_state != 'IDLE' or servo2_controlled_by_rotation:
                    print("[SERIAL CMD] Error: Servo 2 is currently busy.")
                else:
                    # Manually start the trigger sequence using the existing state machine
                    servo2_state = 'TRIGGERED'
                    servo2_trigger_start_ms = now_ms
                    last_servo2_trigger_ms = now_ms # Reset auto-trigger timer

                    if CAMERA_LIGHTING_ENABLED and not rotation_lighting_active:
                        camera_lighting_active = True
                        apply_camera_lighting()
                    
                    set_servo_angle(servo_pwm_2, CAMERA_SERVO_TRIGGER_ANGLE)
                    print("[SERIAL CMD] Manually triggering photo with Servo 2.")

            elif target_servo == "servo3":
                if servo3_state != 'IDLE':
                    print("[SERIAL CMD] Error: Servo 3 is currently busy.")
                else:
                    # Manually start the trigger sequence
                    servo3_state = 'TRIGGERED'
                    servo3_trigger_start_ms = now_ms
                    last_servo3_trigger_ms = now_ms # Reset auto-trigger timer

                    if SERVO3_LIGHTING_ENABLED and not rotation_lighting_active:
                        servo3_using_lighting = True
                        camera_lighting_active = True
                        apply_camera_lighting()

                    set_servo_angle(servo_pwm_3, CAMERA_SERVO_TRIGGER_ANGLE)
                    print("[SERIAL CMD] Manually triggering photo with Servo 3.")
            elif target_servo == "rotation":
                if rotation_in_progress:
                    print("[SERIAL CMD] Error: Rotation cycle is already in progress.")
                else:
                    # Force start a new rotation cycle immediately
                    global last_rotation_absolute_time, rotation_state, manual_rotation_triggered
                    last_rotation_absolute_time = -ROTATION_CYCLE_INTERVAL_MINUTES  # Ensures time_for_new_cycle is True
                    rotation_state = 'IDLE'  # Reset state to allow new cycle
                    manual_rotation_triggered = True  # Flag to indicate manual trigger
                    print("[SERIAL CMD] Manual rotation imaging cycle triggered.")
            else:
                print(f"[SERIAL CMD] Error: Unknown target '{target_servo}'. Use 'servo2', 'servo3', or 'rotation'.")

        elif command == "savelog":
            if len(parts) == 2:
                datecode = parts[1]
                # Basic validation for the datecode
                if len(datecode) == 8 and datecode.isdigit():
                    filename = f"settings_{datecode}.txt"
                    try:
                        # Get current sim time for the log entry
                        now_ms = ticks_ms()
                        _, time_of_day_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)
                        sim_hour = int(time_of_day_minutes // 60) % 24
                        sim_minute = int(time_of_day_minutes % 60)
                        
                        # Open file in append mode to add new entries
                        with open(filename, "a") as f:
                            f.write(f"--- Settings Logged on {datecode} at sim time {sim_hour:02d}:{sim_minute:02d} ---\n")
                            f.write(f"START_TIME_HHMM = {START_TIME_HHMM}\n")
                            f.write(f"TIME_SCALE = {TIME_SCALE}\n")
                            f.write(f"INTENSITY_SCALE = {INTENSITY_SCALE}\n")
                            f.write(f"SIMULATION_DATE = {SIMULATION_DATE}\n")
                            f.write(f"LATITUDE = {LATITUDE}\n")
                            f.write(f"SOLAR_MODE = \"{SOLAR_MODE}\"\n")
                            f.write(f"SUN_COLOR_MODE = \"{SUN_COLOR_MODE}\"\n")
                            f.write(f"DUAL_SUN_ENABLED = {DUAL_SUN_ENABLED}\n")
                            f.write(f"PROGRAM_ENABLED = {PROGRAM_ENABLED}\n")
                            f.write(f"ROTATION_ENABLED = {ROTATION_ENABLED}\n")
                            f.write(f"ROTATION_CAPTURE_MODE = \"{ROTATION_CAPTURE_MODE}\"\n")
                            f.write(f"ROTATION_CYCLE_INTERVAL_MINUTES = {ROTATION_CYCLE_INTERVAL_MINUTES}\n")
                            f.write(f"SERVO2_STANDALONE_ENABLED = {SERVO2_STANDALONE_ENABLED}\n")
                            f.write(f"SERVO2_INTERVAL_SEC = {SERVO2_INTERVAL_SEC}\n")
                            f.write(f"SERVO3_STANDALONE_ENABLED = {SERVO3_STANDALONE_ENABLED}\n")
                            f.write(f"SERVO3_INTERVAL_SEC = {SERVO3_INTERVAL_SEC}\n")
                            f.write(f"ROTATION_CAMERA_SERVO = {ROTATION_CAMERA_SERVO}\n")
                            f.write(f"RESTART_AFTER_LOAD = {RESTART_AFTER_LOAD}\n")
                            f.write(f"STILLS_IMAGING_INTERVAL_SEC = {STILLS_IMAGING_INTERVAL_SEC}\n")
                            f.write(f"CAMERA_TRIGGER_HOLD_MS = {CAMERA_TRIGGER_HOLD_MS}\n")
                            f.write(f"ROTATION_SPEED_PRESET = \"{ROTATION_SPEED_PRESET}\"\n")
                            f.write(f"IMAGES_PER_ROTATION = {IMAGES_PER_ROTATION}\n")
                            f.write(f"DEGREES_PER_IMAGE = {DEGREES_PER_IMAGE:.2f}\n")
                            f.write(f"ROTATION_INCREMENT_DEGREES = {ROTATION_INCREMENT_DEGREES}\n")
                            f.write(f"ROTATION_STEP_INTERVAL_MS = {ROTATION_STEP_INTERVAL_MS}\n")
                            f.write(f"IMAGE_AT_NIGHT = {IMAGE_AT_NIGHT}\n")
                            f.write(f"ROTATION_AT_NIGHT = {ROTATION_AT_NIGHT}\n")
                            f.write("-" * 20 + "\n\n")
                        print(f"[SERIAL CMD] Settings appended to log {filename}")
                    except Exception as e:
                        print(f"[SERIAL CMD] Auto-load latest profile set to: {AUTO_LOAD_LATEST_PROFILE} (NOT persisted: {e})")
                else:
                    print("[SERIAL CMD] Error: Invalid datecode format. Use YYYYMMDD.")
            else:
                print("[SERIAL CMD] Usage: savelog <yyyymmdd>")

        elif command == "saveprofile":
            # PATCH: Support optional note after profile name
            if len(parts) >= 2:
                profilename = parts[1]
                note = " ".join(parts[2:]) if len(parts) > 2 else ""
                filename = f"{profilename}.txt"
                try:
                    with open(filename, "w") as f: # Use "w" to overwrite
                        print(f"[SERIAL CMD] Saving current settings to profile {filename}...")
                        # --- Write note if provided ---
                        if note:
                            f.write(f"NOTE = {note}\n")
                        # --- Write all configurable parameters ---
                        f.write(f"START_TIME_HHMM = {START_TIME_HHMM}\n")
                        f.write(f"TIME_SCALE = {TIME_SCALE}\n")
                        f.write(f"INTENSITY_SCALE = {INTENSITY_SCALE}\n")
                        f.write(f"SIMULATION_DATE = {SIMULATION_DATE}\n")
                        f.write(f"LATITUDE = {LATITUDE}\n")
                        f.write(f"SOLAR_MODE = \"{SOLAR_MODE}\"\n")
                        f.write(f"SUN_COLOR_MODE = \"{SUN_COLOR_MODE}\"\n")
                        f.write(f"DUAL_SUN_ENABLED = {DUAL_SUN_ENABLED}\n")
                        f.write(f"ROTATION_ENABLED = {ROTATION_ENABLED}\n")
                        f.write(f"ROTATION_CAPTURE_MODE = \"{ROTATION_CAPTURE_MODE}\"\n")
                        f.write(f"ROTATION_CYCLE_INTERVAL_MINUTES = {ROTATION_CYCLE_INTERVAL_MINUTES}\n")
                        f.write(f"SERVO2_STANDALONE_ENABLED = {SERVO2_STANDALONE_ENABLED}\n")
                        f.write(f"SERVO2_INTERVAL_SEC = {SERVO2_INTERVAL_SEC}\n")
                        f.write(f"SERVO3_STANDALONE_ENABLED = {SERVO3_STANDALONE_ENABLED}\n")
                        f.write(f"SERVO3_INTERVAL_SEC = {SERVO3_INTERVAL_SEC}\n")
                        f.write(f"ROTATION_CAMERA_SERVO = {ROTATION_CAMERA_SERVO}\n")
                        f.write(f"RESTART_AFTER_LOAD = {RESTART_AFTER_LOAD}\n")
                        f.write(f"STILLS_IMAGING_INTERVAL_SEC = {STILLS_IMAGING_INTERVAL_SEC}\n")
                        f.write(f"CAMERA_TRIGGER_HOLD_MS = {CAMERA_TRIGGER_HOLD_MS}\n")
                        f.write(f"ROTATION_SPEED_PRESET = \"{ROTATION_SPEED_PRESET}\"\n")
                        f.write(f"IMAGES_PER_ROTATION = {IMAGES_PER_ROTATION}\n")
                        f.write(f"DEGREES_PER_IMAGE = {DEGREES_PER_IMAGE:.2f}\n")
                        f.write(f"ROTATION_INCREMENT_DEGREES = {ROTATION_INCREMENT_DEGREES}\n")
                        f.write(f"ROTATION_STEP_INTERVAL_MS = {ROTATION_STEP_INTERVAL_MS}\n")
                        f.write(f"IMAGE_AT_NIGHT = {IMAGE_AT_NIGHT}\n")
                        f.write(f"ROTATION_AT_NIGHT = {ROTATION_AT_NIGHT}\n")
                        f.write(f"CUSTOM_SUN_R = {CUSTOM_SUN_R}\n")
                        f.write(f"CUSTOM_SUN_G = {CUSTOM_SUN_G}\n")
                        f.write(f"CUSTOM_SUN_B = {CUSTOM_SUN_B}\n")
                        # Save program state and related fields only once
                        if PROGRAM_ENABLED:
                            import ujson as json  # Use ujson for MicroPython
                            f.write("PROGRAM_ENABLED = True\n")
                            f.write(f"PROGRAM_REPEATS = {PROGRAM_REPEATS}\n")
                            f.write(f"PROGRAM_STEPS = {json.dumps(PROGRAM_STEPS)}\n")
                        else:
                            f.write("PROGRAM_ENABLED = False\n")
                    print(f"[SERIAL CMD] Profile '{filename}' saved successfully.")
                except Exception as e:
                    print(f"[SERIAL CMD] Error saving profile: {e}")
            else:
                print("[SERIAL CMD] Usage: saveprofile <profilename> [optional note]")

        elif command == "loadprofile":
            if len(parts) == 2:
                profilename = parts[1]
                filename = f"{profilename}.txt"
                
                try:
                    os.stat(filename)
                except OSError:
                    print(f"[SERIAL CMD] Error: Profile '{filename}' not found.")
                    return

                validated_settings = {}
                try:
                    with open(filename, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'): continue
                            
                            key, value_str = line.split('=', 1)
                            key = key.strip()
                            value_str = value_str.strip()

                            if key == "START_TIME_HHMM":
                                v = int(value_str)
                                if not (0 <= v <= 2359 and v % 100 < 60): raise ValueError("invalid HHMM format")
                                validated_settings[key] = v
                            elif key == "TIME_SCALE": validated_settings[key] = float(value_str)
                            elif key == "INTENSITY_SCALE":
                                v = float(value_str);
                                if v < 0: raise ValueError("must be non-negative")
                                validated_settings[key] = v
                            elif key == "SIMULATION_DATE":
                                v = int(value_str);
                                if not (20000101 <= v <= 21001231): raise ValueError("out of range")
                                validated_settings[key] = v
                            elif key == "LATITUDE":
                                v = float(value_str);
                                if not (-90 <= v <= 90): raise ValueError("must be -90 to 90")
                                validated_settings[key] = v
                            elif key in ("SOLAR_MODE", "SUN_COLOR_MODE", "ROTATION_CAPTURE_MODE"):
                                validated_settings[key] = value_str.strip('"')
                            elif key in ("DUAL_SUN_ENABLED", "PROGRAM_ENABLED", "ROTATION_ENABLED", "SERVO2_STANDALONE_ENABLED", "SERVO3_STANDALONE_ENABLED", "RESTART_AFTER_LOAD"):
                                if value_str.lower() not in ('true', 'false'): raise ValueError("must be True or False")
                                validated_settings[key] = value_str.lower() == 'true'
                            elif key in ("ROTATION_CYCLE_INTERVAL_MINUTES", "SERVO2_INTERVAL_SEC", "SERVO3_INTERVAL_SEC"):
                                v = int(value_str);
                                if v <= 0: raise ValueError("must be positive")
                                validated_settings[key] = v
                            elif key == "STILLS_IMAGING_INTERVAL_SEC":
                                v = float(value_str)
                                if v <= 0:
                                    raise ValueError("must be > 0")
                                validated_settings[key] = v
                            elif key == "ROTATION_CAMERA_SERVO":
                                v = int(value_str)
                                if v not in (2, 3):
                                    raise ValueError("ROTATION_CAMERA_SERVO must be 2 or 3")
                                validated_settings[key] = v
                            elif key == "CAMERA_TRIGGER_HOLD_MS":
                                v = int(value_str)
                                if v <= 0:
                                    raise ValueError("must be > 0")
                                validated_settings[key] = v
                            elif key == "ROTATION_INCREMENT_DEGREES":
                                v = float(value_str)
                                if v <= 0:
                                    raise ValueError("must be > 0")
                                validated_settings[key] = v
                            elif key == "ROTATION_STEP_INTERVAL_MS":
                                v = int(value_str)
                                if v <= 0:
                                    raise ValueError("must be > 0")
                                validated_settings[key] = v
                            elif key == "ROTATION_SPEED_PRESET":
                                preset = value_str.strip('"').lower()
                                if preset in ROTATION_SPEED_PRESET_TABLE:
                                    validated_settings[key] = preset
                                else:
                                    raise ValueError("invalid ROTATION_SPEED_PRESET")
                            elif key == "IMAGES_PER_ROTATION":
                                v = int(value_str)
                                if v < 2 or v > 360:
                                    raise ValueError("IMAGES_PER_ROTATION must be 2-360")
                                validated_settings[key] = v
                            elif key == "DEGREES_PER_IMAGE":
                                v = float(value_str)
                                if v <= 0 or v > 180:
                                    raise ValueError("DEGREES_PER_IMAGE must be >0 and <=180")
                                # Don't set directly; will be computed from IMAGES_PER_ROTATION
                            elif key == "PROGRAM_ENABLED":
                                validated_settings[key] = value_str.lower() == 'true'
                            elif key == "PROGRAM_REPEATS":
                                validated_settings[key] = int(value_str)
                            elif key == "PROGRAM_STEPS":
                                import ujson as json
                                validated_settings[key] = json.loads(value_str)    
                            elif key == "CUSTOM_SUN_R":
                                v = int(value_str)
                                validated_settings[key] = clamp(v)
                            elif key == "CUSTOM_SUN_G":
                                v = int(value_str)
                                validated_settings[key] = clamp(v)
                            elif key == "CUSTOM_SUN_B":
                                v = int(value_str)
                                validated_settings[key] = clamp(v)
                            elif key == "IMAGE_AT_NIGHT":
                                if value_str.lower() not in ('true', 'false'):
                                    raise ValueError("IMAGE_AT_NIGHT must be True or False")
                                validated_settings[key] = value_str.lower() == 'true'
                            elif key == "ROTATION_AT_NIGHT":
                                if value_str.lower() not in ('true', 'false'):
                                    raise ValueError("ROTATION_AT_NIGHT must be True or False")
                                validated_settings[key] = value_str.lower() == 'true'
                except Exception as e:
                    print(f"[SERIAL CMD] Load cancelled. Error in '{filename}': {e}")
                    return

                print(f"[SERIAL CMD] Profile '{filename}' validated. Applying settings...")
                g = globals()
                for key, value in validated_settings.items():
                    g[key] = value
                if "CUSTOM_SUN_R" in validated_settings:
                    CUSTOM_SUN_R = validated_settings["CUSTOM_SUN_R"]
                if "CUSTOM_SUN_G" in validated_settings:
                    CUSTOM_SUN_G = validated_settings["CUSTOM_SUN_G"]
                if "CUSTOM_SUN_B" in validated_settings:
                    CUSTOM_SUN_B = validated_settings["CUSTOM_SUN_B"]
                if "PROGRAM_STEPS" in validated_settings:
                    PROGRAM_STEPS = validated_settings["PROGRAM_STEPS"]
                if "PROGRAM_REPEATS" in validated_settings:
                    PROGRAM_REPEATS = validated_settings["PROGRAM_REPEATS"]
                if "PROGRAM_ENABLED" in validated_settings:
                    PROGRAM_ENABLED = validated_settings["PROGRAM_ENABLED"]
                if "IMAGE_AT_NIGHT" in validated_settings:
                    IMAGE_AT_NIGHT = validated_settings["IMAGE_AT_NIGHT"]
                if "ROTATION_AT_NIGHT" in validated_settings:
                    ROTATION_AT_NIGHT = validated_settings["ROTATION_AT_NIGHT"]
                if "ROTATION_CAMERA_SERVO" in validated_settings:
                    ROTATION_CAMERA_SERVO = validated_settings["ROTATION_CAMERA_SERVO"]
                update_rotation_parameters()
                print("[SERIAL CMD] Settings applied.")
                
                # Track the loaded profile name
                global LOADED_PROFILE_NAME
                LOADED_PROFILE_NAME = filename

                if RESTART_AFTER_LOAD:
                    print("[SERIAL CMD] Restarting simulation logic...")
                    init_solar_day()
                    start_real_time_ms = ticks_ms()
                    print("[SERIAL CMD] Simulation restarted. Time anchor reset.")
                else:
                    print("[SERIAL CMD] RESTART_AFTER_LOAD is False. Manual restart may be needed.")

            else:
                print("[SERIAL CMD] Usage: loadprofile <profilename>")

        elif command == "status":
            print("--- System Status ---")
            
            # Calculate current time for display
            now_ms = ticks_ms()
            _, time_of_day_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)
            sim_hour = int(time_of_day_minutes // 60) % 24
            sim_minute = int(time_of_day_minutes % 60)

            print("\x1b[1m-- Simulation & Time --\x1b[0m")
            print(f"  (Re)Start Time: \x1b[1m{START_TIME_HHMM:04d}\x1b[0m")
            print(f"  Sim Time: \x1b[1m{sim_hour:02d}:{sim_minute:02d}\x1b[0m")
            print(f"  Time Scale: \x1b[1m{TIME_SCALE}x\x1b[0m")
            # Human readable speed descriptor (mirrors JSON 'speed')
            try:
                speed_name = get_speed_name(TIME_SCALE)
            except Exception:
                speed_name = "Unknown"
            print(f"  Speed Name: \x1b[1m{speed_name}\x1b[0m")
            print(f"  Program Enabled: \x1b[1m{PROGRAM_ENABLED}\x1b[0m")
            print(f"  Restart After Profile Load: \x1b[1m{RESTART_AFTER_LOAD}\x1b[0m")
            print(f"  Auto-Load Latest Profile: \x1b[1m{AUTO_LOAD_LATEST_PROFILE}\x1b[0m")
            print(f"  Loaded Profile: \x1b[1m{LOADED_PROFILE_NAME if LOADED_PROFILE_NAME else '(none - using defaults)'}\x1b[0m")
            print("\n\x1b[1m-- Environment & Sun --\x1b[0m")
            print(f"  Solar Mode: \x1b[1m{SOLAR_MODE}\x1b[0m")
            print(f"  Intensity Scale: \x1b[1m{INTENSITY_SCALE}\x1b[0m")
            print(f"  Sun Color Mode: \x1b[1m{SUN_COLOR_MODE}\x1b[0m")
            print(f"  Dual Sun Enabled: \x1b[1m{DUAL_SUN_ENABLED}\x1b[0m")
            if SUN_COLOR_MODE == "CUSTOM":
                print(f"  Custom Sun RGB: \x1b[1m({CUSTOM_SUN_R}, {CUSTOM_SUN_G}, {CUSTOM_SUN_B})\x1b[0m")
            #print(f"  Date (for SCI): \x1b[1m{SIMULATION_DATE}\x1b[0m")
            #print(f"  Latitude (for SCI): \x1b[1m{LATITUDE}\x1b[0m")
            print("\n\x1b[1m-- Hardware & Imaging --\x1b[0m")
            print(f"  Servo 2 Standalone: \x1b[1m{SERVO2_STANDALONE_ENABLED}\x1b[0m")
            print(f"  Servo 2 Interval: \x1b[1m{SERVO2_INTERVAL_SEC}s\x1b[0m")
            print(f"  Servo 3 Standalone: \x1b[1m{SERVO3_STANDALONE_ENABLED}\x1b[0m")
            print(f"  Servo 3 Interval: \x1b[1m{SERVO3_INTERVAL_SEC}s\x1b[0m")
            print("-- -- -- -- -- -- -- --")          
            print(f"  Rotation Enabled: \x1b[1m{ROTATION_ENABLED}\x1b[0m")
            print(f"  Rotation Imaging Servo: \x1b[1m{ROTATION_CAMERA_SERVO}\x1b[0m")
            print(f"  Rotation Interval: \x1b[1m{ROTATION_CYCLE_INTERVAL_MINUTES} sim min\x1b[0m")
            print(f"  Images per Rotation: \x1b[1m{IMAGES_PER_ROTATION}\x1b[0m")
            print(f"  Degrees per Image: \x1b[1m{DEGREES_PER_IMAGE:.2f}°\x1b[0m")
            print(f"  Image at Night: \x1b[1m{IMAGE_AT_NIGHT}\x1b[0m")
            print(f"  Rotation at Night: \x1b[1m{ROTATION_AT_NIGHT}\x1b[0m")
            print(f"  Rotation Speed Preset: \x1b[1m{ROTATION_SPEED_PRESET}\x1b[0m ({ROTATION_SPEED_PRESET_TABLE[ROTATION_SPEED_PRESET]}s/360deg)")
            print(f"  Rotation Imaging Mode: \x1b[1m{ROTATION_CAPTURE_MODE}\x1b[0m")
            print(f"  Camera Lighting Panels: \x1b[1m{CAMERA_LIGHTING_PANELS}\x1b[0m")
            print(f"  Camera Light RGB: \x1b[1m({CAMERA_LIGHT_R}, {CAMERA_LIGHT_G}, {CAMERA_LIGHT_B})\x1b[0m")
            print(f"  Rotation Light RGB: \x1b[1m({ROTATION_LIGHT_R}, {ROTATION_LIGHT_G}, {ROTATION_LIGHT_B})\x1b[0m")
            print(f"  1:1 Servo-to-sample rotation ratio: \x1b[1m{SERVO_1TO1_RATIO}\x1b[0m")
            print(f"  Rotation Trigger Hold: \x1b[1m{CAMERA_TRIGGER_HOLD_MS} ms\x1b[0m")
            print("-----------------------")
            
            # Program Steps
            if PROGRAM_ENABLED:
                print("\n\x1b[1m-- Program Configuration --\x1b[0m")
                print(f"  Program Repeats: \x1b[1m{PROGRAM_REPEATS}\x1b[0m")
                print(f"  Number of Steps: \x1b[1m{len(PROGRAM_STEPS)}\x1b[0m")
                if PROGRAM_STEPS:
                    import ujson as json
                    print(f"  Program Steps: \x1b[1m{json.dumps(PROGRAM_STEPS)}\x1b[0m")
            else:
                print("\n\x1b[1m-- Program Configuration --\x1b[0m")
                print(f"  Program Repeats: \x1b[1m{PROGRAM_REPEATS}\x1b[0m")
                print("  Program Steps: \x1b[1m(none - program disabled)\x1b[0m")
            print("-----------------------")

        elif command == "fillpanel" and (len(parts) == 4 or len(parts) == 5):
            try:
                r = int(parts[1])
                g = int(parts[2])
                b = int(parts[3])
                duration = int(parts[4]) if len(parts) == 5 else 30
                fill_panel(r, g, b, duration)
                print(f"[SERIAL CMD] Panel filled with RGB({r},{g},{b}) for {duration}s")
            except Exception as e:
                print(f"[SERIAL CMD] Error: {e}")
            return

        elif command == "light" and len(parts) == 3:
            target = parts[1]
            state = parts[2]
            if target == "camera":
                if state == "on":
                    camera_lighting_active = True
                    apply_camera_lighting()
                    print("[SERIAL CMD] Camera lighting turned ON.")
                elif state == "off":
                    camera_lighting_active = False
                    deactivate_camera_lighting()
                    print("[SERIAL CMD] Camera lighting turned OFF.")
                else:
                    print("[SERIAL CMD] Error: Use 'on' or 'off'.")
            elif target == "rotation":
                if state == "on":
                    rotation_lighting_active = True
                    apply_rotation_lighting()
                    print("[SERIAL CMD] Rotation lighting turned ON.")
                elif state == "off":
                    rotation_lighting_active = False
                    deactivate_rotation_lighting()
                    print("[SERIAL CMD] Rotation lighting turned OFF.")
                else:
                    print("[SERIAL CMD] Error: Use 'on' or 'off'.")
            else:
                print("[SERIAL CMD] Error: Unknown light target. Use 'camera' or 'rotation'.")
            return

        elif command == "listprofiles":
            try:
                files = os.listdir()
                profiles = [f for f in files if f.endswith(".txt")]
                if profiles:
                    print("[SERIAL CMD] Available profiles:")
                    for pf in profiles:
                        note = ""
                        try:
                            with open(pf, "r") as f:
                                first_line = f.readline()
                                if first_line.startswith("NOTE ="):
                                    note = first_line[len("NOTE ="):].strip()
                        except Exception:
                            pass
                        if note:
                            print(f"  {pf} - {note}")
                        else:
                            print(f"  {pf}")
                else:
                    print("[SERIAL CMD] No profile files found.")
            except Exception as e:
                print(f"[SERIAL CMD] Error listing profiles: {e}")
            return

        elif command == "profiledelete":
            if len(parts) < 2:
                print("[SERIAL CMD] Usage: profiledelete <filename>")
                return
            filename = parts[1]
            # Add .txt extension if not present
            if not filename.endswith(".txt"):
                filename += ".txt"
            try:
                # Check if file exists
                files = os.listdir()
                if filename not in files:
                    print(f"[SERIAL CMD] Error: Profile '{filename}' not found.")
                    return
                # Delete the file
                os.remove(filename)
                print(f"[SERIAL CMD] Profile '{filename}' deleted successfully.")
            except Exception as e:
                print(f"[SERIAL CMD] Error deleting profile: {e}")
            return

        elif command == "restart":
            print("[SERIAL CMD] Restarting simulation logic...")
            init_solar_day()
            start_real_time_ms = ticks_ms()
            print("[SERIAL CMD] Simulation restarted. Time anchor reset.")
            return
        
        elif command == "reset":
            print("[SERIAL CMD] Performing hard reset of RP2040 board...")
            sleep_ms(100)  # Brief delay to ensure message is transmitted
            machine.reset()  # Hard reset the microcontroller
            return

        elif command == "help" and len(parts) > 1 and parts[1] == "all":
            print("--- Command Summary ---")
            print("Set: time <hhmm>, autoload <on|off|true|false|1|0>, cameralightingpanels <ALL|MIDDLE5|MIDDLE3|OUTER2|OUTER4>, cameralightrgb <r> <g> <b>, date <yyyymmdd>, degrees_per_image <float>, images_per_rotation <num>, imageatnight <true|false|on|off|1|0>, intensity <0.0-1.0>, latitude <degrees>, programenabled <on|off>, programrepeats <n>, rotationatnight <true|false|on|off|1|0>, rotationcameraservo <2|3>, rotationinterval <minutes>, rotationlightrgb <r> <g> <b>, rotationmode <stills|video>, rot_inc_deg <float>, rot_speed <slow|medium|fast>, rot_step_intv <int>, rot_stills_intv <float>, rot_trig_hold <int>, savelog <yyyymmdd>, servo2interval <seconds>, servo3interval <seconds>, solarmode <basic|scientific>, speed <scale>, starttime <hhmm>, suncolor <natural|blue|custom> [r g b]")
            print("Toggle: dualsun, program, rotation, restartafterload, servo2, servo3, 1to1ratio")
            print("Program/Manual: jump nextstep, jump step <n>, listprofiles, loadprofile <profilename>, saveprofile <profilename> [note], profiledelete <profilename>, savelog <yyyymmdd>, status, trigger servo2, trigger servo3, trigger rotation")
            print("Utility: fillpanel <r> <g> <b> [duration], light camera <on|off>, light rotation <on|off>, reset, restart, help all")
            print("-----------------------")

        else:
            print(f"[SERIAL CMD] Error: Unknown command '{command_str}'")
            
    except (ValueError, IndexError) as e:
        print(f"[SERIAL CMD] Error processing command '{command_str}': {e}")

def safe_print(message):
    """Print a message and flush the output buffer to ensure transmission."""
    print(message)
    try:
        import sys
        sys.stdout.flush()
    except Exception:
        pass
    # Small delay to ensure transmission completes
    from time import sleep_ms
    sleep_ms(10)

def process_serial_input():
    """Checks for and processes incoming serial commands without blocking."""
    global serial_command_buffer
    # Check if there's anything to read on stdin. The '0' timeout makes it non-blocking.
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        char = sys.stdin.read(1)
        if char in ('\n', '\r'):
            if serial_command_buffer:
                handle_command(serial_command_buffer)
                serial_command_buffer = "" # Reset buffer
        elif char is not None:
            serial_command_buffer += char

def get_speed_name(scale):
    """Human-readable description (supports negative for reverse)."""
    if scale == 0:
        return "HOLD"
    reverse = scale < 0
    mag = abs(scale)
    if mag == 1:
        base = "Real Time"
    elif mag == 6:
        base = "6x Speed"
    elif mag == 60:
        base = "1 Min/Sec"
    elif mag == 600:
        base = "10 Min/Sec"
    else:
        base = "Custom"
    return f"Reverse {base}" if reverse else base
    
def shutdown_hardware():
    """Turn off NeoPixels, matrix display, and deinit servos."""
    fill_panel(0, 0, 0)  # Turn off NeoPixels
    # Turn off matrix display
    for c_pin in matrix_display_columns:
        c_pin.low()
    for r_pin in matrix_display_rows:
        r_pin.high()
    # Clean up servos
    for pwm in (servo_pwm_1, servo_pwm_2, servo_pwm_3):
        if pwm:
            pwm.deinit()


frozen_sim_time_minutes = 0  # Stores the frozen time when in HOLD mode
frozen_abs_sim_time = 0  # Stores the frozen absolute simulation time when entering HOLD mode
# Flag to ensure frozen_sim_time_minutes is only initialized at true startup
frozen_time_initialized = False

# Unified re-anchor helper to maintain continuity across speed / direction changes
def _reanchor_start_time(preserved_minutes, new_scale, now_ms, start_time_hhmm, current_start_real_ms):
    """Return adjusted start_real_time_ms so preserved_minutes stays visible.
    preserved_minutes: target simulation clock minute (0-1439)
    new_scale: new TIME_SCALE (non-zero for running)
    now_ms: current ticks_ms()
    start_time_hhmm: START_TIME_HHMM anchor
    current_start_real_ms: existing anchor (used when entering HOLD or error fallback)
    """
    if new_scale == 0:
        return current_start_real_ms
    start_minutes = (start_time_hhmm // 100) * 60 + (start_time_hhmm % 100)
    if new_scale > 0:
        minutes_since_start = (preserved_minutes - start_minutes) % 1440
    else:
        minutes_since_start = (start_minutes - preserved_minutes) % 1440
    denom = max(0.0001, abs(new_scale))
    return now_ms - int((minutes_since_start * 60000) / denom)

def run_simulation():
    """Main loop for the solar simulation."""
    global TIME_SCALE, start_real_time_ms, SOLAR_MODE
    global frozen_sim_time_minutes, frozen_abs_sim_time
    global last_rotation_absolute_time, rotation_in_progress, current_rotation_angle
    global servo2_controlled_by_rotation
    global manual_panel_override_active, manual_panel_override_until_ms
    global button_a_pressed_last, button_a_long_press_detected
    global button_b_pressed_last, button_b_long_press_detected, camera_light_hold_until_ms

    # If starting in HOLD mode (TIME_SCALE == 0), initialize frozen time to START_TIME_HHMM only once at true startup
    global frozen_time_initialized
    if TIME_SCALE == 0 and not frozen_time_initialized:
        start_hour = START_TIME_HHMM // 100
        start_minute = START_TIME_HHMM % 100
        frozen_sim_time_minutes = start_hour * 60 + start_minute
        frozen_abs_sim_time = 0  # No simulated time has elapsed yet relative to START_TIME_HHMM
        frozen_time_initialized = True
    # Initialize the simulated solar day
    init_solar_day()
    
    # Initialize timekeeping
    start_real_time_ms = ticks_ms()
    last_update_time_ms = start_real_time_ms
    display_update_interval_ms = 1000  # Update the display 1 time per second
    last_printed_minute = -1  # Initialize to -1 to ensure first minute prints

    # Button state tracking for edge detection (debounce)
    button_b_pressed_last = False
    button_a_pressed_last = False
    
    # --- Updated display state machine variables ---
    display_state = 'HOUR_TENS'  # Start with hour tens digit
    last_display_change_ms = 0
    
    # Adjust time variables for better stability
    last_pov_refresh_ms = ticks_ms()
    pov_refresh_interval_ms = 3  # Aim for stable >200Hz refresh rate
    
    # Button long press detection variables
    button_a_press_start = 0
    button_a_long_press_detected = False
    button_b_press_start = 0
    button_b_long_press_detected = False

    # Main loop
    while True:
        now_ms = ticks_ms()
        # Calculate the current simulation time
        elapsed_sim_time, time_of_day_minutes = get_sim_time(START_TIME_HHMM, ticks_diff(now_ms, start_real_time_ms), TIME_SCALE)
        abs_sim_time = elapsed_sim_time

        # --- PROGRAM ACTIVATION AND STATE UPDATE ---
        # Activate program when sim time reaches first step
        if PROGRAM_ENABLED and not program_running and not program_has_completed_all_repeats and TIME_SCALE > 0:
            sim_hour_check = int(time_of_day_minutes // 60)
            sim_minute_check = int(time_of_day_minutes % 60)
            current_sim_hhmm_check = (sim_hour_check * 100) + sim_minute_check
            if len(PROGRAM_STEPS) > 0 and current_sim_hhmm_check >= PROGRAM_STEPS[0].get("sim_time_hhmm", 9999):
                start_program()
                print(f"[PROGRAM] First program step activated at sim time {sim_hour_check:02d}:{sim_minute_check:02d}")

        # If program is running, update its state
        if program_running:
            update_program_state(now_ms, time_of_day_minutes)


        # Time printing code
        if TIME_SCALE == 0:  # If in HOLD mode, use frozen time directly
            total_minutes = int(frozen_sim_time_minutes)
            debug_source = "frozen_sim_time_minutes (HOLD)"
        else:
            total_minutes = int(time_of_day_minutes)
            debug_source = "time_of_day_minutes (RUN)"

        current_hour = int(total_minutes // 60) % 24
        current_minute = int(total_minutes % 60)

        # Check for time change OR time scale change
        if total_minutes != last_printed_minute:
            print(f"Simulation time: \x1b[1m{current_hour:02d}:{current_minute:02d}\x1b[0m (Speed: {TIME_SCALE}x)")
            last_printed_minute = total_minutes
        
        # Perform POV refresh at regular intervals
        if ticks_diff(now_ms, last_pov_refresh_ms) >= pov_refresh_interval_ms:
            refresh_pov_matrix_display()
            last_pov_refresh_ms = ticks_ms()  # Use updated time for accuracy
        
        # Check if it's time to update the display content
        if ticks_diff(now_ms, last_update_time_ms) >= display_update_interval_ms:
            # Auto-disable manual panel override after timeout
            if manual_panel_override_active and ticks_ms() > manual_panel_override_until_ms:
                manual_panel_override_active = False
                print("[INFO] fillpanel override ended, resuming normal display.")

            # Only update sun display if no special lighting is active
            if not camera_lighting_active and not rotation_lighting_active and not manual_panel_override_active:
                # Update sun display using the new flicker-free method
                update_sun_display(time_of_day_minutes)
    
            # Get current time digits
            hour_tens_char, hour_ones_char, minute_tens_char, minute_ones_char = time_to_display_chars(time_of_day_minutes)
            
            # Calculate time elapsed since last display state change
            display_elapsed_ms = ticks_diff(now_ms, last_display_change_ms)
            
            # Determine the duration for the CURRENT state
            current_duration = DIGIT_DISPLAY_DURATION_MS  # Default 1 second for digits
            if display_state == 'PAUSE':
                current_duration = DISPLAY_PAUSE_DURATION_MS  # 5 seconds for pause
            
            # Check if it's time to change the display state
            if display_elapsed_ms >= current_duration:
                # We need to transition to the next state
                if display_state == 'HOUR_TENS':
                    display_state = 'HOUR_ONES'
                    update_display_character(hour_ones_char)
                    
                elif display_state == 'HOUR_ONES':
                    display_state = 'COLON'
                    update_display_character(':')
                    
                elif display_state == 'COLON':
                    display_state = 'MINUTE_TENS'
                    update_display_character(minute_tens_char)
                    
                elif display_state == 'MINUTE_TENS':
                    display_state = 'MINUTE_ONES'
                    update_display_character(minute_ones_char)
                    
                elif display_state == 'MINUTE_ONES':
                    display_state = 'PAUSE'
                    # Explicit buffer clearing for PAUSE state
                    for r_idx in range(5):
                        for c_idx in range(1, 4):  # Clear columns 1-3 (character area)
                            matrix_buffer[r_idx][c_idx] = 0
                  # Pause state - keep column 0 (speed indicator) intact
                elif display_state == 'PAUSE':
                    display_state = 'HOUR_TENS'
                    update_display_character(hour_tens_char)
            
                # Record when this state change happened
                last_display_change_ms = now_ms
            elif display_state == 'HOUR_TENS' and display_elapsed_ms == 0:
                # This is the initial state or we just entered this state
                update_display_character(hour_tens_char)
        
            # Always ensure indicators are properly displayed
            update_speed_indicator(TIME_SCALE)
            update_mode_indicator(SOLAR_MODE)
            update_hold_indicator(now_ms, TIME_SCALE == 0)  # Add this line
            
            last_update_time_ms = now_ms
        
        # Update the 360° imaging rotation cycle (servos operate independently now)
        update_rotation_cycle(now_ms, abs_sim_time, TIME_SCALE)
        
        # Update the standalone servo2 (camera trigger) at regular intervals
        update_standalone_servo2(now_ms)
        
        # Update the standalone servo3 (second camera trigger) at regular intervals
        update_standalone_servo3(now_ms)

        # Centralized check for camera lighting hold time
        if camera_light_hold_until_ms > 0 and now_ms >= camera_light_hold_until_ms:
            camera_light_hold_until_ms = 0
            deactivate_camera_lighting()

        # Check for incoming serial commands
        process_serial_input()

        # Check for Button A press (jump to solar noon)
        button_a_state = not button_a.value()  # Pulled up, so LOW means pressed

        # Track start of button press for long press detection
        if button_a_state and not button_a_pressed_last:
            button_a_press_start = now_ms

        # Check for long press (held for over 1 second)
        if button_a_state and button_a_pressed_last:
            if not button_a_long_press_detected and ticks_diff(now_ms, button_a_press_start) >= 1000:
                # Long press detected - Jump to solar noon
                # Use SOLAR_NOON_MINUTES if defined, otherwise use default 720 (12:00)
                solar_noon_minutes = SOLAR_NOON_MINUTES if 'SOLAR_NOON_MINUTES' in globals() else 720
                
                if TIME_SCALE == 0:
                    # In HOLD mode, just update the frozen time to noon without any division
                    frozen_sim_time_minutes = solar_noon_minutes
                    print(f"Button A long press: HOLD mode - frozen time set to solar noon ({solar_noon_minutes//60:02}:{solar_noon_minutes%60:02})")
                elif TIME_SCALE > 0:  # Explicitly check to prevent divide-by-zero
                        # Jump simulation time to solar noon
                    start_time_minutes = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
                    minutes_diff = solar_noon_minutes - start_time_minutes
                    if minutes_diff < 0:
                        minutes_diff += 1440  # Add a day if needed
                    start_real_time_ms = now_ms - int((minutes_diff * 60000) / TIME_SCALE)

                print(f"Button A long press: Simulation time set to solar noon ({solar_noon_minutes//60:02}:{solar_noon_minutes%60:02})")
                
                # Force immediate display update
                last_update_time_ms = 0
                button_a_long_press_detected = True

        # Handle button A release (for short press)
        elif not button_a_state and button_a_pressed_last:
            if not button_a_long_press_detected:
                # Short press detected - Toggle solar mode
                if SOLAR_MODE == "BASIC":
                    SOLAR_MODE = "SCIENTIFIC"
                else:  # SCIENTIFIC
                    SOLAR_MODE = "BASIC"
                
                print(f"Button A short press: Solar mode changed to \x1b[1m{SOLAR_MODE}\x1b[0m")

                # Re-initialize the solar day with the new mode
                init_solar_day()
                
                # Force immediate display update
                last_update_time_ms = 0
    
            # Reset long press detection
            button_a_long_press_detected = False

        button_a_pressed_last = button_a_state
            
        # Check for Button B press
        button_b_state = not button_b.value()  # Pulled up, so LOW means pressed

        # Track start of button B press for long press detection
        if button_b_state and not button_b_pressed_last:
            button_b_press_start = now_ms

        # Check for long press (held for over 1 second)
        if button_b_state and button_b_pressed_last:
            if not button_b_long_press_detected and ticks_diff(now_ms, button_b_press_start) >= 1000:
                # Long press detected - Jump to start time
                start_time_minutes = (START_TIME_HHMM // 100) * 60 + (START_TIME_HHMM % 100)
                
                if TIME_SCALE == 0:
                    # In HOLD mode, just update the frozen time to start time
                    frozen_sim_time_minutes = start_time_minutes
                    print(f"Button B long press: HOLD mode - frozen time set to start time ({start_time_minutes//60:02d}:{start_time_minutes%60:02d})")
                elif TIME_SCALE > 0:
                    # Jump simulation time to start time by resetting start_real_time_ms
                    start_real_time_ms = now_ms
                    print(f"Button B long press: Simulation time reset to start time ({start_time_minutes//60:02d}:{start_time_minutes%60:02d})")
                
                # Force immediate display update
                last_update_time_ms = 0
                button_b_long_press_detected = True

        # Handle button B release (for short press)
        elif not button_b_state and button_b_pressed_last:
            if not button_b_long_press_detected:
                # This is a short press - do the existing button B behavior
                if not rotation_in_progress:
                    # Get current real time
                    now_ms = ticks_ms()
                    
                    # Calculate elapsed REAL time since simulation start
                    elapsed_real_ms = ticks_diff(now_ms, start_real_time_ms)
                    
                    # Calculate current SIMULATION time (in milliseconds)
                    sim_elapsed_ms = elapsed_real_ms * TIME_SCALE
                    
                    # Store old scale before changing
                    old_time_scale = TIME_SCALE
                    
                    # Change the time scale (simulation speed)
                    if TIME_SCALE == 0:  # HOLD mode
                        TIME_SCALE = 1
                    elif TIME_SCALE == 1:
                        TIME_SCALE = CUSTOM_TIME_SCALE
                    elif TIME_SCALE == CUSTOM_TIME_SCALE:
                        TIME_SCALE = 6
                    elif TIME_SCALE == 6:
                        TIME_SCALE = 60
                    elif TIME_SCALE == 60:
                        TIME_SCALE = 600
                    else:
                        # Add this code to capture current time when entering HOLD mode
                        frozen_sim_time_minutes = time_of_day_minutes
                        frozen_abs_sim_time = abs_sim_time
                        print(f"Time frozen at: {frozen_sim_time_minutes//60:02d}:{frozen_sim_time_minutes%60:02d}")
                        TIME_SCALE = 0  # HOLD mode (0X)

                    # When exiting HOLD mode, define start_time_minutes first
                    if old_time_scale == 0 and TIME_SCALE > 0:
                        # Define start_time_minutes before using it
                        start_hour = START_TIME_HHMM // 100
                        start_minute = START_TIME_HHMM % 100
                        start_time_minutes = start_hour * 60 + start_minute
                        
                        # Calculate what start_real_time_ms should be to continue from frozen time
                        minutes_diff = frozen_sim_time_minutes - start_time_minutes
                        if minutes_diff < 0:
                            minutes_diff += 1440  # Add a day if needed
                        start_real_time_ms = now_ms - int((minutes_diff * 60000) / TIME_SCALE)
                        
                        # Calculate what the last rotation time would have been
                        # Find the most recent interval before the frozen time
                        global last_rotation_absolute_time
                        intervals_elapsed = frozen_abs_sim_time // ROTATION_CYCLE_INTERVAL_MINUTES
                        last_rotation_absolute_time = intervals_elapsed * ROTATION_CYCLE_INTERVAL_MINUTES
                        print(f"Last rotation would have been at {last_rotation_absolute_time} minutes")
                    else:
                        # Normal speed change (not exiting HOLD mode)
                        if TIME_SCALE > 0:  # Skip the calculation when entering HOLD mode
                            start_real_time_ms = now_ms - int(sim_elapsed_ms / TIME_SCALE)
                    
                    # Update speed indicator
                    update_speed_indicator(TIME_SCALE)
                    
                    speed_name = "HOLD" if TIME_SCALE == 0 else get_speed_name(TIME_SCALE)
                    print(f"Time Scale: {TIME_SCALE}x ({speed_name})")

            # Reset long press detection on button release
            button_b_long_press_detected = False
            
        button_b_pressed_last = button_b_state

        # IMPORTANT: Refresh the LED matrix display on every loop iteration
        # This is critical for POV effect - must be called frequently for stability and brightness
        refresh_pov_matrix_display()
# Print memory info at startup
# Insert helper above startup sequence
# ===== Auto-Load Latest Profile (tidy placement) =====
def _find_latest_profile(prefix=AUTO_LOAD_PROFILE_PREFIX):
    """Return (base_without_ext, full_filename) for newest timestamped profile or (None,None).
    Pattern: YYYYMMDD_HHMM_* where * contains prefix (e.g. profile_). Chronological via lexicographic sort."""
    try:
        files = [f for f in os.listdir() if f.endswith('.txt') and prefix in f]
        candidates = []
        for f in files:
            if len(f) >= 17 and f[0:8].isdigit() and f[8]=='_' and f[9:13].isdigit():
                candidates.append(f)
        if not candidates:
            return (None, None)
        latest = sorted(candidates)[-1]
        base = latest[:-4] if latest.lower().endswith('.txt') else latest
        return (base, latest)
    except Exception as e:
        print(f"[AUTOLOAD] Error scanning profiles: {e}")
        return (None, None)

def _attempt_autoload():
    global LOADED_PROFILE_NAME
    if not AUTO_LOAD_LATEST_PROFILE:
        return
    base, full = _find_latest_profile()
    if not full:
        print("[AUTOLOAD] No matching profile files found; using embedded defaults.")
        LOADED_PROFILE_NAME = None  # Explicitly mark as no profile loaded
        return
    try:
        print(f"[AUTOLOAD] Loading latest profile '{full}'...")
        handle_command(f"loadprofile {base}")
        # Note: LOADED_PROFILE_NAME is set by the loadprofile command handler
    except Exception as e:
        print(f"[AUTOLOAD] Failed to auto-load '{full}': {e}")
        LOADED_PROFILE_NAME = None  # Mark as no profile if load failed

# ===== Startup Sequence =====
gc.collect()
free_mem = gc.mem_free(); alloc_mem = gc.mem_alloc(); total_mem = free_mem + alloc_mem
print(f"Memory utilization: {alloc_mem/total_mem*100:.1f}%")
# Load persisted autoload preference (if present) BEFORE attempting autoload
def _load_autoload_pref():
    global AUTO_LOAD_LATEST_PROFILE
    try:
        with open('autoload.cfg','r') as f:
            val = f.read().strip()
            if val in ('0','1'):
                AUTO_LOAD_LATEST_PROFILE = (val=='1')
                print(f"[AUTOLOAD] Persisted preference loaded: {AUTO_LOAD_LATEST_PROFILE}")
    except OSError:
        # No file yet – first run, keep default
        pass
    except Exception as e:
        print(f"[AUTOLOAD] Error reading autoload.cfg: {e}")

_load_autoload_pref()
_attempt_autoload()
print("Solar Simulator Starting!      ****   Type \"help\" for available commands.   ****")
sleep_ms(500)

try:
    run_simulation()
except KeyboardInterrupt:
    print("Simulation stopped by user.")
    shutdown_hardware()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.print_exception(e)
    fill_panel(0,0,0)
    shutdown_hardware()