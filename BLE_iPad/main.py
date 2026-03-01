# SPDX-License-Identifier: GPL-3.0-or-later
import gc
gc.collect()

from hardware import Hardware
hw = Hardware()
gc.collect()

from simulator import SolarSimulator
sim = SolarSimulator(hw)
gc.collect()

sim.attempt_autoload()
gc.collect()

sim.run()

