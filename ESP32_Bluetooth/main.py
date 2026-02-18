"""
main.py — ESP32-S3 Solar Simulator Entry Point
=================================================
Wires together all modules and starts the simulation.
"""

import gc

gc.collect()
print(f"[BOOT] Free memory: {gc.mem_free()} bytes")

# Import modules
from hardware import Hardware
from ble_comms import BLEComms
from simulator import SolarSimulator


def main():
    """Initialize BLE, hardware, and start simulation."""
    print("=" * 40)
    print("  Solar Simulator — ESP32-S3")
    print("=" * 40)

    # 1. Initialize BLE communications FIRST — ensures device is
    #    discoverable even if hardware init fails downstream
    ble = BLEComms(name="SolarSim-BT")

    gc.collect()

    # 2. Initialize hardware (servos, NeoPixels, display, buttons)
    hw = Hardware()

    gc.collect()

    # 3. Create simulator with hardware and BLE
    sim = SolarSimulator(hw, ble)

    # 4. Wire BLE command callback to simulator
    ble.on_command = sim.handle_command

    gc.collect()
    print(f"[MAIN] Init complete. Free memory: {gc.mem_free()} bytes")

    # 5. Attempt auto-load of latest profile
    sim.attempt_autoload()

    gc.collect()

    # 6. Run simulation loop (never returns under normal operation)
    try:
        sim.run()
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.print_exception(e)
    finally:
        hw.shutdown()
        ble.stop()
        print("[MAIN] Shutdown complete.")


# Auto-start
main()
