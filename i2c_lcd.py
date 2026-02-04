# MicroPython I2C driver for 1602 LCD (PCF8574)
# Connect SDA to P18, SCL to P19 (I2C1)

from machine import I2C, Pin
import time

class I2cLcd:
    # LCD commands
    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_DISPLAY_CTRL = 0x08
    LCD_SHIFT = 0x10
    LCD_FUNCTION = 0x20
    LCD_CGRAM = 0x40
    LCD_DDRAM = 0x80

    # Flags
    LCD_ENTRY_LEFT = 0x02
    LCD_ENTRY_SHIFT_DECREMENT = 0x00
    LCD_DISPLAY_ON = 0x04
    LCD_CURSOR_OFF = 0x00
    LCD_BLINK_OFF = 0x00
    LCD_2LINE = 0x08
    LCD_5x8DOTS = 0x00
    LCD_4BIT_MODE = 0x00

    def __init__(self, i2c, addr, num_lines=2, num_columns=16):
        self.i2c = i2c
        self.addr = addr
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.backlight = 0x08
        self._init_lcd()

    def _write_byte(self, data):
        self.i2c.writeto(self.addr, bytes([data | self.backlight]))

    def _pulse(self, data):
        self._write_byte(data | 0x04)  # Enable bit
        time.sleep_us(1)
        self._write_byte(data & ~0x04)
        time.sleep_us(50)

    def _write4bits(self, data):
        self._write_byte(data)
        self._pulse(data)

    def _send(self, data, mode=0):
        high = data & 0xF0
        low = (data << 4) & 0xF0
        self._write4bits(high | mode)
        self._write4bits(low | mode)

    def command(self, cmd):
        self._send(cmd, 0)
        time.sleep_ms(2)

    def write(self, char):
        self._send(ord(char), 0x01)

    def putstr(self, string):
        for char in string:
            self.write(char)

    def clear(self):
        self.command(self.LCD_CLR)
        time.sleep_ms(2)

    def move_to(self, line, col):
        addr = col + (0x40 if line else 0x00)
        self.command(self.LCD_DDRAM | addr)

    def _init_lcd(self):
        time.sleep_ms(20)
        self._write4bits(0x30)
        time.sleep_ms(5)
        self._write4bits(0x30)
        time.sleep_us(100)
        self._write4bits(0x30)
        self._write4bits(0x20)
        self.command(self.LCD_FUNCTION | self.LCD_2LINE | self.LCD_5x8DOTS | self.LCD_4BIT_MODE)
        self.command(self.LCD_DISPLAY_CTRL | self.LCD_DISPLAY_ON | self.LCD_CURSOR_OFF | self.LCD_BLINK_OFF)
        self.command(self.LCD_CLR)
        self.command(self.LCD_ENTRY_MODE | self.LCD_ENTRY_LEFT | self.LCD_ENTRY_SHIFT_DECREMENT)
        time.sleep_ms(2)
