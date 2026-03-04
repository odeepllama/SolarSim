# Solar Simulator — Future To-Do List

## Custom Solar Mode (User-Defined Sunrise/Sunset)

Add a third `SOLAR_MODE = "CUSTOM"` option alongside BASIC and SCIENTIFIC, allowing the user to directly specify sunrise and sunset times rather than relying on hardcoded 06:00–18:00 (BASIC) or astronomical calculation (SCIENTIFIC).

### Scope
- **Firmware** (both `SolarSimulatorSun.py` and `simulator.py`):
  - New `CUSTOM` branch in `init_solar_day()` using `CUSTOM_SUNRISE_MINUTES` and `CUSTOM_SUNSET_MINUTES`
  - Use BASIC-style constant sun size (8×8) with user-defined time window
  - New config variables: `CUSTOM_SUNRISE_HHMM`, `CUSTOM_SUNSET_HHMM`
- **Serial commands**: `set sunrise HHMM`, `set sunset HHMM` (or combined)
- **HTML UI** (`SolaSimStudio.html`):
  - New "CUSTOM" option in SOLAR_MODE dropdown
  - Conditional sunrise/sunset time input fields (show only when CUSTOM selected)
  - Profile export/import support for the new fields
  - Comparison modal support
- **Help text**: Update both the inline help panel and the full guide sections
- **Translations** (`i18n` strings): Labels for new fields and mode option
- **Status output**: Firmware should report custom sunrise/sunset in status updates
- **Sun Arc visualization**: Update to reflect custom sunrise/sunset boundaries
