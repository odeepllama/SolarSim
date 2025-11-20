# SolarSimulatorUpdatedHelp.py
# This file contains the updated help output for serial commands in SolarSimulator.
# Original logic and all other code is unchanged except for the help output section.

# ...existing code up to help output...

        elif command == "help" and len(parts) > 1 and parts[1] == "all":
            print("--- Command Summary ---")
            print("Set: autoload [on|off], cameralightingpanels [on|off], date [YYYYMMDD], degrees_per_image [deg], imageatnight [on|off], images_per_rotation [int], intensity [0-255], latitude [deg], rot_inc_deg [deg], rot_speed [deg/s], rot_step_intv [ms], rot_stills_intv [ms], rot_trig_hold [ms], rotationatnight [on|off], rotationcameraservo [on|off], rotationinterval [s], rotationmode [auto|manual], solarmode [auto|manual], speed [scale], starttime [HHMM], suncolor [r,g,b], time [HHMM], servo2interval [ms], servo3interval [ms]")
            print("Toggle: dualsun [on|off], program [on|off], restartafterload [on|off], servo2 [on|off], servo3 [on|off], 1to1ratio [on|off]")
            print("Program/Manual: jump nextstep, jump step, listprofiles, loadprofile <file>, profiledelete <file>, saveprofile <file>, savelog <file>, status, trigger servo2, trigger servo3, trigger rotation")
            print("Utility: fillpanel [r,g,b], light camera [on|off], light rotation [on|off], reset, restart, help")
            print("-----------------------")

# ...existing code after help output...
