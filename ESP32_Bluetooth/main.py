import gc
gc.collect()
from hardware import Hardware
from ble_comms import BLEComms
from simulator import SolarSimulator
gc.collect()
ble = BLEComms(name="SolarSim-BT")
gc.collect()
hw = Hardware()
gc.collect()
sim = SolarSimulator(hw, ble)
ble.on_command = sim.handle_command
gc.collect()
sim.attempt_autoload()
gc.collect()
sim.run()
