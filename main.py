# min_christmas.py
# Minimal MicroPython NeoPixel ribbon controller for Christmas lights
# Features:
# - Button A (GP0): next pattern
# - Button B (GP1): previous pattern
# - 90 NeoPixels on GP15
# - 10 dynamic, smooth, christmassy patterns
# - Default: slow rainbow rotation
# - All patterns use intensity 50/255


import machine
import neopixel
import time
import math
import urandom

# --- 5x5 Matrix Display Setup (RP2040:bit) ---
# Pin mapping for RP2040:bit 5x5 matrix (adjust as needed)
MATRIX_COL_PINS = [2, 3, 4, 5, 25]  # GPIOs for columns (left to right)
MATRIX_ROW_PINS = [7, 8, 9, 21, 22] # GPIOs for rows (top to bottom)
matrix_col_pins = [machine.Pin(pin, machine.Pin.OUT) for pin in MATRIX_COL_PINS]
matrix_row_pins = [machine.Pin(pin, machine.Pin.OUT) for pin in MATRIX_ROW_PINS]

# 5x5 display buffer
matrix_buffer = [[0]*5 for _ in range(5)]

# Minimal 3-col wide font (5 pixels high)
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
}

def clear_matrix_buffer():
    for r in range(5):
        for c in range(5):
            matrix_buffer[r][c] = 0

def display_pattern_number(pattern_num):
    """Display the pattern number (0-9) in the leftmost 3 columns of the 5x5 matrix."""
    clear_matrix_buffer()
    digit = str(pattern_num % 10)
    if digit in FONT:
        for c in range(3):
            for r in range(5):
                matrix_buffer[r][c] = FONT[digit][c][r]

def update_heartbeat(now_ms):
    """Blink a pixel in the bottom-right as a heartbeat (1Hz)."""
    blink = (now_ms // 500) % 2
    matrix_buffer[4][4] = blink

def refresh_matrix_display():
    """Refresh the 5x5 LED matrix using POV."""
    for col in range(5):
        # Turn off all rows
        for row_pin in matrix_row_pins:
            row_pin.high()
        # Activate column
        matrix_col_pins[col].high()
        for row in range(5):
            if matrix_buffer[row][col]:
                matrix_row_pins[row].low()
            else:
                matrix_row_pins[row].high()
        time.sleep_us(2000)
        matrix_col_pins[col].low()

NUM_PIXELS = 90
PIXEL_PIN = 15
BRIGHTNESS = 150  # out of 255

# Button pins
BUTTON_A_PIN = 0
BUTTON_B_PIN = 1

# Setup
np = neopixel.NeoPixel(machine.Pin(PIXEL_PIN), NUM_PIXELS)
button_a = machine.Pin(BUTTON_A_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
button_b = machine.Pin(BUTTON_B_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

pattern = 0
num_patterns = 10
last_a = button_a.value()
last_b = button_b.value()

# Helper: scale color

def scale_color(rgb, scale):
    return tuple((c * scale) // 255 for c in rgb)

# Helper: wheel for rainbow

def color_wheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

# Pattern functions

def pattern_rainbow(offset):
    # Troubleshooting: Light first 5 pixels red at full brightness
    for i in range(NUM_PIXELS):
        if i < 5:
            np[i] = (255, 0, 0)
        else:
            np[i] = (0, 0, 0)
    np.write()

def pattern_candy_cane(offset):
    for i in range(NUM_PIXELS):
        if ((i + offset // 8) % 8) < 4:
            np[i] = (BRIGHTNESS, 0, 0)
        else:
            np[i] = (BRIGHTNESS, BRIGHTNESS, BRIGHTNESS)
    np.write()

def pattern_snow_twinkle(offset):
    import urandom
    for i in range(NUM_PIXELS):
        if urandom.getrandbits(2) == 0:
            np[i] = (BRIGHTNESS, BRIGHTNESS, BRIGHTNESS)
        else:
            np[i] = (0, 0, 0)
    np.write()

def pattern_green_wave(offset):
    for i in range(NUM_PIXELS):
        val = (int((1 + math.sin((i + offset / 3) * 0.2)) * 0.5 * BRIGHTNESS))
        np[i] = (0, val, 0)
    np.write()

def pattern_red_wave(offset):
    for i in range(NUM_PIXELS):
        val = (int((1 + math.sin((i + offset / 3) * 0.2)) * 0.5 * BRIGHTNESS))
        np[i] = (val, 0, 0)
    np.write()

def pattern_gold_sparkle(offset):
    import urandom
    for i in range(NUM_PIXELS):
        if urandom.getrandbits(3) == 0:
            np[i] = (BRIGHTNESS, BRIGHTNESS // 2, 0)
        else:
            np[i] = (0, 0, 0)
    np.write()

def pattern_festive_chase(offset):
    colors = [(BRIGHTNESS, 0, 0), (0, BRIGHTNESS, 0), (0, 0, BRIGHTNESS)]
    for i in range(NUM_PIXELS):
        np[i] = colors[((i + offset // 4) % 3)]
    np.write()

def pattern_blue_icicle(offset):
    for i in range(NUM_PIXELS):
        val = int((1 + math.sin((i + offset / 2) * 0.25)) * 0.5 * BRIGHTNESS)
        np[i] = (0, 0, val)
    np.write()

def pattern_red_green_fade(offset):
    for i in range(NUM_PIXELS):
        phase = (offset + i * 3) % 256
        r = int((1 + math.sin(phase * 2 * 3.14159 / 256)) * 0.5 * BRIGHTNESS)
        g = int((1 + math.cos(phase * 2 * 3.14159 / 256)) * 0.5 * BRIGHTNESS)
        np[i] = (r, g, 0)
    np.write()

def pattern_white_wave(offset):
    for i in range(NUM_PIXELS):
        val = int((1 + math.sin((i + offset / 2) * 0.18)) * 0.5 * BRIGHTNESS)
        np[i] = (val, val, val)
    np.write()

patterns = [
    pattern_rainbow,
    pattern_candy_cane,
    pattern_snow_twinkle,
    pattern_green_wave,
    pattern_red_wave,
    pattern_gold_sparkle,
    pattern_festive_chase,
    pattern_blue_icicle,
    pattern_red_green_fade,
    pattern_white_wave,
]

import math
import urandom


offset = 0
last_matrix_update = time.ticks_ms()


while True:
    # Button handling (debounce)
    a = button_a.value()
    b = button_b.value()
    if last_a == 1 and a == 0:
        pattern = (pattern + 1) % num_patterns
    if last_b == 1 and b == 0:
        pattern = (pattern - 1) % num_patterns
    last_a = a
    last_b = b

    # Run current pattern
    patterns[pattern](offset)
    offset = (offset + 1) % 1024

    # --- Matrix display update ---
    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, last_matrix_update) > 50:  # ~20Hz refresh
        display_pattern_number(pattern)
        update_heartbeat(now_ms)
        refresh_matrix_display()
        last_matrix_update = now_ms

    time.sleep(0.05)  # ~20 FPS, adjust for smoothness
