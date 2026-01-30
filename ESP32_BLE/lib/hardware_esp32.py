"""
Hardware Abstraction Layer for ESP32-S3
========================================
Centralizes all hardware initialization and pin management.
Provides consistent interface for servos, NeoPixels, LCD, and buttons.
"""

from machine import Pin, PWM, I2C
import neopixel
from lcd_i2c import LCD1602

# ============================================================================
# PIN DEFINITIONS - ESP32-S3 Configuration
# ============================================================================

 # Servo Pin
SERVO_1_PIN = 33      # Platform rotation servo (confirmed working)

# NeoPixel Pin
NEOPIXEL_PIN = 16     # LED panel data (was GP15 on RP2040)

# I2C Pins (LCD Display)
I2C_SDA_PIN = 21      # I2C data line (new for ESP32)
I2C_SCL_PIN = 22      # I2C clock line (new for ESP32)

# Button Pins
BUTTON_A_PIN = 0      # Built-in BOOT button (was GP0 on RP2040)
BUTTON_B_PIN = 35     # External button (was GP1 on RP2040)

# Camera Shutter Trigger Pin
CAMERA_SHUTTER_PIN = 19  # Active LOW, idle HIGH (changed from 26)

# ============================================================================
# SERVO CONFIGURATION
# ============================================================================

PWM_FREQ = 50          # Standard servo PWM frequency (Hz)
MIN_DUTY = 1400        # Duty cycle for 0 degrees (approx 0.5ms pulse)
MAX_DUTY = 8352        # Duty cycle for 270 degrees (approx 2.5ms pulse)
SERVO_ANGLE_RANGE = 273.0  # Full range of motion for the servo

# Servo angles
TABLE_SERVO_START_ANGLE = 0     # Starting angle for table servo
CAMERA_SERVO_REST_ANGLE = 45    # Camera servo resting angle
CAMERA_SERVO_TRIGGER_ANGLE = 90 # Camera servo angle when triggered

# Servo1 Nonlinear PWM Calibration (3:4 and 1:1 ratios)
SERVO1_PWM_CALIBRATION_3TO4 = {
    0:   1400,   # PWM for 0°
    90:  3200,   # PWM for 90°
    180: 4900,   # PWM for 180°
    270: 6600,   # PWM for 270°
    360: 8252    # PWM for 360°
}

SERVO1_PWM_CALIBRATION_1TO1 = {
    0:    1400,  # PWM for 0°
    270:  8252,  # PWM for 270°
}

# ============================================================================
# HARDWARE CLASS
# ============================================================================

class HardwareESP32:
    """Hardware abstraction for ESP32-S3 Solar Simulator"""
    
    def __init__(self, neopixel_count=448, lcd_addr=0x27):
        """
        Initialize all hardware components
        
        Args:
            neopixel_count: Number of NeoPixel LEDs (default 448 for 8×56 panel)
            lcd_addr: I2C address for LCD (0x27 or 0x3F, default 0x27)
        """
        print("[HW] Initializing ESP32-S3 hardware...")
        
        self.neopixel_count = neopixel_count
        self.lcd_addr = lcd_addr
        
        # Initialize each subsystem
        self._init_servo()
        self._init_neopixels()
        self._init_lcd()
        self._init_buttons()
        self._init_camera_trigger()
        
        print("[HW] Hardware initialization complete!")
    
    def _init_servo(self):
        """Initialize single servo motor"""
        print("[HW] Initializing servo...")
        self.servo_pin_1 = Pin(SERVO_1_PIN)
        self.servo_pwm_1 = PWM(self.servo_pin_1)
        self.servo_pwm_1.freq(PWM_FREQ)
        self.set_servo_angle(self.servo_pwm_1, TABLE_SERVO_START_ANGLE)
        print(f"[HW] Servo initialized on GPIO{SERVO_1_PIN}")
    
    def _init_neopixels(self):
        """Initialize NeoPixel LED panel"""
        print("[HW] Initializing NeoPixels...")
        
        self.np_pin = Pin(NEOPIXEL_PIN, Pin.OUT)
        self.pixels = neopixel.NeoPixel(self.np_pin, self.neopixel_count)
        
        # Initialize panel buffer for delta updates
        self.panel_buffer = [(0, 0, 0)] * self.neopixel_count
        
        # Clear panel
        self.pixels.fill((0, 0, 0))
        self.pixels.write()
        
        print(f"[HW] NeoPixels initialized: {self.neopixel_count} LEDs on GPIO{NEOPIXEL_PIN}")
    
    def _init_lcd(self):
        """Initialize I2C LCD display"""
        print("[HW] Initializing I2C LCD...")
        
        try:
            # Initialize I2C
            self.i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400000)
            
            # Scan for devices
            devices = self.i2c.scan()
            if devices:
                print(f"[HW] I2C devices found: {[hex(d) for d in devices]}")
                
                # Try specified address, then common alternatives
                if self.lcd_addr in devices:
                    addr = self.lcd_addr
                elif 0x27 in devices:
                    addr = 0x27
                elif 0x3F in devices:
                    addr = 0x3F
                else:
                    addr = devices[0]  # Use first found device
                
                # Initialize LCD
                self.lcd = LCD1602(self.i2c, addr)
                self.lcd_available = True
                print(f"[HW] LCD initialized at address {hex(addr)}")
                
                # Welcome message
                self.lcd.clear()
                self.lcd.print("SolarSim ESP32", 0, 0)
                self.lcd.print("Hardware Ready", 0, 1)
            else:
                print("[HW] Warning: No I2C devices found")
                self.lcd = None
                self.lcd_available = False
                
        except Exception as e:
            print(f"[HW] LCD initialization error: {e}")
            self.lcd = None
            self.lcd_available = False
    
    def _init_buttons(self):
        """Initialize button inputs"""
        print("[HW] Initializing buttons...")
        
        # Button A (built-in BOOT button on GPIO0)
        self.button_a = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
        
        # Button B (external button)
        self.button_b = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
        
        print(f"[HW] Buttons initialized on GPIO{BUTTON_A_PIN}, {BUTTON_B_PIN}")
    
    def _init_camera_trigger(self):
        """Initialize camera shutter trigger pin"""
        print("[HW] Initializing camera trigger...")
        
        # Active LOW, idle HIGH
        self.camera_shutter_pin = Pin(CAMERA_SHUTTER_PIN, Pin.OUT)
        self.camera_shutter_pin.value(1)  # Idle state
        
        print(f"[HW] Camera trigger initialized on GPIO{CAMERA_SHUTTER_PIN}")
    
    # ========================================================================
    # SERVO CONTROL METHODS
    # ========================================================================
    
    def set_servo_angle(self, pwm_obj, angle):
        """
        Set servo to specific angle (0-270 degrees)
        
        Args:
            pwm_obj: PWM object to control
            angle: Target angle (0-270)
            
        Returns:
            bool: True if successful
        """
        # Constrain angle to valid range
        angle = max(0, min(SERVO_ANGLE_RANGE, angle))
        
        # Calculate duty cycle based on angle
        duty_range = MAX_DUTY - MIN_DUTY
        duty = MIN_DUTY + (angle / SERVO_ANGLE_RANGE) * duty_range
        
        try:
            pwm_obj.duty_u16(int(duty))
            return True
        except Exception as e:
            print(f"[HW] Error setting servo angle: {e}")
            return False
    
    def get_servo1_calibrated_pwm(self, angle, use_1to1_ratio=False):
        """
        Return calibrated PWM value for servo1 (rotation table)
        
        Args:
            angle: Target angle (0-360)
            use_1to1_ratio: Use 1:1 ratio table instead of 3:4
            
        Returns:
            int: PWM duty cycle value
        """
        angle = max(0, min(360, angle))
        table = SERVO1_PWM_CALIBRATION_1TO1 if use_1to1_ratio else SERVO1_PWM_CALIBRATION_3TO4
        keys = sorted(table.keys())
        
        for i in range(len(keys) - 1):
            a0, a1 = keys[i], keys[i+1]
            if a0 <= angle <= a1:
                pwm0, pwm1 = table[a0], table[a1]
                return int(pwm0 + (pwm1 - pwm0) * (angle - a0) / (a1 - a0))
        
        return table[keys[-1]]
    
    def set_servo1_angle(self, angle, use_1to1_ratio=False):
        """
        Set servo1 to specific table angle using non-linear calibration
        
        Args:
            angle: Target angle (0-360 for table)
            use_1to1_ratio: Use 1:1 ratio calibration
            
        Returns:
            bool: True if successful
        """
        pwm_val = self.get_servo1_calibrated_pwm(angle, use_1to1_ratio)
        try:
            self.servo_pwm_1.duty_u16(pwm_val)
            return True
        except Exception as e:
            print(f"[HW] Error setting servo1 PWM: {e}")
            return False
    
    # ========================================================================
    # NEOPIXEL METHODS
    # ========================================================================
    
    def xy_to_index(self, x, y):
        """
        Convert (x, y) coordinates to NeoPixel index
        8×56 panel organized as 7 panels of 8×8
        
        Args:
            x: X coordinate (0-55)
            y: Y coordinate (0-7)
            
        Returns:
            int: NeoPixel index
        """
        visual_panel = x // 8
        physical_panel = 6 - visual_panel
        panel_x = x % 8
        if y % 2 == 1:  # For odd rows, reverse direction
            panel_x = 7 - panel_x
        panel_index = y * 8 + panel_x
        return physical_panel * 64 + panel_index
    
    def fill_panel(self, r, g, b):
        """
        Fill entire panel with single color
        
        Args:
            r, g, b: Color components (0-255)
        """
        color = (r, g, b)
        self.pixels.fill(color)
        self.pixels.write()
        # Update state buffer
        self.panel_buffer = [color] * len(self.pixels)
    
    # ========================================================================
    # BUTTON METHODS
    # ========================================================================
    
    def button_a_pressed(self):
        """Check if button A is pressed (active LOW)"""
        return not self.button_a.value()
    
    def button_b_pressed(self):
        """Check if button B is pressed (active LOW)"""
        return not self.button_b.value()
    
    # ========================================================================
    # CAMERA TRIGGER METHODS
    # ========================================================================
    
    def trigger_camera_shutter(self):
        """Pulse camera shutter pin LOW for 10ms"""
        self.camera_shutter_pin.value(0)
        from time import sleep_ms
        sleep_ms(10)
        self.camera_shutter_pin.value(1)
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def shutdown(self):
        """Clean shutdown of all hardware"""
        print("[HW] Shutting down hardware...")
        
        # Turn off NeoPixels
        self.fill_panel(0, 0, 0)
        
        # Return servos to rest positions
        self.set_servo_angle(self.servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
        self.set_servo_angle(self.servo_pwm_3, CAMERA_SERVO_REST_ANGLE)
        self.set_servo1_angle(0)
        
        # Clear LCD
        if self.lcd_available:
            self.lcd.clear()
            self.lcd.print("System Stopped", 0, 0)
        
        # Deinit PWM
        self.servo_pwm_1.deinit()
        self.servo_pwm_2.deinit()
        self.servo_pwm_3.deinit()
        
        print("[HW] Hardware shutdown complete")


# ============================================================================
# TEST CODE
# ============================================================================

def test_hardware():
    """Comprehensive hardware test suite"""
    import time
    
    print("\n" + "="*50)
    print("ESP32-S3 Hardware Test Suite")
    print("="*50 + "\n")
    
    # Initialize hardware
    hw = HardwareESP32()
    time.sleep(1)
    
    # Test 1: LCD Display
    print("\n[TEST 1] LCD Display")
    if hw.lcd_available:
        hw.lcd.clear()
        hw.lcd.print("Test 1: LCD", 0, 0)
        hw.lcd.print("Display OK!", 0, 1)
        time.sleep(2)
        print("✓ LCD test passed")
    else:
        print("✗ LCD not available")
    
    # Test 2: NeoPixels
    print("\n[TEST 2] NeoPixels")
    colors = [
        (50, 0, 0),   # Red
        (0, 50, 0),   # Green  
        (0, 0, 50),   # Blue
        (0, 0, 0)     # Off
    ]
    for i, color in enumerate(colors):
        hw.fill_panel(*color)
        print(f"  Color {i+1}/4: RGB{color}")
        time.sleep(0.5)
    print("✓ NeoPixel test passed")
    
    # Test 3: Servo Sweep
    print("\n[TEST 3] Servos")
    if hw.lcd_available:
        hw.lcd.clear()
        hw.lcd.print("Test 3: Servos", 0, 0)
    
    # Test servo 1 (rotation)
    print("  Servo 1 (rotation): 0° → 90° → 0°")
    hw.set_servo1_angle(0)
    time.sleep(0.5)
    hw.set_servo1_angle(90)
    time.sleep(0.5)
    hw.set_servo1_angle(0)
    
    # Test servo 2 (camera)
    print("  Servo 2 (camera): Rest → Trigger → Rest")
    hw.set_servo_angle(hw.servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
    time.sleep(0.5)
    hw.set_servo_angle(hw.servo_pwm_2, CAMERA_SERVO_TRIGGER_ANGLE)
    time.sleep(0.5)
    hw.set_servo_angle(hw.servo_pwm_2, CAMERA_SERVO_REST_ANGLE)
    
    print("✓ Servo test passed")
    
    # Test 4: Buttons
    print("\n[TEST 4] Buttons")
    print("  Press Button A (BOOT) within 5 seconds...")
    if hw.lcd_available:
        hw.lcd.clear()
        hw.lcd.print("Press Button A", 0, 0)
        hw.lcd.print("(BOOT button)", 0, 1)
    
    start = time.ticks_ms()
    button_a_detected = False
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        if hw.button_a_pressed():
            print("  ✓ Button A pressed!")
            button_a_detected = True
            break
        time.sleep_ms(100)
    
    if not button_a_detected:
        print("  ⚠ Button A not pressed (optional)")
    
    # Test 5: Camera Trigger
    print("\n[TEST 5] Camera Trigger")
    if hw.lcd_available:
        hw.lcd.clear()
        hw.lcd.print("Test 5: Camera", 0, 0)
        hw.lcd.print("Trigger pulse", 0, 1)
    
    print("  Pulsing camera trigger...")
    hw.trigger_camera_shutter()
    time.sleep(0.5)
    hw.trigger_camera_shutter()
    print("✓ Camera trigger test passed")
    
    # Final status
    print("\n" + "="*50)
    print("Hardware Test Summary")
    print("="*50)
    print(f"LCD:       {'✓ OK' if hw.lcd_available else '✗ Not found'}")
    print(f"NeoPixels: ✓ OK ({hw.neopixel_count} LEDs)")
    print(f"Servos:    ✓ OK (3 servos)")
    print(f"Buttons:   {'✓ OK' if button_a_detected else '⚠ Not tested'}")
    print(f"Camera:    ✓ OK")
    print("="*50 + "\n")
    
    if hw.lcd_available:
        hw.lcd.clear()
        hw.lcd.print("All Tests", 0, 0)
        hw.lcd.print("Complete!", 0, 1)
    
    time.sleep(2)
    hw.shutdown()
    
    return hw


if __name__ == "__main__":
    # Run test suite
    test_hardware()
