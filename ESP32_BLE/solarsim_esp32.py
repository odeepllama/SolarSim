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

# ============================================================================
# I. CORE SIMULATION PARAMETERS
# ============================================================================

# Time Configuration
START_TIME_HHMM = 600          # Start at 6:00 AM
TIME_SCALE = 1                  # Time scaling factor (1, 6, 60, 600, or 0 for HOLD)
SIMULATION_DATE = 20260130      # Date in YYYYMMDD format

# Solar Simulation Mode
SOLAR_MODE = "BASIC"            # "BASIC" or "SCIENTIFIC"
MAX_BRIGHTNESS = 50             # Maximum brightness (0-255, reduced for testing)
INTENSITY_SCALE = 1.0           # Global intensity multiplier

# Location Parameters (for SCIENTIFIC mode)
LATITUDE = 0                    # Latitude in degrees
LONGITUDE = 0                   # Longitude in degrees
SOLAR_NOON_MINUTES = 12 * 60    # Solar noon time in minutes

# Rotation Configuration
ROTATION_AT_NIGHT = False       # Disable rotation during nighttime
ROTATION_INCREMENT_DEGREES = 15  # Degrees to rotate per step

# ============================================================================
# II. SIMULATION STATE
# ============================================================================

# Global state variables
start_real_time_ms = 0
frozen_sim_time_minutes = 0
simulation_running = True

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
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


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
    
    Args:
        minute_of_day: Minutes since midnight
        day_of_year: Day number (1-365)
        
    Returns:
        tuple: (x_position, intensity)
    """
    # Simplified scientific calculation
    # This is a placeholder - full implementation would include:
    # - Solar declination
    # - Equation of time
    # - Hour angle calculation
    # For now, fall back to basic mode
    return get_sun_position_basic(minute_of_day)


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
        return f"Time:{time_str} Speed:{speed_str} Int:{intensity}% Mem:{mem_free}KB"
    
    # === SET SPEED ===
    elif command == "SPEED" and len(parts) >= 2:
        try:
            new_speed = int(parts[1])
            if new_speed in [0, 1, 6, 60, 600]:
                set_time_scale(new_speed)
                dm.display_message(f"Speed: {new_speed}X" if new_speed > 0 else "Speed: HOLD", "", 2000)
                return f"OK: Speed set to {new_speed}X" if new_speed > 0 else "OK: HOLD mode"
            else:
                return "ERROR: Speed must be 0, 1, 6, 60, or 600"
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
    
    # === ROTATE ===
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
    
    # === CAMERA TRIGGER ===
    elif command == "CAMERA":
        hw.trigger_camera_shutter()
        dm.display_message("Camera", "Triggered!", 1000)
        return "OK: Camera triggered"
    
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
        return ("Commands: ECHO, STATUS, SPEED <0|1|6|60|600>, TIME <HHMM>, "
                "FILL <r> <g> <b>, ROTATE <angle>, CAMERA, INTENSITY <scale>, MEM, LCD <msg>")
    
    # === STOP/START ===
    elif command == "STOP":
        simulation_running = False
        dm.display_message("Simulation", "STOPPED", 2000)
        return "OK: Simulation stopped"
    
    elif command == "START":
        simulation_running = True
        dm.display_message("Simulation", "RUNNING", 2000)
        return "OK: Simulation started"
    
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
    
    def update(self):
        """Update simulation (call this in main loop)"""
        if not simulation_running:
            return
        
        # Get current simulation time
        sim_minutes = get_sim_time_minutes(START_TIME_HHMM, start_real_time_ms, TIME_SCALE)
        
        # Update sun display
        update_sun_display(self.hw, self.dm, sim_minutes)
        
        # Update rotation
        update_rotation(self.hw, sim_minutes)
        
        # Garbage collection periodically
        if time.ticks_ms() % 10000 < 100:
            gc.collect()
    
    def process_command(self, cmd):
        """Process a command and return response"""
        return handle_command(cmd, self.hw, self.dm)
    
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
