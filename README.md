# DucoBox integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/danielpetrovic/ha-ducobox.svg)](https://github.com/danielpetrovic/ha-ducobox/releases)
[![License](https://img.shields.io/github/license/danielpetrovic/ha-ducobox.svg)](LICENSE)

A Home Assistant integration for DucoBox ventilation systems using the Communication Print (0000-4251) local API.

## Features

This integration enables controlling and monitoring DucoBox ventilation systems with Communication Print devices.

- **Automatic device discovery** via Zeroconf/mDNS
- **Improved reliability** - sensors maintain their last state during network timeouts

### Fan entities

- **Ventilation**: Control ventilation with continuous percentage slider (0-100%) and preset modes
  - **Percentage Slider**: Direct flow override control (0-100%)
  - **Preset Modes**: Auto, Manual 1, Manual 2, Manual 3
  - **Override Mode**: When using percentage slider, mode shows as "Override" and preset mode is cleared
  - **Turn On/Off**: Sets to Auto mode when turned on
  - Percentage slider clears any active preset; selecting a preset clears the override

### Select entities

- **Bypass Mode**: Select bypass operation mode (Automatic, Closed, Open)

### Switch entities

**Main DucoBox:**
- **Bypass Adaptive**: Enable/disable adaptive bypass control

**Room Nodes:**
- **Temperature Dependent**: Enable temperature-weighted ventilation demand (useful for bathrooms)
- **Humidity Delta**: Enable humidity delta control

### Button entities

- **Reset Filter Timer**: Reset the filter replacement countdown

### Number entities

**Main DucoBox Configuration:**
- **Auto Minimum Flow**: Minimum airflow in auto mode (%)
- **Auto Maximum Flow**: Maximum airflow in auto mode (%)
- **Capacity**: Ventilation system capacity
- **Manual Speed Level 1/2/3**: Configure flow rates for manual speed presets (%)
- **Manual Timeout**: Duration for manual mode before returning to auto (minutes)
- **Comfort Temperature**: Target temperature for bypass control (°C)
- **Airflow Inlet Pressure Maximum**: Calibration for inlet pressure sensor (Pa)
- **Airflow Outlet Pressure Maximum**: Calibration for outlet pressure sensor (Pa)
- **Airflow Output Maximum**: Calibration for maximum airflow output (m³/h)
- **Program Mode Zone 1/2**: Zone program mode settings

**Room Node Configuration:**
- **Temperature Offset**: Calibrate temperature readings (-3.0°C to +3.0°C, 0.1°C steps)
- **CO2 Setpoint**: Target CO2 level for demand-based ventilation (ppm)
- **Humidity Setpoint**: Target humidity level for demand-based ventilation (%)
- **Manual Speed Level 1/2/3**: Configure flow rates for this node's manual speed presets (%)
- **Manual Timeout**: Duration for manual mode before returning to auto (minutes)
- **Sensor Visualization Level**: Adjust sensor display sensitivity (%)

### Sensor entities

**Main Box Sensors:**
- **Relative Humidity**: Current relative humidity (%)
- **Airflow Target Level**: Current target flow level (%)
- **Ventilation Mode**: Current ventilation mode (`AUTO`, `MANU`, or `EXTN` for Override)
- **Ventilation State**: Current ventilation state
- **Ventilation State End Time**: Timestamp when current ventilation state will end (hidden when in override mode)
- **Ventilation State Remaining Time**: Remaining time in current ventilation state in seconds (shows 0 when in override mode or expired)

**Energy & Box Information Sensors:**
- **Outdoor Temperature**: Outdoor air temperature (°C)
- **Supply Temperature**: Supply air temperature (°C)
- **Extract Temperature**: Extract air temperature (°C)
- **Exhaust Temperature**: Exhaust air temperature (°C)
- **Bypass Status**: Current bypass status (%)
- **Filter Remaining Time**: Days until filter replacement needed
- **Supply Fan Speed**: Supply fan speed (RPM)
- **Supply Fan PWM**: Supply fan PWM percentage (%)
- **Exhaust Fan Speed**: Exhaust fan speed (RPM)
- **Exhaust Fan PWM**: Exhaust fan PWM percentage (%)

**Room Node Sensors** (automatically discovered):

Each room is created as a **separate device** with its own sensors:
- **Temperature**: Temperature sensor for each room (°C)
- **CO2**: CO2 concentration for each room (ppm)
- **Relative Humidity**: Relative humidity for each room (%) - when available on RH sensors
- **Signal Strength**: RSSI signal strength (dBm) - for RF (wireless) sensors only (disabled by default)
- **Communication Errors**: Total communication errors - diagnostic sensor (disabled by default)

Room devices are automatically discovered and created based on the **Location** field configured for each node in your DucoBox Communication Print device.

## Requirements

- Home Assistant 2025.10.1 or newer
- A DucoBox ventilation system with Communication Print (0000-4251)
- Local network access to your device

## Compatibility

### Tested configuration
This integration has been tested and verified to work with:
- DucoBox Energy with Communication Print (0000-4251)

### Supported DucoBox models

This integration works with DucoBox models equipped with Communication Print (0000-4251), including:
- DucoBox Silent Connect
- DucoBox Focus
- DucoBox Energy Comfort (Plus)
- DucoBox Energy Sky
- DucoBox Energy Premium

**Note:** This is a fork focused on Communication Print hardware. For Connectivity Board 2.0 support, see the [upstream repository](https://github.com/degeens/ha-ducobox).

If you experience issues, please [create a GitHub issue](https://github.com/danielpetrovic/ha-ducobox/issues/new).

## Installation

### Method 1: HACS (Recommended)

The integration is available in the HACS default repository:

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click "Explore & Download Repositories"
4. Search for "DucoBox"
5. Click "Download"
6. Restart Home Assistant

### Method 2: HACS Custom Repository (Alternative)

For development versions or testing pre-release features:

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/danielpetrovic/ha-ducobox`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "DucoBox" and install it
9. Restart Home Assistant

### Method 3: Manual Installation

**Option A: Download Release (Recommended)**

1. Download the latest release from the [releases page](https://github.com/danielpetrovic/ha-ducobox/releases)
2. Extract the `custom_components/ducobox` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

**Option B: Git Clone (For Developers)**

1. Clone the repository to your preferred location:
   ```bash
   cd /share/github
   git clone https://github.com/danielpetrovic/ha-ducobox.git
   ```
2. Create a symlink from the integration to your Home Assistant `custom_components` directory:
   ```bash
   ln -s /share/github/ha-ducobox/custom_components/ducobox /config/custom_components/ducobox
   ```
3. Restart Home Assistant

This approach allows you to maintain the repository separately and easily pull updates while keeping the integration available to Home Assistant.

## Configuration

### Option 1: Automatic discovery (recommended)

The integration supports automatic discovery via Zeroconf/mDNS:

1. Make sure your DucoBox device is on the same network as Home Assistant
2. Go to **Settings** → **Devices & Services**
3. Look for a **"DucoBox discovered"** notification
4. Click **Configure** and confirm the device

### Option 2: Manual setup

If automatic discovery doesn't work or you prefer manual setup:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **DucoBox**
4. Enter the IP address or hostname of your DucoBox device
5. Click **Submit**

The integration will detect your Communication Print device and set it up automatically.

### Device Structure

The integration creates devices in the following structure:
- **Main DucoBox Device**: Contains ventilation control (fan/select) and all box sensors
- **Room Devices** (one per room): Each room sensor node becomes its own device with temperature and CO2 sensors
  - Device names come from the Location field in Communication Print node configuration
  - Example: A node with Location "Living Room" creates a "Living Room" device with "Temperature" and "CO2" sensors

All room devices are linked to the main DucoBox device via the `via_device` relationship.

## Version History

See [Releases](https://github.com/danielpetrovic/ha-ducobox/releases) for detailed changelog and version history.
