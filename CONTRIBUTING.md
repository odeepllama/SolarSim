# Contributing to SolaSim

Thank you for your interest in contributing to SolaSim! This is a research project developed at Akita International University, and we welcome contributions from the community.

## Getting Started

1. **Fork** the repository and clone your fork locally
2. Create a **feature branch** from `main`: `git checkout -b my-feature`
3. Make your changes and test them
4. **Commit** with a clear, descriptive message
5. **Push** to your fork and open a **Pull Request**

## Code Style

### MicroPython Firmware (`RP2040/`, `ESP32/`)
- Follow standard Python/MicroPython conventions (PEP 8 where practical)
- Use descriptive variable and function names
- Add comments for non-obvious logic, especially hardware interactions
- Keep memory usage in mind — the RP2040 has very limited RAM

### Web Interface (`SolaSimStudio.html`)
- The web interface is a single self-contained HTML file (HTML + CSS + JavaScript)
- Use clear, descriptive `id` attributes for interactive elements
- Maintain bilingual support (English/Japanese) for all user-facing text
- Test in Chrome, Edge, or Opera (Web Serial API requirement)

## Testing

### Firmware
- Test on actual hardware (RP2040 or ESP32-S3) when possible
- Verify serial communication works with the web interface
- Check for memory issues — run `gc.mem_free()` to monitor available RAM

### Web Interface
- Open `SolaSimStudio.html` directly in a Chromium-based browser
- Test both connected (with device) and disconnected states
- Verify the timeline, status tiles, and command console all function correctly
- Test in both English and Japanese modes

## Reporting Bugs

Please use the [Bug Report](https://github.com/odeepllama/SolarSim/issues/new?template=bug_report.md) issue template and include:
- Steps to reproduce the issue
- Expected vs. actual behaviour
- Browser and OS version (for web interface issues)
- Hardware setup details (for firmware issues)

## Suggesting Features

Use the [Feature Request](https://github.com/odeepllama/SolarSim/issues/new?template=feature_request.md) issue template to propose new ideas.

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Describe **what** you changed and **why**
- If your change affects the web interface, include a screenshot
- If modifying firmware, note which board(s) you tested on
- For RP2040 firmware changes, remember to rebuild `main_app.mpy` using `mpy-cross`

## Questions?

Open a [Discussion](https://github.com/odeepllama/SolarSim/issues) or reach out via an Issue. We're happy to help!
