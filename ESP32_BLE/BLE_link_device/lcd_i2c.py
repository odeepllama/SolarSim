"""
I2C LCD 1602 Driver for ESP32
==============================
Driver for 16x2 character LCD with PCF8574 I2C backpack

Typical I2C addresses: 0x27 or 0x3F

Wiring:
- SDA: GPIO21 (default)
- SCL: GPIO22 (default)
- VCC: 5V
- GND: GND
"""

from machine import I2C, Pin
from time import sleep_ms

# LCD Commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# Flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# Flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# Flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# Flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# Flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00

# PCF8574 pin mapping
En = 0b00000100  # Enable bit
Rw = 0b00000010  # Read/Write bit
Rs = 0b00000001  # Register select bit


class LCD1602:
    """I2C LCD 1602 Display Driver"""
    
    def __init__(self, i2c, addr=0x27, rows=2, cols=16):
        """
        Initialize LCD display
        
        Args:
            i2c: I2C object
            addr: I2C address (0x27 or 0x3F typically)
            rows: Number of rows (default 2)
            cols: Number of columns (default 16)
        """
        self.i2c = i2c
        self.addr = addr
        self.rows = rows
        self.cols = cols
        self.backlight_state = LCD_BACKLIGHT
        
        # Initialize display
        self._init_display()
        
    def _init_display(self):
        """Initialize LCD in 4-bit mode"""
        sleep_ms(50)  # Wait for LCD to power up
        
        # Put LCD into 4-bit mode (HD44780 initialization sequence)
        self._write_four_bits(0x03 << 4)
        sleep_ms(5)
        self._write_four_bits(0x03 << 4)
        sleep_ms(5)
        self._write_four_bits(0x03 << 4)
        sleep_ms(1)
        self._write_four_bits(0x02 << 4)  # Switch to 4-bit mode
        
        # Configure display
        self._write_cmd(LCD_FUNCTIONSET | LCD_4BITMODE | LCD_2LINE | LCD_5x8DOTS)
        self._write_cmd(LCD_DISPLAYCONTROL | LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF)
        self.clear()
        self._write_cmd(LCD_ENTRYMODESET | LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT)
        sleep_ms(2)
        
    def _write_four_bits(self, data):
        """Write 4 bits to I2C expander"""
        data = data | self.backlight_state
        self.i2c.writeto(self.addr, bytes([data]))
        self._pulse_enable(data)
        
    def _pulse_enable(self, data):
        """Pulse the Enable pin to latch data"""
        self.i2c.writeto(self.addr, bytes([data | En]))
        sleep_ms(1)
        self.i2c.writeto(self.addr, bytes([data & ~En]))
        sleep_ms(1)
        
    def _write_cmd(self, cmd):
        """Write command to LCD"""
        # Send high nibble
        self._write_four_bits(cmd & 0xF0)
        # Send low nibble
        self._write_four_bits((cmd << 4) & 0xF0)
        
    def _write_data(self, data):
        """Write data to LCD"""
        # Send high nibble with RS high
        self._write_four_bits((data & 0xF0) | Rs)
        # Send low nibble with RS high
        self._write_four_bits(((data << 4) & 0xF0) | Rs)
        
    def clear(self):
        """Clear display"""
        self._write_cmd(LCD_CLEARDISPLAY)
        sleep_ms(2)
        
    def home(self):
        """Return cursor to home position"""
        self._write_cmd(LCD_RETURNHOME)
        sleep_ms(2)
        
    def set_cursor(self, col, row):
        """
        Set cursor position
        
        Args:
            col: Column (0-15)
            row: Row (0-1)
        """
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row >= self.rows:
            row = self.rows - 1
        self._write_cmd(LCD_SETDDRAMADDR | (col + row_offsets[row]))
        
    def write_char(self, char):
        """Write a single character"""
        self._write_data(ord(char))
        
    def write(self, text):
        """
        Write text to current cursor position
        
        Args:
            text: String to display (will be truncated to fit)
        """
        for char in text:
            self._write_data(ord(char))
            
    def print(self, text, col=0, row=0):
        """
        Print text at specific position
        
        Args:
            text: String to display
            col: Starting column
            row: Row number
        """
        self.set_cursor(col, row)
        self.write(text)
        
    def backlight_on(self):
        """Turn backlight on"""
        self.backlight_state = LCD_BACKLIGHT
        self.i2c.writeto(self.addr, bytes([self.backlight_state]))
        
    def backlight_off(self):
        """Turn backlight off"""
        self.backlight_state = LCD_NOBACKLIGHT
        self.i2c.writeto(self.addr, bytes([self.backlight_state]))
        
    def display_on(self):
        """Turn display on"""
        self._write_cmd(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
        
    def display_off(self):
        """Turn display off"""
        self._write_cmd(LCD_DISPLAYCONTROL | LCD_DISPLAYOFF)
        
    def display_status(self, time_str, speed, intensity, autoload):
        """
        Display Solar Simulator status (convenience method)
        
        Args:
            time_str: Time string (e.g., "12:34")
            speed: Speed multiplier (e.g., "6X", "HOLD")
            intensity: Intensity scale (float)
            autoload: Auto-load enabled (bool)
        """
        # Line 1: Time and Speed
        line1 = f"{time_str:5s} {speed:>6s}"
        self.print(line1.ljust(16), 0, 0)
        
        # Line 2: Intensity and Auto-load status
        al_status = "AL:ON" if autoload else "AL:OF"
        line2 = f"I:{intensity:4.2f} {al_status:>5s}"
        self.print(line2.ljust(16), 0, 1)


# Test/Example usage
if __name__ == "__main__":
    from machine import I2C, Pin
    import time
    
    # Initialize I2C (adjust pins if needed)
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    
    # Scan for I2C devices
    print("Scanning I2C bus...")
    devices = i2c.scan()
    if devices:
        print(f"Found I2C devices at: {[hex(d) for d in devices]}")
    else:
        print("No I2C devices found!")
        
    # Try common LCD addresses
    lcd_addr = 0x27  # Try 0x3F if this doesn't work
    
    try:
        # Initialize LCD
        lcd = LCD1602(i2c, lcd_addr)
        print(f"LCD initialized at address {hex(lcd_addr)}")
        
        # Test display
        lcd.clear()
        lcd.print("SolarSim ESP32", 0, 0)
        lcd.print("BLE Ready!", 0, 1)
        time.sleep(2)
        
        # Test status display
        lcd.clear()
        lcd.display_status("12:34", "6X", 1.0, True)
        time.sleep(2)
        
        # Animation test
        lcd.clear()
        for i in range(16):
            lcd.print(">" * (i + 1), 0, 0)
            time.sleep(0.1)
            
        # Backlight test
        for _ in range(3):
            lcd.backlight_off()
            time.sleep(0.3)
            lcd.backlight_on()
            time.sleep(0.3)
            
        lcd.clear()
        lcd.print("Test Complete!", 0, 0)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Check wiring and I2C address (try 0x27 or 0x3F)")
