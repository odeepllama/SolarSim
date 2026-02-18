"""
boot.py — ESP32-S3 Boot Configuration
========================================
Runs before main.py on every reset/power-on.
"""

import gc
import esp

# Disable OS-level debug output to keep REPL clean
esp.osdebug(None)

# Run garbage collection early
gc.collect()
