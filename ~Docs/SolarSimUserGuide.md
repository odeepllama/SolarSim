# Solar Simulator User Guide

Welcome to the **SolaSim Studio** user guide. This document provides everything you need to set up your solar simulation hardware and use the web interface to control lighting, rotation, and imaging for your experiments.

---

## 🚀 Quick Start: Installation & Setup

### 1. Prepare the Device (RP2040:bit)
The Solar Simulator runs on a Raspberry Pi Pico-based board called the **RP2040:bit**. You need to install the custom firmware (a single `.uf2` file) which contains both the operating system (MicroPython) and the Solar Simulator software.

1.  **Download the Firmware**: Obtain the latest `SolarSimulator_YYYYMMDD.uf2` file from the SolaSim GitHub repository.
2.  **Enter Bootloader Mode**:
    *   Hold down the **BOOT** button on the edge of the board.
    *   While holding **BOOT**, prese the **RESET** button on the edge of the board.
    *   Release the button.
3.  **Install Firmware**:
    *   A new drive named `RPI-RP2` will appear on your computer (like a USB stick).
    *   Drag and drop the `.uf2` file onto this drive.
    *   The device will automatically disconnect and reboot. The installation is complete!

### 2. Open SolaSim Studio
You do not need to install any software on your computer to control the device.

*   **Recommended**: Open [https://odeepllama.github.io/SolarSim/](https://odeepllama.github.io/SolarSim/) in a compatible browser (Google Chrome, Microsoft Edge, or Opera).
*   **Advanced/Offline**: If you have the `ProfileBuilder.html` file locally, you can simply double-click it to open it in your browser.

### 3. Connect
1.  After connecting the RP2040 board to your computer, click the green **Connect** button in the top "Monitor / Interact" bar.
2.  A browser window will pop up asking permission to connect to a serial device.
3.  Select your device (often listed as "Board in FS node") and click **Connect**.
4.  The status badge will turn green and show **CONNECTED**.
5.  If the device does not immediately conect, press the **RESET** button on the edge of the board and try conencting again.

---

## 💡 Core Concepts

Before using the system, it is helpful to understand two key concepts:

### Form vs. Device
*   **The Form (Web Page)**: This is your workspace. Changing numbers or settings here **does not** immediately change the device. It is like writing a document before printing it.
*   **The Device (Hardware)**: This is the physical board running the simulation.
*   **Syncing**: To make your form settings take effect on the hardware, you must click **Upload to Device**.

### Auto-Load & Persistence
*   **Temporary Changes**: If you use the "Monitor" tiles to change speed or intensity, those changes are lost if the device loses power.
*   **Persistent Profiles**: When you **Upload to Device**, the system saves your settings as a file.
*   **Auto-Load**: By default, when the device powers up, it looks for the most recently uploaded profile and runs it automatically. If Auto-Load is disabled, the device will start with default settings (single sun, 1X speed, sunrise 0600, sunset 1800, etc).

---

## 🎮 Three Ways to Use SolaSim Studio

### 1. Real-Time Interaction (Monitor Mode)
*Best for: Quick adjustments, testing hardware, and checking status.*

At the top of the page is the **Monitor / Interact** bar. Click the arrow to expand it if the Solar Arc is not visible.
*   **Status Tiles**: You will see live data from the device (e.g., `SimTime`, `Speed`, `Intensity`).
    *   **Click a tile** to change its value immediately. For example, click **Speed** to pause (HOLD) or fast-forward (600x) the simulated time.
    *   **Double-click** certain tiles (like `Program` or `Rotation`) to toggle them ON or OFF.
*   **Command Console**: Type commands manually (e.g., `set intensity 0.5`) in the text box for precise control. The **Show All COmmands** button will output all commands in the log window (Visible in Advanced mode)
*   **Solar Arc**: A visual representation of the sun's position and day/night cycle.

> **Note**: Changes made here happen immediately but are **not saved** to the permanent profile.

### 2. Building Custom Profiles
*Best for: Designing specific experiments with precise lighting and timing requirements.*

Use the main form to define your experiment parameters.

#### Core Settings
*   **Start Time**: When the simulation clock begins (e.g., `0600` for 6 AM).
*   **Time Scale**: How fast time passes (e.g., `60x` means 1 hour passes in 1 minute).
*   **Solar Mode**:
    *   **BASIC**: Simple sunrise (6 AM) to sunset (6 PM) with constant sun size.
    *   **SCIENTIFIC**: Calculates accurate sun position based on the **Date** and **Latitude** you provide.
*   **Sun Color**: Choose **BLUE** (standard for experiments), **NATURAL** (yellow/white), or **CUSTOM** (RGB).

#### Program Steps (The Timeline)
If you need the conditions to change over time (e.g., "Run at 2x speed until noon, then hold for 1 hour"), use the **Program Steps** section.
1.  Ensure **Program Enabled** is checked.
2.  Click **Add Step** to create a new sequence.
3.  For each step, define:
    *   **Time**: When this step targets (e.g., `1200`).
    *   **Transition**: `RUN` (simulate time passing) or `JUMP` (skip instantly).
    *   **Speed/Intensity**: The conditions during this step.
4.  Use the **Timeline Visualization** to verify your sequence looks correct.
5.  You can add additional days with different steps/conditions if your experiment requires.

#### Rotation & Imaging
Configure the turntable and camera triggers.
*   **Rotation Enabled**: Master switch for the rotatinf platform.
*   **Capture Mode**: `STILLS` (stop-motion) or `VIDEO` (continuous).
*   **Intervals**: How often to take photos or rotate.

### 3. Uploading & Running
*Best for: Starting your experiment.*

Once your form is configured:
1.  Check the **Profile Diff Viewer** (yellow highlights). This shows you what is different between your form and the device.
2.  Click the green **Upload to Device** button.
3.  Follow the prompt (you may need to press the RESET button on the device if requested, though usually it is automatic).
4.  The device will save the profile, restart, and begin running your experiment immediately.

---

## 📂 Managing Profiles

### Loading from Device
If you want to see or edit the profile currently running on the hardware:
1.  Click **Load / Delete from Device**.
2.  A list of files stored on the RP2040 will appear.
3.  Select a profile to load it into the web form.
    *   *Note: Selecting a profile here also tells the device to run it immediately, but it does not make it the "default" for the next startup unless you re-upload it or it is already the most recent profile.*

### Saving & Importing
*   **Download Profile**: Saves your current settings as a text file (`.txt`) to your computer. Useful for sharing experiments or backups.
*   **Import Profile**: Loads a `.txt` file from your computer into the web form.
*   **Recent Profiles**: The bar at the top of the form saves your recent configurations automatically. Click one to restore it. CLick the **Star** to prevent key profiles from rotating off the screen as more are created.

### Profile Comparison
When you load a profile, the **Comparison Window** will show you exactly what is different between your current settings and the new profile.
*   **Orange Fields**: Indicate settings that differ.
*   **Apply**: Overwrites your form with the new profile.

---

## ⚙️ Advanced Features

### Simple vs. Advanced Mode
*   **Simple Mode**: Hides complex settings (like specific servo timings or RGB values) to keep the interface clean.
*   **Advanced Mode**: Shows all available parameters.
*   Use the **Gear Icon (⚙)** next to the mode toggle to customize which sections are hidden in Simple Mode.

### Device Labeling
If you have multiple devices connected:
1.  Click the **Device Badge** (e.g., "Device 1") in the top header.
2.  Rename it (e.g., "Experiment A").
3.  Use the **Background Color** swatches (top right) to color-code your tabs (Green, Blue, Red).

### Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Device not connecting** | Ensure no other tab or program (like Thonny or VS Code) is using the USB port. Unplug and replug the device. |
| **Settings didn't change** | Did you click **Upload**? Changing the form only updates the web view, not the hardware. |
| **Wrong profile on startup** | The device auto-loads the profile with the **newest timestamp**. If you loaded an older profile via "Load from Device", it won't persist after a reboot. To make an old profile permanent, **Upload** it again so it gets a new timestamp. |
| **Orange highlights everywhere** | This is normal! It means the settings in your web form are different to those on the device. Click **Sync to Device** (in the banner) or **Upload** to make them match. |
