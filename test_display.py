# MicroPython script for scrolling text on I2C display (RP2040:bit)
# Assumes SSD1306 OLED display (128x64 or 128x32)
# SDA: P18, SCL: P19

from machine import Pin, I2C
import time
from i2c_lcd import I2cLcd

# Set up I2C (use I2C1 for RP2040:bit)
i2c = I2C(1, scl=Pin(19), sda=Pin(18))
LCD_ADDR = 0x27
# Init LCD
lcd = I2cLcd(i2c, LCD_ADDR, 2, 16)
lcd.clear()

# Texts to scroll
text1 = "line 1--------->"
text2 = "<---------line 2"

while True:
    # Scroll line 1 left to right
    for i in range(-15, len(text1)):
        lcd.move_to(0, 0)
        lcd.putstr(" " * max(0, i) + text1[max(0, -i):][:16])
        # Scroll line 2 right to left
        lcd.move_to(1, 0)
        j = len(text2) - i - 1
        line2 = text2[max(0, j):][:16]
        # Pad line2 to 16 chars with spaces on the left
        line2_padded = ' ' * (16 - len(line2)) + line2
        lcd.putstr(line2_padded)
        time.sleep(0.2)
