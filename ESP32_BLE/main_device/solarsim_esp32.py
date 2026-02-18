"""
Solar Simulator for ESP32-S3
=============================
Modular port from RP2040 to ESP32-S3 with BLE control

Uses hardware abstraction layer and display manager for clean separation
"""

import gc
import math
import time
from machine import Pin
from lib import HardwareESP32, DisplayManager
from ble_server import BLEServer

# ============================================================================
# I. CORE SIMULATION PARAMETERS
# ============================================================================

# Time Configuration
START_TIME_HHMM = 600          # Start at 6:00 AM
TIME_SCALE = 1                  # Time scaling factor (1, 6, 60, 600, or 0 for HOLD)
SIMULATION_DATE = 20260130      # Date in YYYYMMDD format

# Program configuration
PROGRAM_ENABLED = False        # Master switch for program functionality
PROGRAM_STEPS = [              # Non-program default: neutral single step
    {"sim_time_hhmm": 1200, "speed": 1, "intensity_scale": 1.0, "dual_sun": False}
]
PROGRAM_REPEATS = -1                   # -1 for indefinite repeats, 0 or 1 for single run, or N for N repeats
STOP_SIMULATION_AFTER_PROGRAM = False  # When True, terminates simulation after program completes
AUTO_LOAD_LATEST_PROFILE = True    # Default: attempt to load most recent profile_*.txt

# Solar Simulation Mode
SOLAR_MODE = "BASIC"            # "BASIC" or "SCIENTIFIC"
SUN_COLOR_MODE = "NATURAL"      # "NATURAL", "BLUE", or "CUSTOM"
MAX_BRIGHTNESS = 255            # Maximum brightness (0-255)
INTENSITY_SCALE = 1.0           # Global intensity multiplier
DUAL_SUN_ENABLED = False        # Set to True to enable a mirrored second sun
CUSTOM_SUN_R = 255; CUSTOM_SUN_G = 255; CUSTOM_SUN_B = 0

# Location Parameters (for SCIENTIFIC mode)
LATITUDE = 0                    # Latitude in degrees
LONGITUDE = 0                   # Longitude in degrees
SOLAR_NOON_MINUTES = 12 * 60    # Solar noon time in minutes

# Rotation Configuration
ROTATION_ENABLED = False        # Flag to enable/disable rotation cycle
ROTATION_AT_NIGHT = False       # Disable rotation during nighttime
ROTATION_INCREMENT_DEGREES = 15  # Degrees to rotate per step
ROTATION_SPEED_PRESET_TABLE = {
    "slow": 180.0,    # 180 seconds for 360°
    "medium": 60.0,   # 60 seconds for 360°
    "fast": 7.0       # 5 seconds for 360°
}
ROTATION_SPEED_PRESET = "fast"
ROTATION_CYCLE_INTERVAL_MINUTES = 3
ROTATION_CAMERA_ENABLED = True
ROTATION_CAMERA_SERVO = 2
ROTATION_CAPTURE_MODE = "STILLS"
IMAGES_PER_ROTATION = 8
DEGREES_PER_IMAGE = 360.0 / IMAGES_PER_ROTATION
ROTATION_STEP_INTERVAL_MS = 90
STILLS_IMAGING_INTERVAL_SEC = 13.5
CAMERA_TRIGGER_HOLD_MS = 1500
CAMERA_LIGHTING_ENABLED = True
CAMERA_LIGHTING_PANELS = "ALL"
CAMERA_LIGHT_R = 30; CAMERA_LIGHT_G = 30; CAMERA_LIGHT_B = 30
ROTATION_LIGHTING_ENABLED = True
ROTATION_LIGHT_R = 30; ROTATION_LIGHT_G = 30; ROTATION_LIGHT_B = 30
SERVO2_INTERVAL_DAY_SEC = 120
SERVO2_INTERVAL_NIGHT_SEC = 0
SERVO3_INTERVAL_DAY_SEC = 0
SERVO3_INTERVAL_NIGHT_SEC = 0
SERVO_1TO1_RATIO = False
RESTART_AFTER_LOAD = True

# ============================================================================
# II. SIMULATION STATE
# ============================================================================

# Global state variables
start_real_time_ms = 0
frozen_sim_time_minutes = 0
simulation_running = True

# Rotation/Servo State Re-added
rotation_state = 'IDLE'
last_rotation_absolute_time = 0
rotation_in_progress = False
current_rotation_angle = 0
manual_rotation_triggered = False

servo2_state = 'IDLE'
servo2_trigger_start_ms = 0
last_servo2_trigger_ms = 0
servo2_controlled_by_rotation = False
servo2_using_lighting = False

servo3_state = 'IDLE'
servo3_trigger_start_ms = 0
last_servo3_trigger_ms = 0
servo3_using_lighting = False

camera_lighting_active = False
rotation_lighting_active = False

# ============================================================================
# III. TIME MANAGEMENT
# ============================================================================

def get_sim_time_minutes(start_time_hhmm, start_real_ms, time_scale):
    """
    Calculate current simulation time in minutes
    
    Args:
        start_time_hhmm: Starting time as HHMM (e.g., 600 = 6:00 AM)
        start_real_ms: Real-time milliseconds when simulation started
        time_scale: Speed multiplier (0 = HOLD)
        
    Returns:
        int: Current simulation time in minutes since midnight
    """
    if time_scale == 0:
        # HOLD mode: return frozen time
        return frozen_sim_time_minutes
    
    # Calculate elapsed real time
    now_ms = time.ticks_ms()
    elapsed_real_ms = time.ticks_diff(now_ms, start_real_ms)
    
    # Scale elapsed time by time_scale
    elapsed_sim_ms = elapsed_real_ms * time_scale
    elapsed_sim_minutes = elapsed_sim_ms / (1000 * 60)
    
    # Convert start_time_hhmm to minutes
    start_minutes = (start_time_hhmm // 100) * 60 + (start_time_hhmm % 100)
    
    # Calculate current sim time (wrap at 24 hours)
    sim_minutes = int(start_minutes + elapsed_sim_minutes) % (24 * 60)
    
    return sim_minutes


def set_sim_time(new_time_hhmm):
    """Set simulation time to a specific value"""
    global start_real_time_ms, frozen_sim_time_minutes, START_TIME_HHMM
    
    new_minutes = (new_time_hhmm // 100) * 60 + (new_time_hhmm % 100)
    
    if TIME_SCALE == 0:
        # HOLD mode: just update frozen time
        frozen_sim_time_minutes = new_minutes
    else:
        # Running mode: re-anchor start time
        start_real_time_ms = time.ticks_ms()
        # Adjust START_TIME_HHMM to make current time equal to new_minutes
        # This is simplified - just restart from new time
        START_TIME_HHMM = new_time_hhmm


def set_time_scale(new_scale):
    """Change simulation speed"""
    global TIME_SCALE, start_real_time_ms, frozen_sim_time_minutes, START_TIME_HHMM
    
    if new_scale == TIME_SCALE:
        return  # No change
    
    # Preserve current simulation time
    current_sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
    
    if new_scale == 0:
        # Entering HOLD mode
        frozen_sim_time_minutes = current_sim_minutes
    elif TIME_SCALE == 0:
        # Exiting HOLD mode
        start_real_time_ms = time.ticks_ms()
        # Calculate new START_TIME_HHMM to preserve current time
        START_TIME_HHMM = (current_sim_minutes // 60) * 100 + (current_sim_minutes % 60)
    else:
        # Changing between running scales
        start_real_time_ms = time.ticks_ms()
        START_TIME_HHMM = (current_sim_minutes // 60) * 100 + (current_sim_minutes % 60)
    
    TIME_SCALE = new_scale


def time_to_string(minutes):
    """Convert minutes since midnight to HH:MM string"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"

def clamp(value, min_val=0, max_val=255):
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))

def _reanchor_start_time(known_sim_minutes, new_scale, now_ms, start_hhmm, current_start_real_ms):
    """
    Helper to calculate new start_real_time_ms when speed changes,
    ensuring continuity of simulation time.
    """
    start_hour = start_hhmm // 100
    start_minute = start_hhmm % 100
    start_minutes = start_hour * 60 + start_minute
    
    if new_scale == 0:
        return current_start_real_ms # Irrelevant for HOLD
        
    if new_scale > 0:
        elapsed_sim_minutes = (known_sim_minutes - start_minutes)
        # Handle wrapping if needed, though simple diff is usually enough for linear projection
        while elapsed_sim_minutes < 0: elapsed_sim_minutes += 1440
        
        # elapsed_sim_minutes = (elapsed_real_ms / 60000) * scale
        # elapsed_real_ms = (elapsed_sim_minutes * 60000) / scale
        new_elapsed_real_ms = (elapsed_sim_minutes * 60000) / new_scale
        return now_ms - int(new_elapsed_real_ms)
    else:
        # Backward time unsupported in this simple port for now, defaulting to forward
        return current_start_real_ms


# ============================================================================
# IV. SOLAR CALCULATIONS
# ============================================================================

def get_sun_position_basic(minute_of_day):
    """
    Basic sun position calculation (sine curve)
    
    Args:
        minute_of_day: Minutes since midnight (0-1439)
        
    Returns:
        tuple: (x_position, intensity) where x is 0-55, intensity is 0-100
    """
    # Sun rises at 6 AM (360 min), sets at 6 PM (1080 min)
    sunrise_min = 6 * 60
    sunset_min = 18 * 60
    
    if minute_of_day < sunrise_min or minute_of_day >= sunset_min:
        # Night time
        return (0, 0)
    
    # Calculate progress through the day (0.0 to 1.0)
    day_length = sunset_min - sunrise_min
    progress = (minute_of_day - sunrise_min) / day_length
    
    # X position: 0 at sunrise, 55 at sunset
    x_position = int(progress * 55)
    
    # Intensity: sine curve peaking at noon
    # sin(0) = 0 at sunrise, sin(π) = 0 at sunset, sin(π/2) = 1 at noon
    intensity_fraction = math.sin(progress * math.pi)
    intensity = int(intensity_fraction * 100 * INTENSITY_SCALE)
    
    return (x_position, intensity)


def get_sun_position_scientific(minute_of_day, day_of_year):
    """
    Scientific sun position with declination and equation of time
    Ported from v2
    """
    # Default values for nighttime
    x, y = -10, 4  # Off-screen
    size = 0
    r, g, b = 0, 0, 0
    
    # Calculate solar elevation angle
    elevation = calculate_solar_elevation(minute_of_day, day_of_year)
    
    # Check if it's daytime (elevation > 0)
    if elevation > 0:
        # Calculate position based on time between sunrise and sunset (simplified for this port)
        # In v2 there was global SUNRISE/SUNSET. We should recalculate them or use defaults.
        # For now, we reuse the basic sunrise/sunset concept but modulated by elevation
        
        # NOTE: To FULLY replicate v2 we need the init_solar_day logic too.
        # But for position, we can approximate knowing elevation.
        # X position roughly tracks time of day.
        
        # Re-implementing the V2 scientific math fully:
        
        # We need SUNRISE_TIME and SUNSET_TIME. 
        # For efficiency, we'll calculate them on the fly or assume standard 
        # unless we port init_solar_day.
        # Let's port calculate_solar_parameters() to be safe.
        
        start_min = 6 * 60
        end_min = 18 * 60
        day_len = end_min - start_min
        
        if end_min > start_min:
             day_position = (minute_of_day - start_min) / day_len
        else:
             day_position = 0.5 # Fallback
             
        day_position = max(0, min(1, day_position))
        x = 0.5 + day_position * 54
        
        # Calculate sun size based on elevation angle
        size = 2 + 6 * min(1, elevation / 45)
        size = round(size / 2) * 2
        
        # Calculate vertical center position
        y = (8 - size) // 2 + size // 2
        
        # Sun color calculation
        r = 255
        if elevation < 10:
             sunrise_factor = elevation / 10
             g = int(100 + 155 * sunrise_factor)
             b = int(50 + 205 * sunrise_factor)
        else:
             g = 255
             b = 255
             
        # Intensity based on air mass
        sin_elev = math.sin(math.radians(elevation))
        if sin_elev > 0:
            air_mass = 1 / (sin_elev + 0.50572 * math.pow(elevation + 6.07995, -1.6364))
            extinction = 0.21
            rel_intensity = math.exp(-extinction * air_mass)
        else:
            rel_intensity = 0
            
        brightness_factor = rel_intensity * INTENSITY_SCALE
        r = clamp(int(r * brightness_factor), 0, MAX_BRIGHTNESS)
        g = clamp(int(g * brightness_factor), 0, MAX_BRIGHTNESS)
        b = clamp(int(b * brightness_factor), 0, MAX_BRIGHTNESS)
        
    return (x, int((r+g+b)/3/2.55)) # Return compatible format (x, intensity)
    # Note: v2 returned (x, y, size, r, g, b). The current architecture expects (x, intensity).
    # This is a friction point. The current 'update_sun_display' handles drawing.
    # To fully restore v2 visuals, we should update 'update_sun_display' too.

def calculate_solar_elevation(minute_of_day, day_of_year):
    """Calculate solar elevation angle"""
    # Convert minute of day to hour angle
    solar_noon_minutes = 12 * 60
    eot_minutes = equation_of_time(day_of_year)
    longitude_correction = (0 * 15 - LONGITUDE) / 15 * 60 # Assuming UTC+0 for simplistic port
    adjusted_minutes = minute_of_day + eot_minutes - longitude_correction
    
    hour_angle = (adjusted_minutes - solar_noon_minutes) * 0.25
    hour_angle_rad = math.radians(hour_angle)
    
    declination = calculate_declination(day_of_year)
    declination_rad = math.radians(declination)
    latitude_rad = math.radians(LATITUDE)
    
    sin_elevation = (math.sin(latitude_rad) * math.sin(declination_rad) + 
                    math.cos(latitude_rad) * math.cos(declination_rad) * 
                    math.cos(hour_angle_rad))
                    
    elevation_rad = math.asin(max(-1, min(1, sin_elevation)))
    return math.degrees(elevation_rad)

def calculate_declination(day_of_year):
    """Calculate solar declination angle"""
    return 23.45 * math.sin(math.radians(360/365 * (day_of_year - 81)))

def equation_of_time(day_of_year):
    """Calculate equation of time adjustment"""
    B = 2 * math.pi * (day_of_year - 1) / 365
    eot = 229.18 * (0.000075 + 0.001868*math.cos(B) - 0.032077*math.sin(B) 
                    - 0.014615*math.cos(2*B) - 0.040849*math.sin(2*B))
    return eot


def get_sun_position(minute_of_day):
    """Get sun position based on current solar mode"""
    if SOLAR_MODE == "SCIENTIFIC":
        day_of_year = date_to_day_number(SIMULATION_DATE)
        return get_sun_position_scientific(minute_of_day, day_of_year)
    else:
        return get_sun_position_basic(minute_of_day)


def date_to_day_number(date_yyyymmdd):
    """Convert YYYYMMDD to day of year (1-365)"""
    year = date_yyyymmdd // 10000
    month = (date_yyyymmdd // 100) % 100
    day = date_yyyymmdd % 100
    
    # Days in each month (non-leap year)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check for leap year
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        days_in_month[1] = 29
    
    # Sum days in previous months + current day
    day_of_year = sum(days_in_month[:month-1]) + day
    
    return day_of_year


# ============================================================================
# V. DISPLAY UPDATE
# ============================================================================

def update_sun_display(hw, dm, minute_of_day):
    """
    Update NeoPixel panel and LCD with current sun position
    
    Args:
        hw: HardwareESP32 instance
        dm: DisplayManager instance
        minute_of_day: Current simulation time in minutes
    """
    # Get sun position and intensity
    x_pos, intensity = get_sun_position(minute_of_day)
    
    # Clear panel
    hw.pixels.fill((0, 0, 0))
    
    if intensity > 0:
        # Calculate RGB values based on intensity
        brightness = int(MAX_BRIGHTNESS * intensity / 100)
        
        # Simple white/yellow sun
        r = brightness
        g = brightness
        b = int(brightness * 0.8)  # Slightly yellow
        
        # Draw sun at x_pos (simplified - just light up a vertical column)
        for y in range(8):
            index = hw.xy_to_index(x_pos, y)
            if 0 <= index < len(hw.pixels):
                hw.pixels[index] = (r, g, b)
    
    # Write to panel
    hw.pixels.write()
    
    # Update display with sim time and intensity
    time_str = time_to_string(minute_of_day)
    speed_str = f"x{TIME_SCALE}" if TIME_SCALE > 0 else "HOLD"
    dm.display_status(minute_of_day * 60, TIME_SCALE, intensity, False)


# ============================================================================
# VI. ROTATION CONTROL
# ============================================================================

def update_rotation(hw, minute_of_day):
    """
    Update platform rotation based on sun position
    
    Args:
        hw: HardwareESP32 instance
        minute_of_day: Current simulation time in minutes
    """
    x_pos, intensity = get_sun_position(minute_of_day)
    
    # Only rotate during daytime if ROTATION_AT_NIGHT is False
    if not ROTATION_AT_NIGHT and intensity == 0:
        return
    
    # Map x position (0-55) to rotation angle (0-180 degrees)
    angle = int((x_pos / 55.0) * 180)
    
    # Set servo angle
    hw.set_servo1_angle(angle)


# ============================================================================
# VII. COMMAND HANDLER
# ============================================================================

def handle_command(cmd, hw, dm):
    """
    Process commands from BLE or serial
    
    Args:
        cmd: Command string
        hw: HardwareESP32 instance
        dm: DisplayManager instance
        
    Returns:
        str: Response message
    """
    global TIME_SCALE, START_TIME_HHMM, simulation_running
    
    parts = cmd.strip().upper().split()
    if not parts:
        return "ERROR: Empty command"
    
    command = parts[0]
    
    # === ECHO ===
    if command == "ECHO":
        return f"Echo: {' '.join(parts[1:])}"
    
    # === STATUS ===
    elif command == "STATUS":
        sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
        time_str = time_to_string(sim_minutes)
        speed_str = f"{TIME_SCALE}X" if TIME_SCALE > 0 else "HOLD"
        _, intensity = get_sun_position(sim_minutes)
        mem_free = gc.mem_free() // 1024
        # Legacy format for compatibility
        return f"Time:{time_str} Speed:{speed_str} Int:{intensity}% Mem:{mem_free}KB"
    
    # === SET SPEED ===
    elif command == "SPEED" and len(parts) >= 2:
        try:
            new_speed = float(parts[1]) # Changed to float to support 0.1x etc
            # V2 supported any float speed
            set_time_scale(new_speed)
            dm.display_message(f"Speed: {new_speed}X" if new_speed > 0 else "Speed: HOLD", "", 2000)
            return f"OK: Speed set to {new_speed}X" if new_speed > 0 else "OK: HOLD mode"
        except ValueError:
            return f"ERROR: Invalid speed value '{parts[1]}'"
    
    # === SET TIME ===
    elif command == "TIME" and len(parts) >= 2:
        try:
            new_time = int(parts[1])
            if 0 <= new_time <= 2359:
                set_sim_time(new_time)
                dm.display_message(f"Time: {new_time:04d}", "", 2000)
                return f"OK: Time set to {new_time:04d}"
            else:
                return "ERROR: Time must be 0000-2359"
        except ValueError:
            return f"ERROR: Invalid time value '{parts[1]}'"

    # === SOLAR MODE ===
    elif command == "SOLARMODE" and len(parts) >= 2:
        mode = parts[1].upper()
        if mode in ["BASIC", "SCIENTIFIC"]:
            global SOLAR_MODE
            SOLAR_MODE = mode
            return f"OK: Solar mode set to {mode}"
        return "ERROR: Mode must be BASIC or SCIENTIFIC"

    # === SIM DATE ===
    elif command == "DATE" and len(parts) >= 2:
        try:
            global SIMULATION_DATE
            SIMULATION_DATE = int(parts[1])
            return f"OK: Date set to {SIMULATION_DATE}"
        except:
            return "ERROR: Invalid date"

    # === LOCATION ===
    elif command == "LOCATION" and len(parts) >= 3:
        try:
            global LATITUDE, LONGITUDE
            LATITUDE = float(parts[1])
            LONGITUDE = float(parts[2])
            return f"OK: Location set to {LATITUDE}, {LONGITUDE}"
        except:
            return "ERROR: Invalid coordinates"

    # === SUN COLOR ===
    elif command == "SUNCOLOR" and len(parts) >= 2:
        global SUN_COLOR_MODE, CUSTOM_SUN_R, CUSTOM_SUN_G, CUSTOM_SUN_B
        mode = parts[1].upper()
        if mode in ["NATURAL", "BLUE", "CUSTOM"]:
             SUN_COLOR_MODE = mode
             if mode == "CUSTOM" and len(parts) >= 5:
                 try:
                     CUSTOM_SUN_R = int(parts[2])
                     CUSTOM_SUN_G = int(parts[3])
                     CUSTOM_SUN_B = int(parts[4])
                 except: pass # Keep previous if error
             return f"OK: Sun color mode set to {mode}"
        return "ERROR: Invalid sun color mode"

    # === ROTATION CONFIG ===
    elif command == "ROTATION":
        if len(parts) >= 2:
            sub = parts[1].upper()
            if sub == "ENABLE":
                global ROTATION_ENABLED
                ROTATION_ENABLED = True
                return "OK: Rotation enabled"
            elif sub == "DISABLE":
                ROTATION_ENABLED = False
                return "OK: Rotation disabled"
            elif sub == "MODE" and len(parts) >= 3:
                global ROTATION_CAPTURE_MODE
                mode = parts[2].upper()
                if mode in ["STILLS", "VIDEO"]:
                    ROTATION_CAPTURE_MODE = mode
                    return f"OK: Rotation mode {mode}"
            elif sub == "IMAGES" and len(parts) >= 3:
                global IMAGES_PER_ROTATION
                IMAGES_PER_ROTATION = int(parts[2])
                return f"OK: Images per rotation {IMAGES_PER_ROTATION}"
    
    # === CAMERA CONFIG ===
    elif command == "CAMERA":
        if len(parts) >= 2:
            sub = parts[1].upper()
            if sub == "TRIGGER":
                hw.trigger_camera_shutter()
                return "OK: Camera triggered"
            elif sub == "SERVO" and len(parts) >= 3:
                global ROTATION_CAMERA_SERVO
                ROTATION_CAMERA_SERVO = int(parts[2])
                return f"OK: Camera servo set to {ROTATION_CAMERA_SERVO}"

    # === FILL PANEL ===
    elif command == "FILL" and len(parts) >= 4:
        try:
            r = int(parts[1])
            g = int(parts[2])
            b = int(parts[3])
            if all(0 <= val <= 255 for val in [r, g, b]):
                hw.fill_panel(r, g, b)
                dm.display_message(f"Fill RGB", f"{r},{g},{b}", 2000)
                return f"OK: Panel filled with RGB({r},{g},{b})"
            else:
                return "ERROR: RGB values must be 0-255"
        except ValueError:
            return "ERROR: Invalid RGB values"
    
    # === ROTATE MANUAL ===
    elif command == "ROTATE" and len(parts) >= 2:
        try:
            angle = float(parts[1])
            if 0 <= angle <= 360:
                hw.set_servo1_angle(angle)
                dm.display_rotation_angle(angle)
                return f"OK: Rotated to {angle}°"
            else:
                return "ERROR: Angle must be 0-360"
        except ValueError:
            return f"ERROR: Invalid angle '{parts[1]}'"

    # === INTENSITY SCALE ===
    elif command == "INTENSITY" and len(parts) >= 2:
        global INTENSITY_SCALE
        try:
            new_scale = float(parts[1])
            if 0 <= new_scale <= 2.0:
                INTENSITY_SCALE = new_scale
                dm.display_message(f"Intensity", f"Scale: {new_scale}", 2000)
                return f"OK: Intensity scale set to {new_scale}"
            else:
                return "ERROR: Intensity scale must be 0.0-2.0"
        except ValueError:
            return f"ERROR: Invalid intensity value '{parts[1]}'"
    
    # === MEMORY INFO ===
    elif command == "MEM":
        free_kb = gc.mem_free() // 1024
        total_kb = 512  # Approximate
        dm.display_memory_info(free_kb, total_kb)
        gc.collect()
        free_after_kb = gc.mem_free() // 1024
        return f"OK: Memory: {free_kb}KB free ({free_after_kb}KB after GC)"
    
    # === LCD MESSAGE ===
    elif command == "LCD" and len(parts) >= 2:
        message = ' '.join(parts[1:])
        dm.display_message(message[:16], "", 3000)
        return f"OK: LCD message: {message}"
    
    # === HELP ===
    elif command == "HELP":
        return ("Commands: ECHO, STATUS, SPEED, TIME, SOLARMODE, DATE, LOCATION "
                "SUNCOLOR, ROTATION, CAMERA, FILL, ROTATE, INTENSITY, MEM, LCD")
     
    # === STOP/START ===
    elif command == "STOP":
        simulation_running = False
        dm.display_message("Simulation", "STOPPED", 2000)
        return "OK: Simulation stopped"
    
    elif command == "START":
        simulation_running = True
        dm.display_message("Simulation", "RUNNING", 2000)
        return "OK: Simulation started"
    
    # === LOAD PROFILE ===
    elif command == "LOADPROFILE" and len(parts) >= 2:
        return f"CMD_LOADPROFILE:{parts[1]}"

    # === SAVE PROFILE ===
    elif command == "SAVEPROFILE" and len(parts) >= 2:
        profilename = parts[1]
        note = " ".join(parts[2:]) if len(parts) > 2 else ""
        filename = f"{profilename}.txt"
        try:
            with open(filename, "w") as f:
                print(f"[SIM] Saving profile {filename}...")
                if note: f.write(f"NOTE={note}\n")
                f.write(f"START_TIME_HHMM={START_TIME_HHMM}\n")
                f.write(f"TIME_SCALE={TIME_SCALE}\n")
                f.write(f"INTENSITY_SCALE={INTENSITY_SCALE}\n")
                f.write(f"SIMULATION_DATE={SIMULATION_DATE}\n")
                f.write(f"LATITUDE={LATITUDE}\n")
                f.write(f"SOLAR_MODE={SOLAR_MODE}\n")
                f.write(f"SUN_COLOR_MODE={SUN_COLOR_MODE}\n")
                f.write(f"DUAL_SUN_ENABLED={DUAL_SUN_ENABLED}\n")
                f.write(f"ROTATION_ENABLED={ROTATION_ENABLED}\n")
                f.write(f"ROTATION_CAPTURE_MODE={ROTATION_CAPTURE_MODE}\n")
                f.write(f"ROTATION_CYCLE_INTERVAL_MINUTES={ROTATION_CYCLE_INTERVAL_MINUTES}\n")
                f.write(f"IMAGES_PER_ROTATION={IMAGES_PER_ROTATION}\n")
                f.write(f"ROTATION_CAMERA_SERVO={ROTATION_CAMERA_SERVO}\n")
                f.write(f"CUSTOM_SUN_R={CUSTOM_SUN_R}\n")
                f.write(f"CUSTOM_SUN_G={CUSTOM_SUN_G}\n")
                f.write(f"CUSTOM_SUN_B={CUSTOM_SUN_B}\n")
                
                # Extended V2 properties
                f.write(f"SERVO2_INTERVAL_DAY_SEC={SERVO2_INTERVAL_DAY_SEC}\n")
                f.write(f"SERVO2_INTERVAL_NIGHT_SEC={SERVO2_INTERVAL_NIGHT_SEC}\n")
                f.write(f"SERVO3_INTERVAL_DAY_SEC={SERVO3_INTERVAL_DAY_SEC}\n")
                f.write(f"SERVO3_INTERVAL_NIGHT_SEC={SERVO3_INTERVAL_NIGHT_SEC}\n")
                f.write(f"STILLS_IMAGING_INTERVAL_SEC={STILLS_IMAGING_INTERVAL_SEC}\n")
                f.write(f"CAMERA_TRIGGER_HOLD_MS={CAMERA_TRIGGER_HOLD_MS}\n")
                f.write(f"ROTATION_INCREMENT_DEGREES={ROTATION_INCREMENT_DEGREES}\n")
                f.write(f"ROTATION_STEP_INTERVAL_MS={ROTATION_STEP_INTERVAL_MS}\n")
                f.write(f"ROTATION_SPEED_PRESET={ROTATION_SPEED_PRESET}\n")
                f.write(f"ROTATION_AT_NIGHT={ROTATION_AT_NIGHT}\n")
                f.write(f"RESTART_AFTER_LOAD={RESTART_AFTER_LOAD}\n")

                if PROGRAM_ENABLED:
                    import ujson
                    f.write("PROGRAM_ENABLED=True\n")
                    f.write(f"PROGRAM_REPEATS={PROGRAM_REPEATS}\n")
                    f.write(f"PROGRAM_STEPS={ujson.dumps(PROGRAM_STEPS)}\n")
                else:
                    f.write("PROGRAM_ENABLED=False\n")
                
            return f"OK: Profile '{filename}' saved"
        except Exception as e:
            return f"ERROR: Could not save profile: {e}"

    # === AUTOLOAD ===
    elif command == "AUTOLOAD":
         # v2 syntax was 'set autoload on/off', here we support 'AUTOLOAD ON/OFF'
         if len(parts) >= 2:
             global AUTO_LOAD_LATEST_PROFILE
             val = parts[1].upper()
             if val in ("ON", "TRUE", "1"):
                 AUTO_LOAD_LATEST_PROFILE = True
             elif val in ("OFF", "FALSE", "0"):
                 AUTO_LOAD_LATEST_PROFILE = False
             else:
                 return "ERROR: Use ON or OFF"
                 
             try:
                 with open('autoload.cfg', 'w') as f:
                     f.write('1' if AUTO_LOAD_LATEST_PROFILE else '0')
                 return f"OK: Autoload set to {AUTO_LOAD_LATEST_PROFILE}"
             except:
                 return "OK: Autoload set (not persisted)"
                 
    # === PROGRAM CONTROL ===
    elif command == "PROGRAM":
        # Simplified handling
        return "Program commands handled by main loop"
        
    # === UNKNOWN COMMAND ===
    else:
        return f"ERROR: Unknown command '{command}'. Try HELP"


# ============================================================================
# VIII. MAIN SIMULATION CLASS
# ============================================================================

class SolarSimulator:
    """Main solar simulator controller"""
    
    def __init__(self):
        """Initialize simulator with hardware"""
        print("[SIM] Initializing Solar Simulator...")
        
        # Initialize hardware
        self.hw = HardwareESP32(neopixel_count=448)
        self.dm = DisplayManager(self.hw.lcd if self.hw.lcd_available else None)
        
        # Initialize timing
        global start_real_time_ms
        start_real_time_ms = time.ticks_ms()
        
        # Display welcome
        self.dm.display_welcome()
        time.sleep(2)
        
        print("[SIM] Solar Simulator initialized")
        print(f"[SIM] Start time: {START_TIME_HHMM:04d}")
        print(f"[SIM] Time scale: {TIME_SCALE}X")
        print(f"[SIM] Solar mode: {SOLAR_MODE}")
        
        # Init state
        self.program_running = False
        self.current_program_step = 0
        self.current_step_repeat = 0
        self.program_step_start_sim_time = 0
        self.last_printed_minute = -1
        self.hold_step_start_ms = 0
        
        # Try autoload
        self.auto_load_latest_profile()
        
        # If program enabled in profile, start it
        if PROGRAM_ENABLED:
            self.start_program()
    
    def update(self):
        """Update simulation (call this in main loop)"""
        if not simulation_running:
            return
        
        # Get current simulation time
        sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
        
        # Update sun display
        update_sun_display(self.hw, self.dm, sim_minutes)
        
        # Update rotation
        self.update_rotation_cycle(sim_minutes)
        self.update_standalone_servo3()
        
        # Update program state
        self.update_program_state(sim_minutes)
        
        # Garbage collection periodically
        if time.ticks_ms() % 10000 < 100:
            gc.collect()

    # ========================================================================
    # PROGRAM ENGINE METHODS (Ported from v2)
    # ========================================================================

    def get_status_string(self):
        """Generate status string for Serial/BLE"""
        sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
        time_str = time_to_string(sim_minutes)
        speed_str = f"{TIME_SCALE}X" if TIME_SCALE > 0 else "HOLD"
        _, intensity = get_sun_position(sim_minutes)
        mem_free = gc.mem_free() // 1024
        return f"Time:{time_str} Speed:{speed_str} Int:{intensity}% Mem:{mem_free}KB"

    def update_program_state(self, sim_time_minutes):
        """Update program logic"""
        if not self.program_running:
            return

        now_ms = time.ticks_ms()
        
        # Print status periodically
        if int(sim_time_minutes) > self.last_printed_minute:
            # We print the concise status string for parsing
            print(self.get_status_string())
            # We also print the detailed program status for debugging/logging
            self.print_program_status(sim_time_minutes)
            self.last_printed_minute = int(sim_time_minutes)

        step = PROGRAM_STEPS[self.current_program_step]
        step_time_hhmm = step["sim_time_hhmm"]
        step_time_minutes = (step_time_hhmm // 100) * 60 + (step_time_hhmm % 100)
        
        # Initialize step if needed
        if self.program_step_start_sim_time == 0:
            self.program_step_start_sim_time = sim_time_minutes
            self.apply_step_settings(step)
            
            # Handle HOLD steps
            if TIME_SCALE == 0:
                 self.hold_step_start_ms = now_ms
                 if "hold_minutes" not in step and self.current_program_step < len(PROGRAM_STEPS) - 1:
                     # Calculate implied hold duration
                     next_step = PROGRAM_STEPS[self.current_program_step + 1]
                     if "sim_time_hhmm" in next_step:
                         next_step_minutes = (next_step["sim_time_hhmm"] // 100) * 60 + (next_step["sim_time_hhmm"] % 100)
                         current_minutes = int(sim_time_minutes)
                         hold_duration = (next_step_minutes - current_minutes) % 1440
                         step["hold_minutes"] = hold_duration

        # Check for step completion
        target_reached = False
        
        if TIME_SCALE == 0: # HOLD mode
             if "hold_minutes" in step and self.hold_step_start_ms > 0:
                 elapsed_min = time.ticks_diff(now_ms, self.hold_step_start_ms) // 60000
                 if elapsed_min >= step["hold_minutes"]:
                     target_reached = True
        else: # RUN mode
            # Check if we passed the target time
            # Simplified logic: if current time is close to next step time
            if self.current_program_step < len(PROGRAM_STEPS) - 1:
                next_step_hhmm = PROGRAM_STEPS[self.current_program_step + 1]["sim_time_hhmm"]
                target_minutes = (next_step_hhmm // 100) * 60 + (next_step_hhmm % 100)
                
                # Check if we crossed the target time
                # (Simple check: are we within 1 minute of target?)
                diff = (sim_time_minutes - target_minutes) % 1440
                if diff < 2 or diff > 1438: 
                    target_reached = True
            
        if target_reached:
            self.advance_program()

    def advance_program(self):
        """Move to next program step"""
        # Logic to handle repeats and next step
        step = PROGRAM_STEPS[self.current_program_step]
        repeat_limit = step.get("repeat", 1)
        
        if self.current_step_repeat < repeat_limit - 1:
            self.current_step_repeat += 1
            print(f"[PROGRAM] Repeating step {self.current_program_step+1}")
            # Jump back to step start time
            step_time_hhmm = step["sim_time_hhmm"]
            set_sim_time(step_time_hhmm)
        else:
            self.current_step_repeat = 0
            self.current_program_step += 1
            
            if self.current_program_step >= len(PROGRAM_STEPS):
                # Program complete or repeat
                if PROGRAM_REPEATS == -1 or self.current_program_repeat < PROGRAM_REPEATS - 1:
                     self.current_program_repeat += 1
                     self.current_program_step = 0
                     print(f"[PROGRAM] Repeating program (cycle {self.current_program_repeat+1})")
                else:
                    print("[PROGRAM] Program Complete")
                    self.stop_program()
                    return

        self.program_step_start_sim_time = 0 # Reset init flag

    def apply_step_settings(self, step):
        """Apply settings from a program step"""
        global TIME_SCALE, INTENSITY_SCALE, DUAL_SUN_ENABLED
        
        new_speed = step.get("speed", 1)
        if new_speed != TIME_SCALE:
             set_time_scale(new_speed)
             
        if "intensity_scale" in step:
            INTENSITY_SCALE = step["intensity_scale"]
            
        if "dual_sun" in step:
            DUAL_SUN_ENABLED = bool(step["dual_sun"])

    def start_program(self):
        self.program_running = True
        self.current_program_step = 0
        self.current_step_repeat = 0
        self.program_step_start_sim_time = 0
        print("[PROGRAM] Started")

    def stop_program(self):
        self.program_running = False
        print("[PROGRAM] Stopped")

    def print_program_status(self, sim_time_minutes):
        print(f"[PROGRAM] Step {self.current_program_step+1}/{len(PROGRAM_STEPS)} | Sim: {int(sim_time_minutes//60):02d}:{int(sim_time_minutes%60):02d}")

    # ========================================================================
    # ROTATION LOGIC (Ported from v2)
    # ========================================================================

    # ========================================================================
    # ROTATION LOGIC (Ported from v2)
    # ========================================================================

    # ========================================================================
    # ROTATION LOGIC (Fully Ported from v2)
    # ========================================================================

    def update_rotation_cycle(self, sim_minutes):
        """Update rotation state machine - Full V2 Implementation"""
        global rotation_state, last_rotation_absolute_time, rotation_in_progress
        global current_rotation_angle, manual_rotation_triggered
        global camera_lighting_active, rotation_lighting_active, servo2_using_lighting
        global rotation_camera_trigger_started_ms, last_rotation_step_time_ms
        global servo2_controlled_by_rotation, last_stills_trigger_ms
        global return_angle
        
        if not ROTATION_ENABLED:
            return

        now_ms = time.ticks_ms()
        
        # 1. Check for new cycle start
        # Only start new cycle if we are in >1X mode (unless manual trigger?)
        # V2 logic: if sim_time_scale > 1 and rotation_state == 'IDLE'
        if TIME_SCALE > 1 and rotation_state == 'IDLE':
             current_sim_minute = int(sim_minutes) # abs sim time essentially
             # Simplified trigger logic using modulo instead of absolute tracking for robustness
             if current_sim_minute % ROTATION_CYCLE_INTERVAL_MINUTES == 0 and current_sim_minute != last_rotation_absolute_time:
                 last_rotation_absolute_time = current_sim_minute
                 
                 # Check night/day
                 x_pos, _ = get_sun_position(sim_minutes)
                 sun_visible = (x_pos > -4 and x_pos < 60)
                 
                 if not sun_visible and not ROTATION_AT_NIGHT:
                     return
                     
                 print(f"[ROTATION] Starting new 360° imaging cycle at {current_sim_minute}m")
                 manual_rotation_triggered = False
                 rotation_state = 'INITIAL_CAMERA_TRIGGER' if ROTATION_CAMERA_ENABLED else 'ROTATING'
                 rotation_in_progress = True
                 current_rotation_angle = 0
                 
                 if ROTATION_CAPTURE_MODE == "STILLS":
                     last_stills_trigger_ms = now_ms
                 
                 if ROTATION_CAMERA_ENABLED:
                     servo2_controlled_by_rotation = (ROTATION_CAMERA_SERVO == 2)
                     rotation_camera_trigger_started_ms = now_ms
                     # Trigger camera
                     pwm_idx = 1 if ROTATION_CAMERA_SERVO == 2 else 2 # Map to servo idx logic
                     # Assuming set_servo_angle takes index 1,2,3
                     # HardwareESP32: servo2 is index 2, servo3 is index 3
                     self.hw.set_servo_angle(ROTATION_CAMERA_SERVO, 90) # Trigger angle
                     print(f"[ROTATION] Initial camera trigger")
                     
                     if ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                         self.apply_rotation_lighting()
                 else:
                     rotation_state = 'ROTATING'
                     last_rotation_step_time_ms = now_ms
                     self.hw.set_servo1_angle(0)
                     if ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                         self.apply_rotation_lighting()

        # 2. State Machine
        if rotation_state == 'INITIAL_CAMERA_TRIGGER':
            if time.ticks_diff(now_ms, rotation_camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
                self.hw.set_servo_angle(ROTATION_CAMERA_SERVO, 45) # Rest angle
                print(f"[ROTATION] Initial camera trigger released")
                self.hw.trigger_camera_shutter()
                
                rotation_state = 'ROTATING'
                last_rotation_step_time_ms = now_ms
                self.hw.set_servo1_angle(current_rotation_angle)
                
                if ROTATION_CAPTURE_MODE == "VIDEO" and ROTATION_LIGHTING_ENABLED and not rotation_lighting_active:
                    self.apply_rotation_lighting()
                    
        elif rotation_state == 'ROTATING':
            # Calculate next imaging angle
            image_angle = 360.0 / IMAGES_PER_ROTATION
            next_trigger_idx = int(current_rotation_angle // image_angle)
            next_trigger_angle = (next_trigger_idx + 1) * image_angle
            
            if current_rotation_angle < 360:
                # Calculate next step
                # Fixed step logic for port simplicity: 1 degree per update
                next_angle = current_rotation_angle + 1 # Simplified step
                
                if next_angle > next_trigger_angle:
                    current_rotation_angle = next_trigger_angle
                    self.hw.set_servo1_angle(current_rotation_angle)
                    
                    if ROTATION_CAPTURE_MODE == "STILLS" and ROTATION_CAMERA_ENABLED and current_rotation_angle < 360:
                        rotation_state = 'ROTATION_CAMERA_TRIGGER'
                        rotation_camera_trigger_started_ms = now_ms
                        self.hw.set_servo_angle(ROTATION_CAMERA_SERVO, 90)
                        print(f"[ROTATION] Stills trigger at {current_rotation_angle}")
                        return
                else:
                    if time.ticks_diff(now_ms, last_rotation_step_time_ms) >= ROTATION_STEP_INTERVAL_MS:
                        current_rotation_angle = next_angle
                        self.hw.set_servo1_angle(current_rotation_angle)
                        last_rotation_step_time_ms = now_ms
                        
            if current_rotation_angle >= 360:
                # End of rotation
                if ROTATION_CAPTURE_MODE == "VIDEO" and rotation_lighting_active:
                    self.deactivate_rotation_lighting()
                rotation_state = 'DWELL'
                last_rotation_step_time_ms = now_ms
                print("[ROTATION] Rotation complete, DWELL")
                
        elif rotation_state == 'ROTATION_CAMERA_TRIGGER':
             if time.ticks_diff(now_ms, rotation_camera_trigger_started_ms) >= CAMERA_TRIGGER_HOLD_MS:
                 self.hw.set_servo_angle(ROTATION_CAMERA_SERVO, 45)
                 self.hw.trigger_camera_shutter()
                 rotation_state = 'ROTATING'
                 last_rotation_step_time_ms = now_ms
                 
        elif rotation_state == 'DWELL':
             if time.ticks_diff(now_ms, last_rotation_step_time_ms) >= 1500: # 1.5s dwell
                 if ROTATION_CAPTURE_MODE == "STILLS" and rotation_lighting_active:
                     self.deactivate_rotation_lighting()
                 rotation_state = 'RETURNING'
                 return_angle = 360
                 last_rotation_step_time_ms = now_ms
                 print("[ROTATION] Returning")
                 
        elif rotation_state == 'RETURNING':
             if time.ticks_diff(now_ms, last_rotation_step_time_ms) >= 50:
                 return_angle = max(0, return_angle - 5)
                 self.hw.set_servo1_angle(return_angle)
                 last_rotation_step_time_ms = now_ms
                 
                 if return_angle <= 0:
                     rotation_state = 'IDLE'
                     rotation_in_progress = False
                     servo2_controlled_by_rotation = False
                     print("[ROTATION] Cycle Validated/Complete")

        # Fallback for when rotation is disabled but we want solar tracking
        if rotation_state == 'IDLE' and not ROTATION_AT_NIGHT:
             # Basic tracking
             x_pos, _ = get_sun_position(sim_minutes)
             if x_pos > 0:
                 angle = int((x_pos / 55.0) * 180)
                 self.hw.set_servo1_angle(angle)

    def update_standalone_servo2(self):
        """Standalone logic for Servo 2 (if not used by rotation)"""
        global servo2_state, last_servo2_trigger_ms, servo2_trigger_start_ms
        global servo2_controlled_by_rotation, camera_lighting_active, servo2_using_lighting
        
        if servo2_controlled_by_rotation: return
        
        now_ms = time.ticks_ms()
        # Intervals logic...
        current_interval = SERVO3_INTERVAL_DAY_SEC if True else 0 # Simplified check
        
        if servo2_state == 'IDLE':
            if current_interval > 0 and time.ticks_diff(now_ms, last_servo2_trigger_ms) >= current_interval * 1000:
                servo2_state = 'TRIGGERED'
                servo2_trigger_start_ms = now_ms
                if CAMERA_LIGHTING_ENABLED and not rotation_lighting_active:
                     servo2_using_lighting = True
                     camera_lighting_active = True
                     self.apply_camera_lighting()
                self.hw.set_servo_angle(2, 90)
                print("[SERVO2] Trigger")
        elif servo2_state == 'TRIGGERED':
            if time.ticks_diff(now_ms, servo2_trigger_start_ms) >= CAMERA_TRIGGER_HOLD_MS:
                servo2_state = 'IDLE'
                last_servo2_trigger_ms = now_ms
                self.hw.set_servo_angle(2, 45)
                servo2_using_lighting = False
                if camera_lighting_active and not servo3_using_lighting:
                     self.deactivate_camera_lighting()

    def update_standalone_servo3(self):
        """Update servo 3 logic"""
        global servo3_state, last_servo3_trigger_ms, servo3_trigger_start_ms
        global servo3_using_lighting, camera_lighting_active, rotation_lighting_active
        
        now_ms = time.ticks_ms()
        sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
        
        # Determine intervals
        x_pos, _ = get_sun_position(sim_minutes)
        sun_visible = (x_pos > 0 and x_pos < 55)
        current_interval = SERVO3_INTERVAL_DAY_SEC if sun_visible else SERVO3_INTERVAL_NIGHT_SEC
        
        if servo3_state == 'IDLE':
            if current_interval > 0:
                 if time.ticks_diff(now_ms, last_servo3_trigger_ms) >= (current_interval * 1000):
                     servo3_state = 'TRIGGERED'
                     servo3_trigger_start_ms = now_ms
                     
                     if CAMERA_LIGHTING_ENABLED and not rotation_lighting_active:
                         servo3_using_lighting = True
                         camera_lighting_active = True
                         self.apply_camera_lighting()
                         
                     self.hw.set_servo_angle(3, 90) # Trigger
                     print(f"[SERVO3] Triggered ({'day' if sun_visible else 'night'} interval)")
                     
        elif servo3_state == 'TRIGGERED':
            if time.ticks_diff(now_ms, servo3_trigger_start_ms) >= CAMERA_TRIGGER_HOLD_MS:
                servo3_state = 'IDLE'
                last_servo3_trigger_ms = now_ms
                self.hw.set_servo_angle(3, 45) # Rest
                servo3_using_lighting = False
                if camera_lighting_active and not servo2_using_lighting:
                    self.deactivate_camera_lighting()

    def apply_rotation_lighting(self):
        """Activate rotation lighting"""
        global rotation_lighting_active
        color = (ROTATION_LIGHT_R, ROTATION_LIGHT_G, ROTATION_LIGHT_B)
        self.hw.pixels.fill((0,0,0))
        # Apply to all panels for now (simplified)
        self.hw.fill_panel(color[0], color[1], color[2])
        rotation_lighting_active = True
        
    def deactivate_rotation_lighting(self):
        """Deactivate rotation lighting"""
        global rotation_lighting_active
        rotation_lighting_active = False
        self.hw.pixels.fill((0,0,0))
        self.hw.pixels.write()

    def apply_camera_lighting(self):
        """Activate camera lighting"""
        color = (CAMERA_LIGHT_R, CAMERA_LIGHT_G, CAMERA_LIGHT_B)
        self.hw.fill_panel(color[0], color[1], color[2]) # Simplified to all panels
        
    def deactivate_camera_lighting(self):
        """Deactivate camera lighting"""
        global camera_lighting_active
        camera_lighting_active = False
        self.hw.pixels.fill((0,0,0))
        self.hw.pixels.write()


    # ========================================================================
    # PROFILE LOADING
    # ========================================================================
    
    def load_profile(self, filename):
        """Load settings from a profile file"""
        import os
        print(f"[SIM] Loading profile {filename}...")
        try:
             with open(filename, 'r') as f:
                 for line in f:
                     line = line.strip()
                     if not line or line.startswith("#"): continue
                     if "=" in line:
                         key, val = line.split("=", 1)
                         key = key.strip()
                         val = val.strip()
                         self._apply_setting(key, val)
             
             print(f"[SIM] Profile loaded.")
             if RESTART_AFTER_LOAD:
                 self.start_program()
                         
        except Exception as e:
            print(f"[SIM] Error loading profile: {e}")

    def _apply_setting(self, key, val):
        """Apply a single setting from profile"""
        global START_TIME_HHMM, TIME_SCALE, INTENSITY_SCALE, SIMULATION_DATE
        global LATITUDE, SOLAR_MODE, PROGRAM_ENABLED, PROGRAM_STEPS, PROGRAM_REPEATS
        global ROTATION_ENABLED
        
        try:
            if key == "START_TIME_HHMM": START_TIME_HHMM = int(val)
            elif key == "TIME_SCALE": set_time_scale(float(val))
            elif key == "INTENSITY_SCALE": INTENSITY_SCALE = float(val)
            elif key == "SIMULATION_DATE": SIMULATION_DATE = int(val)
            elif key == "PROGRAM_ENABLED": PROGRAM_ENABLED = (val.lower() == "true")
            elif key == "ROTATION_ENABLED": ROTATION_ENABLED = (val.lower() == "true")
            elif key == "PROGRAM_STEPS": 
                import ujson
                PROGRAM_STEPS = ujson.loads(val)
            elif key == "PROGRAM_REPEATS": PROGRAM_REPEATS = int(val)
        except Exception as e:
            print(f"[SIM] Error applying {key}: {e}")

    def auto_load_latest_profile(self):
        """Attempt to load the most recent profile"""
        if not AUTO_LOAD_LATEST_PROFILE:
            return
            
        import os
        try:
            files = [f for f in os.listdir() if f.endswith(".txt") and f.startswith("profile_")]
            if files:
                latest = sorted(files)[-1]
                self.load_profile(latest)
        except Exception as e:
            print(f"[SIM] Auto-load failed: {e}")
    
    def process_command(self, cmd):
        """Process a command and return response"""
        response = handle_command(cmd, self.hw, self.dm)
        
        # Intercept special commands
        if response.startswith("CMD_LOADPROFILE:"):
            filename = response.split(":")[1]
            self.load_profile(filename + ".txt")
            return f"OK: Loading {filename}..."
            
        return response
    
    def shutdown(self):
        """Shutdown simulator"""
        print("[SIM] Shutting down...")
        self.hw.shutdown()
        self.dm.clear()
        print("[SIM] Shutdown complete")


# ============================================================================
# IX. TEST CODE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SOLAR SIMULATOR ESP32-S3 - TEST MODE")
    print("="*60 + "\n")
    
    # Start BLE server for wireless control
    def test_command_handler(cmd):
        # You can route this to your simulator's process_command if desired
        print(f"[BLE] Command received: {cmd}")
        return f"Echo: {cmd}"
    ble = BLEServer(name="SolarSim-ESP32", command_handler=test_command_handler)

    # Create simulator
    sim = SolarSimulator()
    
    # Test commands
    test_commands = [
        "STATUS",
        "SPEED 6",
        "TIME 1200",
        "ROTATE 90",
        "FILL 30 0 0",
        "CAMERA",
        "MEM"
    ]
    
    print("\nTesting commands:")
    for cmd in test_commands:
        print(f"\n> {cmd}")
        response = sim.process_command(cmd)
        print(f"< {response}")
        time.sleep(2)
    
    print("\nRunning simulation for 30 seconds...")
    start_test = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start_test) < 30000:
        sim.update()
        time.sleep_ms(100)
    
    sim.shutdown()
    print("\n✓ Test complete!\n")
