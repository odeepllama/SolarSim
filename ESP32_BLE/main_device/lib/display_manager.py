"""
Display Manager for ESP32-S3 Solar Simulator
==============================================
Manages LCD display updates and provides consistent interface
to replace RP2040's 5x5 LED matrix display functionality.

LCD Layout (16x2):
-------------------
Line 0: Status message or sim time with speed
Line 1: Intensity, autoload status, or secondary info
"""

import time

class DisplayManager:
    """Manages all display updates for the Solar Simulator"""
    
    def __init__(self, lcd=None):
        """
        Initialize display manager
        
        Args:
            lcd: LCD1602 instance (or None if no display available)
        """
        self.lcd = lcd
        self.lcd_available = lcd is not None
        
        # Display state tracking
        self.current_line0 = ""
        self.current_line1 = ""
        self.last_update_time = 0
        self.update_interval_ms = 200  # Minimum time between LCD updates (ms)
        
        # Display mode tracking
        self.display_mode = "status"  # "status", "sim_time", "message", "error"
        
        print(f"[DISP] Display manager initialized (LCD: {self.lcd_available})")
    
    def _should_update(self):
        """Check if enough time has passed since last update"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_update_time) >= self.update_interval_ms:
            self.last_update_time = now
            return True
        return False
    
    def _format_time(self, seconds):
        """
        Format seconds into HH:MM:SS or MM:SS
        
        Args:
            seconds: Time in seconds
            
        Returns:
            str: Formatted time string
        """
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def update_display(self, line0, line1, force=False):
        """
        Update LCD display with new content
        
        Args:
            line0: Text for line 0 (top) - max 16 chars
            line1: Text for line 1 (bottom) - max 16 chars
            force: Force update even if throttled
        """
        if not self.lcd_available:
            return
        
        # Throttle updates unless forced
        if not force and not self._should_update():
            return
        
        # Truncate to 16 characters
        line0 = str(line0)[:16]
        line1 = str(line1)[:16]
        
        # Only update if content changed
        if line0 != self.current_line0 or line1 != self.current_line1 or force:
            try:
                self.lcd.clear()
                self.lcd.print(line0, 0, 0)
                self.lcd.print(line1, 0, 1)
                
                self.current_line0 = line0
                self.current_line1 = line1
            except Exception as e:
                print(f"[DISP] Error updating display: {e}")
    
    def display_status(self, sim_time, sim_speed, intensity, autoload):
        """
        Display simulation status (replaces 5x5 matrix status display)
        
        Args:
            sim_time: Current simulation time in seconds
            sim_speed: Simulation speed multiplier (e.g., 60.0)
            intensity: Light intensity percentage (0-100)
            autoload: Autoload enabled (True/False)
        """
        self.display_mode = "status"
        
        # Line 0: Time and speed
        time_str = self._format_time(sim_time)
        speed_str = f"x{sim_speed:.0f}" if sim_speed >= 1 else f"x{sim_speed:.1f}"
        line0 = f"{time_str} {speed_str}"
        
        # Line 1: Intensity and autoload
        intensity_str = f"I:{intensity:3d}%"
        autoload_str = "AL:ON" if autoload else "AL:OFF"
        line1 = f"{intensity_str} {autoload_str}"
        
        self.update_display(line0, line1)
    
    def display_sim_time(self, sim_time, sim_speed=None):
        """
        Display just simulation time (simplified status)
        
        Args:
            sim_time: Current simulation time in seconds
            sim_speed: Optional speed multiplier
        """
        self.display_mode = "sim_time"
        
        time_str = self._format_time(sim_time)
        
        if sim_speed is not None:
            speed_str = f"x{sim_speed:.0f}" if sim_speed >= 1 else f"x{sim_speed:.1f}"
            line0 = f"Time: {time_str}"
            line1 = f"Speed: {speed_str}"
        else:
            line0 = f"Time: {time_str}"
            line1 = ""
        
        self.update_display(line0, line1)
    
    def display_message(self, message, line1="", duration_ms=0):
        """
        Display a temporary message (replaces matrix message display)
        
        Args:
            message: Message for line 0
            line1: Optional message for line 1
            duration_ms: If > 0, automatically clear after this time
        """
        self.display_mode = "message"
        self.update_display(message, line1, force=True)
        
        if duration_ms > 0:
            time.sleep_ms(duration_ms)
            self.clear_message()
    
    def display_error(self, error_msg, details=""):
        """
        Display error message
        
        Args:
            error_msg: Error description (line 0)
            details: Optional details (line 1)
        """
        self.display_mode = "error"
        self.update_display(f"ERR: {error_msg[:11]}", details, force=True)
    
    def clear_message(self):
        """Clear temporary message and return to previous mode"""
        if self.display_mode in ["message", "error"]:
            self.display_mode = "status"
            self.update_display("", "", force=True)
    
    def display_welcome(self):
        """Display welcome message on startup"""
        self.display_message("SolarSim ESP32", "Initializing...", duration_ms=2000)
    
    def display_ready(self):
        """Display ready message"""
        self.display_message("System Ready", "Waiting...", duration_ms=2000)
    
    def display_program_info(self, program_name, step_info):
        """
        Display program execution info
        
        Args:
            program_name: Name of running program
            step_info: Info about current step (e.g., "Step 3/10")
        """
        self.display_mode = "message"
        line0 = program_name[:16]
        line1 = step_info[:16]
        self.update_display(line0, line1, force=True)
    
    def display_rotation_angle(self, angle):
        """
        Display current rotation angle
        
        Args:
            angle: Rotation angle in degrees
        """
        line0 = "Rotation"
        line1 = f"Angle: {angle:.1f}°"
        self.update_display(line0, line1)
    
    def display_intensity(self, intensity):
        """
        Display light intensity
        
        Args:
            intensity: Intensity percentage (0-100)
        """
        line0 = "Light Intensity"
        line1 = f"{intensity}%"
        self.update_display(line0, line1)
    
    def display_camera_status(self, camera_num, status):
        """
        Display camera trigger status
        
        Args:
            camera_num: Camera number (1 or 2)
            status: Status string ("Ready", "Triggered", etc.)
        """
        line0 = f"Camera {camera_num}"
        line1 = status[:16]
        self.update_display(line0, line1)
    
    def display_servo_position(self, servo_name, angle):
        """
        Display servo position
        
        Args:
            servo_name: Name of servo ("Table", "Cam1", "Cam2")
            angle: Current angle
        """
        line0 = f"{servo_name} Servo"
        line1 = f"Angle: {angle:.1f}°"
        self.update_display(line0, line1)
    
    def display_connection_status(self, connection_type, status):
        """
        Display connection status (BLE, Serial, etc.)
        
        Args:
            connection_type: "BLE", "Serial", etc.
            status: Status string ("Connected", "Waiting", etc.)
        """
        line0 = f"{connection_type}"
        line1 = status[:16]
        self.update_display(line0, line1, force=True)
    
    def display_memory_info(self, free_kb, total_kb):
        """
        Display memory usage
        
        Args:
            free_kb: Free memory in KB
            total_kb: Total memory in KB
        """
        line0 = "Memory Status"
        used_percent = 100 * (1 - free_kb / total_kb) if total_kb > 0 else 0
        line1 = f"{free_kb}KB {used_percent:.0f}% used"
        self.update_display(line0, line1)
    
    def display_progress_bar(self, title, progress_percent):
        """
        Display progress bar using character blocks
        
        Args:
            title: Title for line 0
            progress_percent: Progress percentage (0-100)
        """
        line0 = title[:16]
        
        # Create 16-character progress bar
        filled_chars = int(16 * progress_percent / 100)
        bar = "#" * filled_chars + "-" * (16 - filled_chars)
        line1 = bar
        
        self.update_display(line0, line1)
    
    def clear(self):
        """Clear display completely"""
        if self.lcd_available:
            self.lcd.clear()
            self.current_line0 = ""
            self.current_line1 = ""
    
    def set_update_interval(self, interval_ms):
        """
        Set minimum interval between display updates
        
        Args:
            interval_ms: Interval in milliseconds
        """
        self.update_interval_ms = max(50, interval_ms)  # Minimum 50ms
    
    # ========================================================================
    # COMPATIBILITY METHODS (Replace RP2040 5x5 matrix functions)
    # ========================================================================
    
    def show_single_char(self, char, duration_ms=1000):
        """
        Show single character (replaces matrix show_char)
        
        Args:
            char: Character to display
            duration_ms: Display duration
        """
        self.display_message(f"     {char}     ", "", duration_ms)
    
    def scroll_text(self, text, scroll_speed=300):
        """
        Scroll text across display (replaces matrix scroll)
        
        Args:
            text: Text to scroll
            scroll_speed: Speed in ms per character
        """
        # Add padding
        padded = "    " + text + "    "
        
        for i in range(len(padded) - 15):
            line0 = padded[i:i+16]
            self.update_display(line0, "", force=True)
            time.sleep_ms(scroll_speed)
    
    def show_animation(self, frames, frame_delay=200):
        """
        Show frame-by-frame animation
        
        Args:
            frames: List of (line0, line1) tuples
            frame_delay: Delay between frames in ms
        """
        for line0, line1 in frames:
            self.update_display(line0, line1, force=True)
            time.sleep_ms(frame_delay)


# ============================================================================
# TEST CODE
# ============================================================================

def test_display_manager():
    """Test suite for display manager"""
    print("\n" + "="*50)
    print("Display Manager Test Suite")
    print("="*50 + "\n")
    
    # Try to import LCD
    try:
        from machine import Pin, I2C
        from lcd_i2c import LCD1602
        
        # Initialize I2C and LCD
        i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        devices = i2c.scan()
        
        if devices:
            addr = 0x27 if 0x27 in devices else devices[0]
            lcd = LCD1602(i2c, addr)
            print(f"[TEST] LCD found at {hex(addr)}")
        else:
            print("[TEST] No LCD found - using None")
            lcd = None
    except Exception as e:
        print(f"[TEST] LCD init error: {e}")
        lcd = None
    
    # Create display manager
    dm = DisplayManager(lcd)
    
    if not dm.lcd_available:
        print("\n⚠ No LCD available - tests will run but nothing will display")
        return dm
    
    print("\n[TEST 1] Welcome Message")
    dm.display_welcome()
    time.sleep(2)
    
    print("\n[TEST 2] Status Display")
    for i in range(5):
        sim_time = 3600 + i * 300  # Start at 1 hour
        sim_speed = 60.0
        intensity = 75 + i * 5
        autoload = i % 2 == 0
        dm.display_status(sim_time, sim_speed, intensity, autoload)
        print(f"  Update {i+1}/5: Time={sim_time}s, Speed={sim_speed}x, I={intensity}%, AL={autoload}")
        time.sleep(1)
    
    print("\n[TEST 3] Message Display")
    dm.display_message("Test Message", "Line 2 Text", duration_ms=2000)
    
    print("\n[TEST 4] Error Display")
    dm.display_error("Test Error", "Details here")
    time.sleep(2)
    dm.clear_message()
    
    print("\n[TEST 5] Program Info")
    dm.display_program_info("TestProgram", "Step 3/10")
    time.sleep(2)
    
    print("\n[TEST 6] Rotation Angle")
    for angle in [0, 45, 90, 135, 180]:
        dm.display_rotation_angle(angle)
        print(f"  Angle: {angle}°")
        time.sleep(0.5)
    
    print("\n[TEST 7] Intensity")
    for intensity in [0, 25, 50, 75, 100]:
        dm.display_intensity(intensity)
        print(f"  Intensity: {intensity}%")
        time.sleep(0.5)
    
    print("\n[TEST 8] Camera Status")
    dm.display_camera_status(1, "Ready")
    time.sleep(1)
    dm.display_camera_status(1, "Triggered")
    time.sleep(1)
    
    print("\n[TEST 9] Connection Status")
    dm.display_connection_status("BLE", "Connecting...")
    time.sleep(1)
    dm.display_connection_status("BLE", "Connected")
    time.sleep(1)
    
    print("\n[TEST 10] Progress Bar")
    for progress in [0, 25, 50, 75, 100]:
        dm.display_progress_bar("Loading", progress)
        print(f"  Progress: {progress}%")
        time.sleep(0.5)
    
    print("\n[TEST 11] Scroll Text")
    dm.scroll_text("Solar Simulator ESP32-S3", scroll_speed=200)
    
    print("\n[TEST 12] Animation")
    frames = [
        ("Frame 1", "Animation"),
        ("Frame 2", "Test"),
        ("Frame 3", "Complete!"),
    ]
    dm.show_animation(frames, frame_delay=500)
    
    print("\n" + "="*50)
    print("All Display Tests Complete!")
    print("="*50 + "\n")
    
    dm.display_ready()
    time.sleep(2)
    dm.clear()
    
    return dm


if __name__ == "__main__":
    test_display_manager()
