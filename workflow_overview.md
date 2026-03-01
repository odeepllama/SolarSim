# GitHub Pages Deployment Overview

Managed by `.github/workflows/deploy-pages.yml`. Deploys on every push to any branch.

Base URL: `https://odeepllama.github.io/SolarSim`

| URL Path | Source File | Branch | Description |
|----------|------------|--------|-------------|
| `/` | `ProfileBuilder.html` | main | Root USB-only ProfileBuilder |
| `/Bt/` | `ESP32_Bluetooth/ProfileBuilderBt.html` | main | ESP32 Bluetooth (production) |
| `/Bt/test/` | `ESP32_Bluetooth/ProfileBuilderBt.html` | non-main | ESP32 Bluetooth (testing) |
| `/ble/` | `BLE_iPad/SolaSimStudioBLE.html` | main | Latest UI + restored BLE (production) |
| `/ble/test/` | `BLE_iPad/SolaSimStudioBLE.html` | non-main | Latest UI + restored BLE (testing) |
| `/ble/working/` | `BLE_Working/ProfileBuilderBt.html` | main | Original known-working BLE snapshot (production) |
| `/ble/working/test/` | `BLE_Working/ProfileBuilderBt.html` | non-main | Original known-working BLE snapshot (testing) |
