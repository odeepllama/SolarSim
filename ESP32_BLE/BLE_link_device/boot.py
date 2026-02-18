"""
boot.py - Runs on ESP32-S3 startup
======================================
Minimal boot configuration. Main code runs from main.py
"""

import gc
import esp
import machine

# Disable debug output for cleaner serial
esp.osdebug(None)

# Run garbage collection
gc.collect()

# Print boot message
print("\n" + "="*50)
print("   Solar Simulator ESP32-S3 - Boot")
print("="*50)

# Check reset cause
reset_cause = machine.reset_cause()
reset_causes = {
    machine.PWRON_RESET: "Power On",
    machine.HARD_RESET: "Hard Reset (button)",
    machine.WDT_RESET: "Watchdog Timeout",
    machine.DEEPSLEEP_RESET: "Deep Sleep Wake",
    machine.SOFT_RESET: "Soft Reset (Ctrl+D)"
}
print(f"Reset cause: {reset_causes.get(reset_cause, 'Unknown')}")

# Show system info
import sys
print(f"MicroPython: {sys.version}")
print(f"Platform: {sys.platform}")

# Memory info
print(f"Initial free memory: {gc.mem_free() // 1024} KB")

# Check for PSRAM
try:
    import esp32
    if hasattr(esp32, 'spiram_size'):
        psram_size = esp32.spiram_size()
        if psram_size > 0:
            print(f"PSRAM detected: {psram_size // 1024} KB")
        else:
            print("No PSRAM detected")
except:
    print("PSRAM check not available")

print("="*50)
print("Loading main.py...")
print("="*50 + "\n")
