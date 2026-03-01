# SPDX-License-Identifier: GPL-3.0-or-later
import gc
gc.collect()

# CRITICAL: Initialize BLE BEFORE any large files are imported.
# Importing `simulator.py` fragments the heap because compiling 50KB of text
# on-device takes messy allocations. If the BLE radio initializes after
# fragmentation, the ESP32 throws a 'Guru Meditation Error' and bootloops.
from ble_comms import BLEComms
ble = BLEComms(name="SolarSim-BT")
gc.collect()

from hardware import Hardware
hw = Hardware()
gc.collect()

from simulator import SolarSimulator
sim = SolarSimulator(hw, ble)
ble.on_command = sim.handle_command
gc.collect()

sim.attempt_autoload()
gc.collect()

sim.run()
