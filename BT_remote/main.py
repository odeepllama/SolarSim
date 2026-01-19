import machine
import time

# This script triggers the shutter of a BT-connected camera
# when Button A is pressed, then released.
button_a = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
trigger_pin = machine.Pin(14, machine.Pin.OUT)
trigger_pin.value(1)  # Camera shutter idle state is HIGH

print("Ready: Press, then release Button A to trigger the camera shutter (pin 14 LOW for 50ms).")

last_state = button_a.value()

while True:
    current_state = button_a.value()
    # Detect rising edge: Button A pressed, then released (from 0 to 1)
    if last_state == 0 and current_state == 1:
        print("Button A released! Triggering camera shutter (pin 14 LOW for 50ms).")
        trigger_pin.value(0)
        time.sleep_ms(10)
        trigger_pin.value(1)
    last_state = current_state
    time.sleep_ms(10)