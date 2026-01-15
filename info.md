# DucoBox Integration

A Home Assistant integration for DucoBox ventilation systems using the Communication Print (0000-4251) local API.

## Features

- **Automatic device discovery** via Zeroconf/mDNS
- **Continuous percentage slider** for direct flow control (0-100%)
- **Preset modes**: Auto, Manual 1/2/3, Away
- **Comprehensive configuration entities** for all DucoBox settings
- **Room sensor discovery** - automatic detection of temperature, CO2, and humidity sensors
- **40+ entities** depending on your configuration

## Supported Hardware

- DucoBox with Communication Print (0000-4251)
- Works with: DucoBox Silent Connect, Focus, Energy Comfort/Sky/Premium

**Note:** This integration supports Communication Print only. For Connectivity Board 2.0, see the [original repository](https://github.com/degeens/ha-ducobox).

## Installation

1. Add this repository to HACS as a custom repository
2. Install "DucoBox" from HACS
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services
5. Enter your DucoBox IP address (or use automatic discovery)

For detailed documentation, see the [GitHub repository](https://github.com/danielpetrovic/ha-ducobox).
