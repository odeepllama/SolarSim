[Link to RP2040:bit board page](https://spotpear.com/index/study/detail/id/943.html)

[Link to Bill Of Materials (BOM)](https://docs.google.com/spreadsheets/d/1aQhFblNy1jl5k1DLb-90Tq7NmfreDscm0g0mmVD8wfg/edit?usp=sharing)

Resources needed (cameras, servos, soldering iron, cables, connectors, LED matrix panels)

(Bluetooth cell phone trigger?)

[Link to Video Walkthrough] (comign soon!)

Also need to share .stl / .3mf / .step files

Notes:

Could use a "Simple Mode"
Check profile examples
(Disbale button when not "Running on Device")


Hit disconnect to edit from current loaded program/profile

Immediate concerns:

Still some issues jump between steps and days - need a review/refresh of this area of the code (get sonnet's understanding and then rationalization/simplification/implementation)

Background colour to identify device (if 2 or more are connected)

Make Program control 5 columns wide and thus shrink down the Pogram enabled and Program repeats entries

Stripped down version for the first time user

To do:

The playhead navigation buttons (prev and next) for both step and day are basically working, but there's a issue whereby I cannot get back to the previous stap if it is on the rpeviousl day. For example, I cannto get the playhead to jump to Day 1 from Day 2 using the Prev Step button. However, the next step button can take the playhead correctly from Day 1 to Day 2. Please carefully look into this issue and see fi you can propose an efficient solution that doesn't break anything.