# The Self-Driving Plant 🌱🚗

A phototropism-driven feedback system where a plant's own bending triggers mechanical movement of its container.

## Concept Summary

A pea seedling (*Pisum sativum*) sits in a container ("plant car") on a track running **parallel** to the SolaSim lighting arc. The system creates a closed-loop oscillation:

```
 ┌─── Plant bends toward light (right) ───────────────┐
 │                                                     │
 │  SUN at E30° (10am, RIGHT)                          ▼
 │  ┌─────────────────────────────────────┐    Sensor triggered
 │  │ [car] 🌱→                        ☀️ │    (bend threshold)
 │  └─────────────────────────────────────┘           │
 │       LEFT                         RIGHT            │
 │  Car moves RIGHT toward sun (fixed distance)        │
 │  Sun INSTANTLY flips to W30° (2pm, LEFT)            │
 │                                                     │
 │  SUN at W30° (2pm, LEFT)                            │
 │  ┌─────────────────────────────────────┐            │
 │  │ ☀️                        ←🌱 [car] │    Plant redirects
 │  └─────────────────────────────────────┘           │
 │                                                     │
 │  Car moves LEFT toward sun → returns to start       │
 └─────────────────────────────────────────────────────┘
                    CYCLE REPEATS
```

After night, the plant recovers to vertical. The cycle begins with the sun at E30° (10am, right) and the plant on the left — the plant bends right, "driving" toward the morning light.

### The Key Insight

The plant is both the **sensor** and the **driver** in a bio-mechanical feedback loop. Phototropic bending steers the car **toward** the light. Each time the car arrives, the light flips to the opposite side, and the plant must redirect — driving itself back and forth along the track.

---

## Trigger Mechanisms

How does the system detect "the plant has bent far enough"?

### Option 1: IR Beam Break (★ Recommended for v1)

```
  IR emitter ───── beam ───── IR detector
                    ↑
               plant stem interrupts beam
```

- Cheap (~¥200 for emitter + phototransistor pair)
- No contact with the plant
- Adjustable trigger angle by positioning the beam height/angle
- Simple digital output → GPIO interrupt
- **Drawback**: Requires precise alignment; leaves and younger stems might cause false triggers

### Option 2: Hall Effect + Magnet on Stem Tip

- Small magnet glued/clipped to the stem tip
- Hall sensor positioned at the trigger angle
- Detects proximity magnetically — no optical issues
- **Drawback**: Magnet weight may influence bending; need re-attachment as stem grows

### Option 3: Trip Wire / Whisker Switch

- Thin conductive wire positioned at the trigger angle
- Stem physically pushes against it, completing a circuit
- Extremely simple (a GPIO with pull-up)
- **Drawback**: Physical contact may resist/influence bending; stem could grow around it

### Option 4: Host-Side Computer Vision (★★ Recommended)

ESP32-S3-CAM streams JPEG frames to the webpage. JavaScript processes the image using `<canvas>`, detects stem angle, and sends a trigger command back via serial/BLE.

- **Pros**: No C code needed — all JS. Visual debugging (see what CV sees, draw angle overlay live). Threshold adjustable in real-time via UI. Camera feed doubles as time-lapse. Works on iPad/desktop.
- **Cons**: Requires a host browser running continuously. WiFi needed if using wireless camera. Not standalone.
- **Mitigation**: Raspberry Pi as dedicated headless host, or fall back to IR beam break if host disconnects.

### Recommendation

**Option C (host-side CV) for development and calibration** — the visual feedback and tuneable thresholds make it ideal for discovering optimal parameters. Once timings are proven, the experiment runs as a **standalone timed program** on the ESP32 without any CV in the loop (see Dual-Mode below).

IR beam break remains a viable fallback for simple demos or when no host is available.

---

## Dual-Mode Operation

### Mode 1: CV-Assisted Discovery (host required)

The webpage shows a **live dashboard** with camera feed, angle overlay, and system state:

```
┌─────────────────────────────────────────────┐
│  🌱 Self-Driving Plant        [Connected ●] │
│  ┌───────────────────┐   State: DRIVING_EAST│
│  │   [live camera    │   Angle: 18° / 30°   │
│  │    feed with      │   Cycles: 3          │
│  │    angle overlay] │   Distance: 12cm     │
│  └───────────────────┘   Sun: E30° (10am)   │
│  ████████░░░░░░░░░░░░  18°/30° to trigger   │
└─────────────────────────────────────────────┘
```

Use this to empirically determine: bending rate (°/hour), optimal trigger angle, time per half-cycle, max repeats before stem fatigue.

#### Proportional Response Model

Rather than a simple binary trigger (bend past threshold → move car a fixed distance), the CV mode can implement **continuous proportional movement**: the car moves in proportion to the plant's lean angle, creating a smoother, more biologically-relevant feedback loop.

**Configurable UI parameters:**

| Slider / Control | Description |
|---|---|
| **Trigger Angle (°)** | Minimum lean angle before any car movement begins (dead zone) |
| **Movement Speed** | How fast the car responds once past the trigger angle — maps lean angle to motor speed |
| **Max Speed Cap** | Upper limit on motor speed to prevent overshooting |

**Behaviour**: Once lean exceeds the trigger angle, the car's instantaneous speed is proportional to `(current_angle - trigger_angle)`. A small lean above threshold → slow creep. A large lean → faster movement. This mimics a natural pursuit dynamic where stronger phototropic response drives faster displacement.

```
Speed ▲
      │         ╱ speed cap ─────
      │       ╱
      │     ╱  ← proportional zone
      │   ╱
      │──╱ trigger angle
      └──────────────────────▶ Lean angle (°)
```

This creates a **smooth feedback loop** instead of discrete jumps, and the dashboard sliders let the researcher tune the response curve in real time during CV discovery mode.

### Mode 2: Standalone Timed Program (no host)

Once parameters are known, encode as a simple step table on the ESP32:

```python
program = [
  { "sun": "E30", "duration_h": 4, "car_action": "RIGHT" },
  { "sun": "W30", "duration_h": 4, "car_action": "LEFT" },
  # repeat N times
]
```

No host, no camera, no WiFi — runs autonomously in a growth chamber for days.

### Development Path

1. **Build with CV** → discover optimal timings, collect dashboard video, tune thresholds live
2. **Parameterize** → encode proven timings into a standalone program
3. **Keep both modes** → CV for new species/conditions, timed for proven protocols

---

## Mechanical Design

### Track

- Linear rail or guide rod, ~30-50cm long, parallel to the arc
- Could be 3D printed with V-slot or use aluminium extrusion
- Plant car slides on the track, driven by a stepper motor or servo with a rack-and-pinion / belt

### Plant Car

- Small platform (~5cm × 5cm) holding the cuvette/pot
- Low-friction bearings on the track rail
- Wired sensor (IR pair) mounted on the car, moves with the plant
- Endstop switches at each end of the track for safety

### Drive Mechanism Options

| Mechanism | Pros | Cons |
|-----------|------|------|
| **Servo + rack-and-pinion** | Simple, uses existing servo code | Limited travel, needs long rack |
| **Stepper + belt** | Smooth, precise, long travel | Needs stepper driver, more complex |
| **Servo + string/pulley** | Simple, cheap, long travel | Less precise, string can slip |
| **Linear actuator** | Direct, self-contained | Slow, expensive, limited options |

**Recommendation**: Stepper + GT2 belt is the cleanest for a ~30cm travel. But a servo + string/pulley could work for v1 with minimal hardware.

---

## SolaSim Integration

The self-driving plant builds on the existing SolaSim/SolaChoice hardware:

### What Already Exists

- Arc with addressable panels → provides the two light source positions
- Servo control code → adaptable for car drive motor
- Camera trigger system → time-lapse of the whole cycle
- Serial/BLE communication → control from host

### New Hardware Needed

| Component | Purpose | GPIO |
|-----------|---------|:----:|
| IR emitter | Beam break trigger (emitter) | GPIO 10 |
| IR detector | Beam break trigger (detector) | GPIO 11 |
| Stepper/servo for car | Drive along track | GPIO 12-13 |
| Endstop switches (×2) | Track limits | GPIO 14-15 |

### New Firmware Logic

```python
state = "DRIVING_EAST"   # plant on left, sun at E30° (10am), bending right

if beam_break_detected():
    if state == "DRIVING_EAST":
        move_car("RIGHT", distance=10_cm)   # toward E30° (10am) sun
        set_sun_position("W30")             # flip sun to W30° (2pm)
        state = "DRIVING_WEST"
    elif state == "DRIVING_WEST":
        move_car("LEFT", distance=10_cm)    # toward W30° (2pm) sun, back to start
        set_sun_position("E30")             # flip sun to E30° (10am)
        state = "DRIVING_EAST"
    
    cycle_count += 1
    trigger_camera()                        # capture the moment
```

---

## Timing Analysis

| Parameter | Value | Notes |
|-----------|:-----:|-------|
| Phototropic bending rate (*Pisum*) | ~5-15°/hour | Varies with light intensity and species |
| Trigger angle | ~30° from vertical | Adjustable via beam position |
| Time to trigger | **2-6 hours** | Per half-cycle |
| Full oscillation cycle | **4-12 hours** | Out + return |
| Cycles per day | **2-6** | Depends on bending speed |
| Car travel distance | ~5-10 cm | Per trigger event |

### Speed Considerations

Phototropism is slow — hours per response. This is a **patience experiment**. The car moves in brief bursts separated by hours of waiting. The time-lapse camera is essential to make the motion visible.

---

## Scientific & Outreach Value

### As Science
- **Closed-loop phototropism**: Most studies are open-loop (stimulus → response). This creates a feedback cycle where the plant's response changes its environment.
- **Adaptive behaviour**: Does the plant "learn"? Do subsequent cycles get faster/slower? Does the bending angle or direction change over repeated oscillations?
- **Biomechanics**: Quantify the force/speed of phototropic bending under repeated reversal conditions.

### As Outreach / Art
- **"Plant-powered vehicle"** — extremely compelling visual and narrative
- **Time-lapse video** of a plant driving itself back and forth is social media gold
- **JSPP poster** or **science communication** — demonstrates phototropism in a visceral, intuitive way
- **Student projects** — accessible, visual, interdisciplinary (biology + engineering)

---

## Variations & Extensions

| Variant | Description |
|---------|-------------|
| **Race** | Two plants side-by-side, first to trigger wins |
| **Maze** | Track has branches; plant chooses direction based on light placement |
| **Compass** | Light rotates around the plant; measure how quickly it redirects |
| **Tug-of-war** | Two plants pulling a car in opposite directions via competing light sources |
| **Speedometer** | Measure and display bending rate in real-time on the OLED |
| **Autonomous navigation** | CV-guided version with light positioned dynamically based on plant position |

---

## Open Questions

1. **Trigger reliability**: Will IR beam break be reliable enough, or will leaves/growth artefacts cause false triggers? Need debounce logic.

2. **Stem fatigue**: Can a pea seedling sustain repeated 30° bends back and forth over multiple days without mechanical damage to the stem?

3. **Gravitropism interaction**: Repeated bending means the stem is alternately leaning left and right. Does gravitropism interfere with the phototropic reversal?

4. **Growth vs. bending**: As the plant grows taller, the trigger point changes. Does the beam need to auto-adjust, or is the growth rate slow enough that manual daily adjustment suffices?

5. **Car travel distance**: How far should the car move per trigger? Too far = plant may not redirect (light is still roughly the same direction). Too short = no visible "driving" effect.

6. **Track orientation**: Parallel to the arc means the car moves E-W. Should the car move perpendicular to the arc (toward/away from the panels) instead, so the light angle changes more dramatically?

7. **Number of plants**: One seedling, or multiple in the cuvette for redundancy? Multiple stems could trigger the sensor more reliably but complicate the visual.

8. **What species?**: *Pisum* bends strongly but is tall. *Arabidopsis* is too small. *Helianthus* (sunflower)? *Phaseolus* (bean)? Need strong, visible bending.
