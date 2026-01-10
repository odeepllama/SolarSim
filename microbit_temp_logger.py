from microbit import *
import time

# Initialize Serial (UART)
# 115200 is the standard baud rate for Web Serial with micro:bit
uart.init(baudrate=115200)

# Show a happy face to indicate the script is running
display.show(Image.HAPPY)

while True:
    # Get temperature in Celsius
    temp = temperature()
    
    # Send to serial console (adds a newline automatically)
    print(temp)
    
    # Wait 1 second (1000 milliseconds)
    sleep(1000)
