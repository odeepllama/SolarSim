# Advanced Lighting & Imaging: Feature Brainstorm

Expanding SolaSim's unique capabilities — spatially-addressable LED panels on a solar arc, programmable camera triggering, and rotation imaging — into a richer experimental platform.

## Hardware Recap (What We Can Do)

| Resource | Detail |
|----------|--------|
| **NeoPixel Panels** | 7 × (8×8) panels = 56×8 pixel grid on a curved semi-circular arc |
| **Addressing** | Per-pixel (x,y), per-panel (0-6), or preset groups (ALL, MIDDLE3, OUTER2, etc.) |
| **Color** | Full RGB per pixel, independently controllable |
| **FR Strips** | 2 × 0.5m 730nm LED strips following the arc curve, offset N/S of the NeoPixel panels. Non-addressable, single PWM channel. Purpose: phytochrome depletion (Pfr→Pr) |
| **Servos** | Servo 1 (platform rotation), Servo 2+3 (camera triggers) |
| **Camera** | GPIO shutter pin + servo-actuated triggers, BLE HID trigger |
| **Power** | USB-powered. Current NeoPixels: ~35W peak at RGB(255,255,255) all panels — sufficient for phototropism at short distances |
| **Modes** | Sun tracks across the arc; panels can also be uniformly filled with `apply_lighting()` |

---

## 1. Imaging Schedule Table (Your Idea — Expanded)

**Core concept**: Replace the single `SERVO2_INTERVAL_DAY_SEC` with a time-varying schedule.

### Data Model
Each entry specifies a simulation-time window and its imaging interval:

```
imaging_schedule = [
  { "start": 600, "end": 800, "servo2_interval": 60, "servo3_interval": 0 },
  { "start": 800, "end": 1200, "servo2_interval": 300, "servo3_interval": 0 },
  { "start": 1200, "end": 1800, "servo2_interval": 120, "servo3_interval": 120 }
]
```

### Why This Matters Scientifically
- **Dawn/dusk sensitivity**: Plant phototropic responses are strongest during the first hours of light — high-frequency capture here, sparse elsewhere
- **Event windows**: If you know a tropic bending response peaks at ~2h after stimulus, you concentrate imaging there
- **Battery/storage**: Fewer images during quiet periods = longer unattended runs

### UI Approach
A mini-table below the existing program steps (or as collapsible sub-rows within them), with the same drag-to-reorder and inline editing pattern. The timeline strip would show imaging density as a subtle dot-pattern overlay.

---

## 2. Stimulus Lighting Layer (Your Idea — Expanded)

**Core concept**: A persistent "background" lighting layer that runs independently of the imaging flash.

Currently, `CAMERA_LIGHTING_PANELS` activates panels only **during** camera trigger events, then deactivates. Your idea introduces a second purpose: **continuous stimulus lighting** from selected panels at a different RGB/intensity than the sun.

### Two-Layer Lighting Model

```
Layer 1: Sun simulation      — moves across the arc per solar model
Layer 2: Stimulus lighting   — static or dynamic pattern, panel-subset, independent RGB
Layer 3: Imaging flash       — brief burst during camera trigger (existing)
```

Each layer has its own RGB, panel mask, and intensity. The panel buffer composites them (priority: L3 > L2 > L1 when overlapping).

### Per-Step Stimulus Parameters
Extend the existing step schema:

```json
{
  "sim_time_hhmm": 600,
  "intensity_scale": 1.0,
  "sun_color_rgb": [0, 0, 255],
  "stimulus_panels": "OUTER2",
  "stimulus_rgb": [255, 0, 0],
  "stimulus_intensity": 0.3
}
```

This lets you run blue sun + dim red side-lighting, changing per program step.

---

## 3. Arc-Segment Directional Light (Your Idea — New Concept)

**Core concept**: Specify a **spatial region of the arc** as a light source using **compass degrees from zenith** — invariant regardless of sunrise/sunset settings.

### Compass-Degree Notation

```
◀── WEST ──────────── 0° (Zenith) ──────────── EAST ──▶
 -90°    -60°    -30°      0°      30°     60°    90°
  P0      P1      P2       P3      P4      P5     P6
```

- **0°** = zenith (center of arc, column 28)
- **W** = west/sunrise side, **E** = east/sunset side
- Degrees are fixed physical positions — they don't shift when solar mode or sunrise/sunset changes
- Solar-time notation (`12:00-14:00`) was considered but rejected because CUSTOM sunrise/sunset settings change which physical panel a given time maps to

### Column-Level Resolution

The arc has **56 columns** (each 8 pixels tall). Degrees map to the nearest column:

```
x_column = round(28 + (degrees / 90) × 28)
spread_columns = round((spread / 90) × 28)
```

| Notation | Center column | Spread=10° columns |
|----------|:-:|:-:|
| `W30 ±10°` | col 18 | cols 15–21 |
| `E30 ±10°` | col 38 | cols 35–41 |
| `W60 ±5°` | col 9 | cols 7–11 |

This is **per-column**, not per-panel — sources can be positioned at any degree without aligning to panel boundaries.

### `stimulus_source` Parameter

```json
{
  "stimulus_sources": [
    { "position": "W45", "spread": 20, "rgb": [0, 0, 255], "intensity": 1.0 },
    { "position": "E45", "spread": 20, "rgb": [255, 0, 0], "intensity": 0.3 }
  ]
}
```

Where `position` is the center of the lit region and `spread` is the half-width in degrees. `W45 ± 20°` illuminates from W65° to W25° (approximately panels 1-2).

### Compound Sources
Multiple arc segments with different colors/intensities — for bilateral phototropism or gradient experiments.

---

## 4. Anti-Sun & Advanced Patterns (Your Idea — Extended)

### Anti-Sun
The sun occupies an 8×8 block at position x; the anti-sun illuminates everything **except** that block. At noon the center is dark, horizons are lit. At sunrise/sunset, the center is lit, edges dark.

**Biological rationale**: Background lighting with a dark object traversing the arc is a form of "negative stimulus" — the organism sees a moving shadow rather than a moving light source. This is relevant for **skototropism** (growth toward darkness) studies.

### More Pattern Ideas

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Anti-Sun** | All panels lit except the sun's current position | Skototropism, shadow response |
| **Leading Edge** | Only panels *ahead* of the sun (in its direction of travel) | Directional cue without full illumination |
| **Trailing Edge** | Only panels *behind* the sun | Post-exposure light memory experiments |
| **Gradient** | Intensity gradient across the arc (bright center → dim edges, or vice versa) | Dose-response gradients |
| **Pulse** | Brief flashes at configurable intervals superimposed on baseline | Phytochrome induction pulses |
| **Oscillating** | Alternating panel groups toggle at a fixed frequency | Circadian rhythm entrainment studies |
| **Migration** | A secondary light source moves in the opposite direction to the sun | Competing cue experiments |
| **Sentinel** | Specific panels flash briefly before each camera trigger | "Here comes the camera" warning for behavioral studies |

---

## 4b. Light Competition / Choice Experiments

**Core concept**: After stabilising a plant at solar noon (vertical, gravitropically neutral), transition to a **choice phase** where two stationary light sources compete — differing in color, intensity, or spectral composition.

### Experimental Design

```
Phase 1 (Stabilisation): Sun runs normally 06:00→12:00 (speed 60×)
  → Plant vertical under moving sun, intensity 1.0
Phase 2 (Transition):    Sun intensity → 0, two sources appear at W30°/E30°
  → Clear spatial separation from zenith (e.g. "10am" and "2pm" positions)
Phase 3 (Choice):        Speed = 0, sources static, high-frequency imaging
  → Plant bends toward preferred stimulus
```

### Example Step Sequence

```json
[
  { "sim_time_hhmm": 600,  "speed": 60, "intensity_scale": 1.0 },
  { "sim_time_hhmm": 1200, "speed": 0,  "intensity_scale": 0.0,
    "stimulus_sources": [
      { "position": "W30", "spread": 10, "rgb": [0,0,255], "intensity": 1.0 },
      { "position": "E30", "spread": 10, "rgb": [255,0,0], "intensity": 1.0 }
    ]
  }
]
```

### Transition Options
- **Instant**: Sun → 0 and sources → 1.0 simultaneously (simplest)
- **Ramp**: Sources ramp from 0→1.0 over a few simulated minutes to avoid startle response (add `ramp_seconds` parameter or use two successive steps at low, then full intensity)
- **Drifting sources**: Sources slowly move along the arc during the choice phase — tests whether the plant tracks a moving cue vs. committing to its initial choice (advanced, future)

### Competition Parameters

| Variable | Source A (Left) | Source B (Right) |
|----------|:-:|:-:|
| **Wavelength** | Blue (450nm) | Red (660nm) |
| **Intensity** | 100% | 100% |
| **Panels** | 1-2 | 5-6 |

Or for intensity discrimination:

| Variable | Source A (Left) | Source B (Right) |
|----------|:-:|:-:|
| **Color** | Blue | Blue |
| **Intensity** | 100% | 30% |
| **Panels** | 0-1 | 5-6 |

### Data Model

Competition fits naturally into the compass-degree multi-source model:

```json
{
  "sim_time_hhmm": 1200,
  "speed": 0,
  "stimulus_sources": [
    { "position": "W45", "spread": 20, "rgb": [0, 0, 255], "intensity": 1.0 },
    { "position": "E45", "spread": 20, "rgb": [255, 0, 0], "intensity": 1.0 }
  ],
  "far_red": 0.0,
  "imaging": {
    "schedule": [{ "start": 1200, "end": 1800, "interval": 30 }]
  }
}
```

Default position **W45°/E45°** (~9am/3pm) provides 90° total separation — enough to clearly separate gravity from light cues.

### Why This Is Novel

Most phototropism studies use a single unilateral light source. The arc hardware allows:

- **Symmetric bilateral stimuli** at precisely controlled angles
- **Parametric sweeps** — vary one parameter (intensity ratio, wavelength pair, angular separation)
- **Temporal sequences** — present Source A for 30 min, then switch to Source B, capture re-orientation kinetics
- **Three-way choice** — with 7 panels, create left/center/right stimuli
- **Phytochrome control** — FR pre-irradiation to deplete Pfr before choice phase, isolating phototropin-mediated responses

### Hardware

- **Current NeoPixel panels** (~35W peak): Sufficient for directional cue experiments at short plant-to-arc distances. USB power adequate.
- **FR strips**: 2 × 0.5m 730nm strips following the arc curve (offset N/S of NeoPixels), single PWM channel. Phytochrome depletion (Pfr→Pr) is saturated well within a 5-minute pulse even at modest fluence rates.
- **Future**: Higher-output panels could extend to intensity discrimination assays at greater distances.

---

## 5. Per-Step, Per-Panel "Light Recipes"

The most flexible approach: each program step can define a complete **panel map** — individual RGB + intensity for each of the 7 panels.

### Compact Encoding
To keep the step data manageable:

```json
{
  "sim_time_hhmm": 600,
  "light_recipe": {
    "mode": "arc",
    "position": "W15",
    "spread": 20,
    "rgb": [0, 0, 255],
    "intensity": 0.5
  }
}
```

Or for full manual control:

```json
{
  "light_recipe": {
    "mode": "panels",
    "panels": {
      "0": [0,0,0], "1": [0,0,50], "2": [0,0,100],
      "3": [0,0,255], "4": [0,0,100], "5": [0,0,50], "6": [0,0,0]
    }
  }
}
```

### UI: Visual Panel Editor
A horizontal row of 7 clickable panel tiles (matching the arc layout), each showing its current color. Click to open a color picker. The arc-time slider could overlay on the timeline strip.

---

## 6. Unified Feature Composition

All of these features compose naturally. A single program step could specify:

```
Sun:       Blue, BASIC mode, 06:00-18:00 day
Stimulus:  Red side-lighting from outer panels, 0.3 intensity
Imaging:   Every 60s during 06:00-08:00, every 300s otherwise
Camera:    Servo 2 only, with full-panel white flash for imaging
```

### Proposed Step Schema (Extended)

```json
{
  "sim_time_hhmm": 600,
  "speed": 60,
  "intensity_scale": 1.0,
  "sun_color_rgb": [0, 0, 255],
  "sunrise": 600,
  "sunset": 1800,

  "stimulus_sources": [
    { "position": "W30", "spread": 15, "rgb": [255, 0, 0], "intensity": 0.3 }
  ],
  "far_red": 0.0,

  "imaging": {
    "schedule": [
      { "start": 600, "end": 800, "interval": 60 },
      { "start": 800, "end": 1800, "interval": 300 }
    ],
    "flash_rgb": [255, 255, 255],
    "flash_panels": "ALL"
  }
}
```

### Implementation Priority Matrix

| Feature | Firmware Effort | UI Effort | Scientific Value |
|---------|:-:|:-:|:-:|
| Imaging schedule table | Medium | Medium | ★★★★★ |
| Stimulus lighting layer | Medium | Medium | ★★★★★ |
| Light competition / choice | Small | Medium | ★★★★★ |
| Arc-segment light source | Small | Medium | ★★★★☆ |
| Anti-sun pattern | Small | Small | ★★★☆☆ |
| Per-panel light recipes | Medium | High | ★★★★☆ |
| Advanced patterns (gradient, pulse, etc.) | Medium | Medium | ★★★★☆ |

---

## Resolved Decisions

| # | Question | Resolution |
|:-:|----------|------------|
| 1 | Compositing priority | **Sun > Imaging > Stimulus**. Sun always renders; imaging flash overrides everything; stimulus fills remaining columns |
| 2 | Arc-segment notation | **Compass degrees from zenith** (W/E). Column-level resolution (56 cols). Invariant across solar modes |
| 3 | FR strip design | Single non-addressable PWM channel. Arc-following, offset N/S. Purpose: phytochrome depletion only |
| 4 | Competition architecture | **Separate forked repo** (SolaChoice). Cross-linked with SolaSimStudio. Shared firmware |
| 5 | Default competition angle | **W45°/E45°** (~9am/3pm). 90° separation reduces gravity confound |
| 6 | NeoPixel adequacy | **Sufficient** at short distances (~35W peak). USB power adequate |
| 7 | FR efficacy | **Sufficient** — Pfr→Pr photoconversion completes in seconds; 5-min pulse is conservative |
| 8 | FR pre-irradiation timing | **After** sun off (in darkness), before choice sources activate |
| 9 | FR UI | **Checkbox** + duration field (default 5 min) |

---

## Open Questions — Resolved

| # | Question | Resolution |
|:-:|----------|------------|
| 1 | Prototype scope | **SolaChoice (competition) is the priority.** SolaSimStudio is locked down. New features developed in SolaChoice, ported back later. |
| 2 | Codebase strategy | **Fork-first.** Separate repo for SolaChoice. Shared firmware, distinct lighter UI. Cross-linked. |
| 3 | Gravity interaction | **Empirical.** Include 30°, 45°, and 60° as three built-in example programs. |
| 4 | Ramp vs. instant | **Instant switch only.** Ramp adds complexity for uncertain benefit. Simplify. |
| 5 | Stimulus rendering | **Back-burnered.** Not important for near-term work. |
| 6 | Step schema memory | Must fit on both **ESP32 and RP2040** (less RAM). Competition profiles stay compact (defaults until choice step). |
| 7 | Imaging schedule | Straightforward window lookup. Implement as needed. |

---

## Development Strategy: Fork-First

**Plan**: SolaSimStudio is stable — lock it down. Build SolaChoice as a separate forked repo. Port proven features back.

**Why this works**:
- SolaChoice has a fundamentally different UI (pre/post step tables, WEST/EAST cards) — cleaner to build fresh than contort the existing 1.2MB HTML
- Lighter codebase = faster iteration, fewer regressions
- Features battle-tested in SolaChoice (e.g., imaging timetable) port back to SolaSimStudio as known-good code
- Shared firmware step schema means profiles are interchangeable

**Key constraint**: keep the ESP32/RP2040 firmware step schema **identical** across both apps. SolaChoice uses a subset; SolaSimStudio supports the full set.

---

## Example Competition Programs

Three built-in examples for initial experiments, varying angular separation:

### Program 1: Narrow (30° separation)
```json
[
  { "sim_time_hhmm": 600, "speed": 60, "intensity_scale": 1.0 },
  { "sim_time_hhmm": 1200, "speed": 0, "intensity_scale": 0.0,
    "stimulus_sources": [
      { "position": "W15", "spread": 10, "rgb": [0,0,255], "intensity": 1.0 },
      { "position": "E15", "spread": 10, "rgb": [255,0,0], "intensity": 1.0 }
    ]
  }
]
```

### Program 2: Medium (90° separation) ★ Default
```json
[
  { "sim_time_hhmm": 600, "speed": 60, "intensity_scale": 1.0 },
  { "sim_time_hhmm": 1200, "speed": 0, "intensity_scale": 0.0,
    "stimulus_sources": [
      { "position": "W45", "spread": 10, "rgb": [0,0,255], "intensity": 1.0 },
      { "position": "E45", "spread": 10, "rgb": [255,0,0], "intensity": 1.0 }
    ]
  }
]
```

### Program 3: Wide (120° separation)
```json
[
  { "sim_time_hhmm": 600, "speed": 60, "intensity_scale": 1.0 },
  { "sim_time_hhmm": 1200, "speed": 0, "intensity_scale": 0.0,
    "stimulus_sources": [
      { "position": "W60", "spread": 10, "rgb": [0,0,255], "intensity": 1.0 },
      { "position": "E60", "spread": 10, "rgb": [255,0,0], "intensity": 1.0 }
    ]
  }
]
```

---

## Remaining Open Questions — Resolved

| # | Question | Resolution |
|:-:|----------|------------|
| 1 | Naming | **SolaChoice** ✓ |
| 2 | Firmware versioning | **Separate until proven.** Risk: unknown if extended schema fits without OOM. Keep firmware repos independent until competition features are validated on both MCUs. |
| 3 | RP2040 parity | **Ideally both** ESP32 and RP2040. RP2040 is serial-only with less RAM — competition profiles must stay compact. |
| 4 | Cross-link UX | **Button in header** on each app linking to the other. |
| 5 | Profile compatibility | **Yes.** SolaChoice profiles openable in SolaSimStudio (competition fields ignored) and vice versa. |

---

## Next Steps

| Priority | Action | Effort |
|:-:|--------|:-:|
| **1** | Create the SolaChoice repo (fork from SolarSimulator) | Small |
| **2** | Strip SolaSimStudio UI down to competition essentials (pre/post tables, WEST/EAST cards, FR checkbox) | Medium |
| **3** | Add `stimulus_sources` and `far_red` fields to the firmware step handler | Small |
| **4** | Implement column-level stimulus rendering in `hardware.py` | Small |
| **5** | Build 3 example programs (30°/45°/60°) as built-in presets | Small |
| **6** | Add imaging schedule table to SolaChoice UI | Medium |
| **7** | Port imaging schedule back to SolaSimStudio | Medium |

---

## Future Features (App-Agnostic)

### Shared Profile Repository on GitHub

A public GitHub repo (`SolaSim-Profiles`) storing experiment profiles that both SolaSimStudio and SolaChoice can browse and import.

**Structure**:
```
SolaSim-Profiles/
├── solasim/          ← SolaSimStudio profiles
├── solachoice/       ← SolaChoice profiles
└── index.json        ← manifest (name, description, tags, app type)
```

**Load**: `📥 Load from Repo` button fetches `index.json` via `raw.githubusercontent.com` (no auth needed for public repos). Shows filterable list → click to preview → confirm to load. Greyed out if offline.

**Share**: `📤 Share to Repo` exports current profile as JSON with metadata (author, date, description, app version). Copies to clipboard or downloads file. User submits a PR to the repo.

**Benefits**: Free, no backend, version controlled, cross-app, community contributions via PRs, graceful offline fallback.

