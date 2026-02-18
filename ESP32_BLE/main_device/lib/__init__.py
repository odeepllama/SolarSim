"""
ESP32 Solar Simulator Library
==============================
Hardware abstraction and display management for ESP32-S3
"""

from .hardware_esp32 import HardwareESP32
from .display_manager import DisplayManager

__version__ = "1.0.0"
__all__ = ["HardwareESP32", "DisplayManager"]
