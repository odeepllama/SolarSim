# SPDX-License-Identifier: GPL-3.0-or-later
"""
boot.py — ESP32-S3 Boot Configuration
========================================
Runs before main.py on every reset/power-on.
"""

import gc
import esp

# Keep OS-level debug output ENABLED so Guru Meditation
# backtraces are visible on UART0 for crash diagnosis.
# Use esp.osdebug(0) to send to UART0 (default serial).
# Previously this was esp.osdebug(None) which suppressed
# all crash diagnostics, making boot failures invisible.
esp.osdebug(0)

# Run garbage collection early
gc.collect()
