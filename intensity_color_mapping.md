# Intensity → Color Mapping Reference

## Design Principle

Speed bar segments use the step's **sun color** as the base hue, with **opacity over white** encoding the intensity level. Higher intensity = more vivid/opaque. Lower intensity = paler/more transparent (fading toward white).

## Formula

```
composited_pixel = sun_color × opacity + 255 × (1 - opacity)
```

## Blue Sun Benchmark (base color: `rgb(30, 130, 235)` / `#1E82EB`)

| Intensity | Opacity | Composited RGB | Hex | HSL |
|-----------|---------|---------------|-----|-----|
| **1.0** | 1.00 | `rgb(30, 130, 235)` | `#1E82EB` | `hsl(211, 83%, 52%)` |
| **0.8** | 0.85 | `rgb(64, 149, 238)` | `#4095EE` | `hsl(211, 83%, 59%)` |
| **0.6** | 0.70 | `rgb(98, 168, 241)` | `#62A8F1` | `hsl(211, 83%, 66%)` |
| **0.4** | 0.55 | `rgb(131, 186, 244)` | `#83BAF4` | `hsl(211, 82%, 74%)` |
| **0.2** | 0.40 | `rgb(165, 205, 247)` | `#A5CDF7` | `hsl(211, 82%, 81%)` |
| **0.0** | 0.00 | `rgb(255, 255, 255)` | `#FFFFFF` | white |

## Opacity Interpolation

For arbitrary intensity values between 0 and 1:

```
opacity = 0.40 + intensity × 0.60
```

This maps intensity 0 → opacity 0.40, intensity 1 → opacity 1.00. For a true white at intensity 0, use:

```
opacity = intensity × 1.00
```

## Speed Bar Graph

- **Bar height** encodes speed (taller = faster)
- **Bar opacity** encodes intensity (more opaque = higher intensity)
- **Bar hue** comes from the step's `sun_color_rgb`
- **HOLD steps**: grey diagonal hatching (unchanged)
- **JUMP steps**: zero width (invisible)

## CSS Implementation

```css
/* In the speed bar, each segment's background: */
background: rgba(sun_r, sun_g, sun_b, opacity);
/* over a white (#f0f0f0) strip background */
```

## Preview

See `oklch_grid.html` in `ESP32/` for a live interactive preview.
