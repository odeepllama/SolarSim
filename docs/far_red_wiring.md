# Far-Red LED Array Wiring (Optional)

The far-red (FR) LED array is an **optional** add-on for phototropism and phytochrome experiments. It delivers a saturating 730 nm pulse to drive Pfr → Pr photoconversion before an experiment, then switches off so a normal white/RGB program can begin.

If you don't run phototropism experiments, you don't need this array — SolaSim runs fine without it.

---

## Bill of Materials (5-LED, 12V single-string build)

Sized for single-plant benchtop use on a shared 12V rail. See the [full parts list (Bill of Materials)](https://shorturl.at/ypCK8) for links to specific suppliers.

| Item | Qty | Notes |
|---|---|---|
| **3W 730 nm FR LED** (3535 die on 16 mm aluminium PCB) | 5 | Series-chained. `+` pad = anode, `−` pad = cathode. |
| **Mean Well LDD-700H** LED driver | 1 | Buck constant-current driver, 700 mA output, 3.3 V DIM input works natively. |
| 220 µF 35 V electrolytic capacitor | 1 | Across VIN+/VIN− for input smoothing. |
| **12 V DC power supply**, 1 A minimum | 1 | 2 A recommended for headroom. Barrel-jack wall adapter is fine. |
| 22 AWG silicone hookup wire | ~1 m | LED-to-LED jumpers and driver connections. |
| Heat shrink tubing | assorted | Insulate every exposed solder joint. |
| Optional: DC barrel jack + inline switch | 1 | Convenience for bench use. |

**Power budget:** 5 LEDs × ~2 V × 700 mA ≈ 7 W at the string; ≈0.6 A draw from the 12 V rail. A 12 V / 1 A supply is sufficient; 12 V / 2 A gives comfortable headroom.

---

## Why 5 LEDs at 12V

The LDD-700H is a **step-down** (buck) driver: VOUT must sit at least ~1 V below VIN. On a 12 V rail this caps the string at ~11 V total forward voltage → **5 LEDs @ 2.0–2.2 V** each is the sweet spot (uses one driver, one supply, minimum parts).

If you have a 24 V rail available and want higher fluence, use the dual-string 20-LED build documented in the PlantSense repo (link at bottom).

---

## Wiring

```
        12V DC POWER SUPPLY
           (+12V)  (GND)
             │       │
             │  ┌────┤   C1: 220µF 35V (close to LDD input)
             │  └────┤
             │       │
     ┌───────┴───────┴───────┐
     │      LDD-700H         │
     │      (buck CC)        │
  ──▶│ VIN+                  │
  ──▶│ VIN−                  │
GPIO▶│ DIM  (3.3V logic OK)  │  HIGH = on, LOW = off, PWM = dim
     │ VOUT+ ─────► LED1(+)  │
     │ VOUT− ◄──── LED5(−)   │
     └───────────────────────┘

  LEDs in series, anode(+) → cathode(−) → next anode(+) → … :
   VOUT+ ─► +LED1− ─► +LED2− ─► +LED3− ─► +LED4− ─► +LED5− ─► VOUT−
```

**Key points:**

- Single constant-current loop — the LDD-700H regulates 700 mA regardless of exact Vf.
- **Polarity is critical.** One backwards LED and nothing lights. `+` pad = anode = current in; `−` pad = cathode = current out.
- 12 V supply GND and the microcontroller GND must be **connected** — the DIM signal needs a common reference.

---

## LDD-700H pin colours

Mean Well's typical colour code (confirm against the datasheet packed with your unit):

| Pin | Colour (typical) | Connect to |
|---|---|---|
| VIN+ | Red | 12 V supply (+) |
| VIN− | Black | 12 V supply (−) / GND |
| DIM | White | MCU GPIO (3.3 V logic) |
| VOUT+ | Blue | LED 1 anode (+) |
| VOUT− | Yellow | LED 5 cathode (−) |

---

## SolaSim wiring pin

Wired to **GP13** on the RP2040:bit, which routes to micro:bit edge pin **P16** through a Keyestudio KS0360 (or similar) sensor shield. The 3.3 V logic level is well within the LDD-700H DIM range (0.3–5 V). No level shifter needed.

Firmware handling and profile fields (`FR_PREEXPOSURE_TRIGGER`, `FR_PREEXPOSURE_MINUTES`) are documented in the SolaSimStudio in-app Help panel under *Settings & Configuration → Far-Red (FR) Pre-Exposure*.

Manual serial commands:

```
fr on          # drive GP13 HIGH — LEDs on until 'fr off' (bench debug, no time freeze)
fr off         # drive GP13 LOW — also aborts any pulse / pre-exposure in progress
fr pulse 5     # 5-minute dark treatment (freezes sim time, blanks sun panel, resumes)
```

---

## Authoritative source

This is a condensed reference. The full build doc — including safety notes, LED die placement details, alternative 24 V / 20-LED build, and photobiology background — lives in the sibling PlantSense repo:

- `PlantSense/FR_Wiring_5LED_12V.md` — 5-LED, 12 V single-string (this build)
- `PlantSense/FR_Wiring.md` — 20-LED, 24 V dual-string (larger arrays)
