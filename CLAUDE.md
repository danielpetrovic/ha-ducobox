# Home Assistant DucoBox Integration - AI Assistant Context

This document provides comprehensive context for AI assistants working on the DucoBox Integration for Home Assistant.

## Integration Overview

**Purpose:** Control and monitor DucoBox ventilation systems with Communication Print (0000-4251) hardware via local REST API.

**Why This Fork Exists:**
- Original upstream repository (degeens/ha-ducobox) supports Connectivity Board 2.0
- This fork adds full Communication Print support
- Upstream maintainer couldn't test Communication Print changes (doesn't have hardware)
- PR was rejected, leading to independent fork
- **Version 1.0.0** is the first independent release supporting Communication Print only

**Architecture:** Clean abstract base class pattern allows hardware-specific API implementations without affecting entity code.

## Hardware Supported

**Communication Print (0000-4251):**
- Older DucoBox connectivity hardware
- REST API over HTTP (no authentication)
- All features fully implemented and tested
- Reference device: DucoBox Energy with Communication Print

**NOT Supported:**
- Connectivity Board 2.0 (newer hardware)
- Connectivity Board 1.0 (legacy)

Users with Connectivity Board should use upstream: https://github.com/degeens/ha-ducobox

## Communication Print REST API Endpoints

### Device Detection & Info

**`GET /nodeinfoget?node=1`**
- Primary detection endpoint (must respond for integration to work)
- Returns device type, serial number, software version, location
- Required fields in response: `devtype`, `state`, `serialnb`

### Box State Data

**`GET /nodeinfoget?node=1`**
- Box ventilation state and sensor data
- Returns: `state`, `mode`, `trgt` (target flow), `rh` (humidity), `cntdwn` (countdown), `endtime`
- State codes mapped to friendly names: AUTO→Auto, MAN1→Manual 1, MAN2→Manual 2, MAN3→Manual 3, CNT1/2/3→Manual 1/2/3 Forced, EMPT→Away

**`GET /boxinfoget`**
- Energy information from main box
- Returns: `EnergyInfo` (temperatures, bypass, filter), `EnergyFan` (fan speeds/PWM)
- Temperatures returned in deciselsius (divide by 10)

### Ventilation Control

**`GET /nodesetoperstate?node=1&value=<STATE>`**
- Set ventilation state/preset mode
- State values: AUTO, MAN1, MAN2, MAN3, CNT1, CNT2, CNT3, EMPT
- Returns HTTP 200 on success (no JSON body)

**`GET /nodesetoverrule?node=<NODE_ID>&value=<0-100|255>`**
- Manual flow override (percentage slider)
- 0-100: Set specific flow percentage (triggers EXTN/Override mode)
- 255: Clear override, return to auto/preset mode
- Works for both main box (node 1) and room sensors

### Node Discovery

**`GET /nodeinfoget?node=<NODE_ID>`**
- Query individual node by ID
- Valid nodes have both `location` and `devtype` fields
- Scan ranges: 2-10 (room sensors), 50-100 (box sensors like UCRH)
- Integration uses 2-second timeout for fast scanning

**Typical Node Types:**
- UCCO2: CO2 sensor with temperature
- UCRH: Humidity sensor
- UCTEMP: Temperature-only sensor

### Box Configuration

**`GET /boxconfigget`**
- Box-level configuration parameters
- Returns `Energy` section with parameters like:
  - BypassMode, BypassAdaptive, ComfortTemperature
  - CalibPinMax, CalibPoutMax, CalibQout (airflow calibration)
  - ProgramModeZone1, ProgramModeZone2
  - FilterReset

**`GET /boxconfigset?mod=Energy&para=<PARAMETER>&value=<VALUE>`**
- Set box-level configuration
- All box params go through `Energy` module
- Returns HTTP 200 on success

**Special: ComfortTemperature**
- API stores value with 8-unit offset
- Formula: `api_value = (celsius * 10) + 8`
- Example: 20°C → API value 208

### Node Configuration

**`GET /nodeconfigget?node=<NODE_ID>`**
- Node-specific configuration for room sensors
- Returns parameters like:
  - CO2Setpoint, RHSetpoint (demand thresholds)
  - Manual1, Manual2, Manual3 (manual mode flow rates)
  - ManualTimeout (auto-return timer)
  - TempDependent, RHDelta (boolean switches)
  - SensorVisuLevel (display sensitivity)

**`GET /nodeconfigset?node=<NODE_ID>&para=<PARAMETER>&value=<VALUE>`**
- Set node-specific configuration
- Direct parameter names (no module prefix)

**Parameter Structure:**
All config parameters return object with:
- `Val`: Current value
- `Min`: Minimum allowed
- `Max`: Maximum allowed
- `Inc`: Increment step

**Main DucoBox (node 1) Special Handling:**
- Fetches BOTH `/nodeconfigget?node=1` AND `/boxconfigget`
- Merges node-level and box-level config into single DucoBoxNodeConfig object
- Box-level params (bypass, comfort temp, filter, calibration) only available for node 1

## Differential Polling Strategy

**Problem:** Simultaneous polling of box + energy + all nodes caused timeout cascades on slow devices.

**Solution:** Staggered polling with caching:

| Data Type | Frequency | Fetch Parameter | Cache When Skipped |
|-----------|-----------|-----------------|---------------------|
| Box State | Every 15s | Always fetched | N/A (always fresh) |
| Node Data | Every 9s | `fetch_nodes` conditional | Yes (uses `_cached_nodes`) |
| Energy Info | Every 60s | `fetch_energy` conditional | Yes (uses `_cached_energy`) |

**Coordinator Logic (coordinator.py):**
```python
now = time.time()

# Node data: fetch every 9 seconds
fetch_nodes = (now - self._last_nodes_fetch) >= 9
if fetch_nodes:
    self._last_nodes_fetch = now

# Energy info: fetch every 60 seconds
fetch_energy = (now - self._last_energy_fetch) >= 60
if fetch_energy:
    self._last_energy_fetch = now

# Call API with conditional flags
data = await self.api.async_get_data(
    fetch_energy=fetch_energy,
    fetch_nodes=fetch_nodes
)

# Update caches when data is fetched
if fetch_energy and data.energy_info:
    self._cached_energy = data.energy_info
if fetch_nodes and data.nodes:
    self._cached_nodes = data.nodes

# Use cache when not fetching
if not fetch_energy:
    data.energy_info = self._cached_energy
if not fetch_nodes:
    data.nodes = self._cached_nodes
```

**Timeouts:**
- Request timeout: 10 seconds (REQUEST_TIMEOUT constant in api.py)
- Node scanning timeout: 2 seconds per node
- Overall coordinator update interval: 15 seconds

**Benefits:**
- Eliminates timeout errors
- Reduces load on slow Communication Print devices
- Entities always have data (cache prevents None values)
- UI updates feel responsive (box state every 15s)

## Entity Architecture

### Device Hierarchy

**Main DucoBox Device:**
- Created from `/nodeinfoget?node=1` device info
- Contains all box-level entities
- Model name format: `{devtype} {location}` (e.g., "Duco Box Meterkast")

**Room Node Devices (one per sensor):**
- Created from `/nodeinfoget` scan results
- Linked to main device via `via_device` relationship
- Device name from `location` field (e.g., "Woonkamer", "Slaapkamer")
- Shows software version and serial number

### Entity Types

**Fan Entity (`fan.py`):**
- Domain: `fan`
- Unique entity per integration (main ventilation control)
- **Percentage Slider:** 0-100% flow override via `/nodesetoverrule`
- **Preset Modes:** Auto, Manual 1/2/3, etc. via `/nodesetoperstate`
- **Interaction:** Setting percentage clears preset, selecting preset clears override
- **Turn On:** Sets to Auto mode
- **Turn Off:** Not supported (ventilation always runs)

**Sensor Entities (`sensor.py`):**

*Main Box Sensors:*
- `flow_lvl_tgt`: Airflow Target Level (%)
- `rh`: Relative Humidity (%)
- `iaq_rh`: Air Quality Index RH (%) - NOT available on Communication Print
- `mode`: Ventilation Mode (AUTO/MANU/EXTN)
- `state`: Ventilation State (user-friendly name)
- `time_state_end`: Timestamp when current state ends
- `time_state_remain`: Remaining seconds in current state (shows 0 when override active)

*Energy Info Sensors (from /boxinfoget):*
- `temp_oda`: Outdoor Temperature (°C)
- `temp_sup`: Supply Temperature (°C)
- `temp_eta`: Extract Temperature (°C)
- `temp_eha`: Exhaust Temperature (°C)
- `bypass_status`: Bypass Status (%)
- `filter_remaining_time`: Filter days remaining
- `supply_fan_speed`: Supply fan RPM
- `supply_fan_pwm`: Supply fan PWM (%)
- `exhaust_fan_speed`: Exhaust fan RPM
- `exhaust_fan_pwm`: Exhaust fan PWM (%)

*Room Node Sensors (per room device):*
- `node_temperature`: Temperature (°C)
- `node_co2`: CO2 concentration (ppm)
- `node_rh`: Relative Humidity (%) - only if RH > 0
- `node_rssi`: Signal Strength (dBm) - diagnostic, disabled by default
- `node_cerr`: Communication Errors (count) - diagnostic, disabled by default

**Number Entities (`number.py`):**

*Main DucoBox Configuration:*
- `ducobox_auto_min`: Auto Minimum Flow (%)
- `ducobox_auto_max`: Auto Maximum Flow (%)
- `ducobox_capacity`: System Capacity
- `ducobox_manual1/2/3`: Manual Speed Levels (%)
- `ducobox_manual_timeout`: Manual Timeout (minutes)
- `ducobox_comfort_temperature`: Comfort Temperature (°C) - uses special conversion
- `ducobox_calib_pin_max`: Inlet Pressure Max (Pa)
- `ducobox_calib_pout_max`: Outlet Pressure Max (Pa)
- `ducobox_calib_qout`: Airflow Output Max (m³/h)
- `ducobox_program_mode_zone1/2`: Program Mode Zones

*Room Node Configuration:*
- `node_temp_offset`: Temperature Offset (-3.0 to +3.0°C, 0.1 steps)
- `node_co2_setpoint`: CO2 Setpoint (ppm)
- `node_rh_setpoint`: Humidity Setpoint (%)
- `node_manual1/2/3`: Manual Speed Levels per node (%)
- `node_manual_timeout`: Manual Timeout per node (minutes)
- `node_sensor_visu_level`: Sensor Visualization Level (%)

**Select Entities (`select.py`):**
- `ducobox_bypass_mode`: Bypass Mode (Automatic/Closed/Open)

**Switch Entities (`switch.py`):**

*Main DucoBox:*
- `ducobox_bypass_adaptive`: Bypass Adaptive (on/off)

*Room Nodes:*
- `node_temp_dependent`: Temperature Dependent ventilation (useful for bathrooms)
- `node_rh_delta`: Humidity Delta control

**Button Entities (`button.py`):**
- `ducobox_filter_reset`: Reset Filter Timer

### Entity Naming Conventions

**Pattern:** `{entity_type}.{device_location}_{entity_name}`

Examples:
- `fan.ventilation` (main fan control)
- `sensor.airflow_target_level` (box sensor)
- `sensor.woonkamer_temperature` (room sensor)
- `number.kantoor_co2_setpoint` (room config)

**Icon Usage:**
All entities have logical MDI icons:
- Sensors: timer, clock, thermometer, molecule-co2, water-percent, wifi, network
- Numbers: gauge, speedometer, fan-speed, thermometer
- Switches: valve, water, temperature-celsius
- Button: filter

## Room Node Discovery

**Scan Strategy:**
```python
node_ranges = [
    range(2, 11),    # Common room sensors (2-10)
    range(50, 101)   # Box sensors like UCRH (50-100)
]
```

**Valid Node Criteria:**
- Must have both `location` and `devtype` fields
- Example valid node:
  ```json
  {
    "location": "Woonkamer",
    "devtype": "UCCO2",
    "temp": 212,        // 21.2°C (deciselsius)
    "co2": 850,         // 850 ppm
    "rh": 55,           // 55%
    "serialnb": "12345678",
    "swversion": "V1.2.3"
  }
  ```

**Fast Scanning:**
- 2-second timeout per node request
- Skips nodes that timeout or return invalid data
- Typical installation: 6-10 room sensors discovered

**Signal Strength (RF sensors):**
- `rssi_n2m`: RSSI Node to Master
- `rssi_n2h`: RSSI Node to Hop
- `hop_via`: Node ID this sensor hops through (0 = direct)
- Used for diagnostic network topology visualization

## Configuration Entities Deep Dive

### Temperature Offset Calibration

**Purpose:** Adjust individual room sensor temperature readings.

**Range:** -3.0°C to +3.0°C in 0.1°C increments

**API:** `/nodeconfigset?node=<NODE_ID>&para=TempOffset&value=<VALUE>`

**Implementation:**
- Number entity with native unit `°C`
- Device class: `temperature`
- Optimistic updates for immediate UI feedback

### Box-Level vs Node-Level Parameters

**Box-Level (only node 1):**
- Bypass settings
- Comfort temperature
- Calibration parameters
- Filter reset
- Program mode zones

**Node-Level (all nodes including node 1):**
- CO2/RH setpoints
- Manual speed levels
- Manual timeout
- Sensor visualization
- Temperature dependent / RH delta switches

**Code Pattern:**
```python
box_level_params = {
    "BypassMode", "BypassAdaptive", "ComfortTemperature",
    "FilterReset", "CalibPinMax", "CalibPoutMax", "CalibQout",
    "ProgramModeZone1", "ProgramModeZone2"
}

if node_id == 1 and parameter in box_level_params:
    # Use /boxconfigset with mod=Energy
    url = f"{base_url}/boxconfigset"
    params = {"mod": "Energy", "para": parameter, "value": int(value)}
else:
    # Use /nodeconfigset
    url = f"{base_url}/nodeconfigset"
    params = {"node": node_id, "para": parameter, "value": int(value)}
```

## Code Architecture

### Abstract Base Class Pattern

**Why It's Excellent:**
```python
# api.py structure
class DucoApiBase(ABC):
    # Abstract methods define contract
    @abstractmethod
    async def async_get_device_info(self) -> DucoBoxDeviceInfo:
        pass

    # 8 more abstract methods...

class DucoCommunicationPrintApi(DucoApiBase):
    # Concrete implementation
    async def async_get_device_info(self) -> DucoBoxDeviceInfo:
        # Communication Print-specific code
        pass
```

**Benefits:**
1. **Entity code is hardware-agnostic** - uses only abstract base class
2. **No isinstance() checks** anywhere in codebase
3. **Easy to add new hardware** - just implement abstract methods
4. **Easy to remove hardware** - surgical cut, no ripple effects
5. **Type safety** - mypy can verify contract compliance

### Files Overview

| File | Purpose | Hardware-Specific? |
|------|---------|-------------------|
| `api.py` | API clients | ✅ Yes (Communication Print impl) |
| `config_flow.py` | Setup flow | ❌ No (uses abstract base) |
| `coordinator.py` | Data polling | ❌ No (uses abstract base) |
| `sensor.py` | Sensor entities | ❌ No (conditional creation) |
| `number.py` | Number entities | ❌ No (conditional creation) |
| `select.py` | Select entities | ❌ No (conditional creation) |
| `switch.py` | Switch entities | ❌ No (conditional creation) |
| `button.py` | Button entities | ❌ No (conditional creation) |
| `fan.py` | Fan entity | ❌ No (uses abstract methods) |

**No entity file imports `DucoCommunicationPrintApi`** - only imports `DucoApiBase`.

## Development Notes

### Why Connectivity Board Was Removed (v1.0.0)

**Original Situation:**
- Repository had 2 API implementations: Connectivity Board + Communication Print
- Connectivity Board had ~230 lines of stub code (5 of 9 methods returned None/False/"not yet implemented")
- Only Communication Print was fully implemented and tested
- Maintainer has Communication Print hardware only

**Problems:**
- Can't test Connectivity Board changes
- Can't verify upstream contributions
- Stub code adds maintenance burden
- Misleading to users (advertised but incomplete)

**Solution:**
- Remove entire `DucoConnectivityBoardApi` class
- Simplify detection to Communication Print only
- Update all documentation and branding
- Release as v1.0.0 (first independent release)

**Code Impact:**
- Deleted 231 lines from api.py
- Zero changes needed in any entity file (✅ abstraction worked!)
- Updated README, translations, manifest

### Testing Requirements

**Integration Setup:**
1. Delete existing DucoBox integration from HA
2. Re-add via config flow (Settings → Integrations)
3. Enter Communication Print IP address
4. Verify detection logs: "Detected Duco Communication Print API"

**Entity Creation Verification:**
- Main DucoBox device created with ~20-30 entities
- 6-10 room devices created (depends on installation)
- Each room has 2-4 sensors (temp, CO2, RH if available, diagnostics disabled)

**Functional Testing:**
- Change ventilation state → verify API call works
- Adjust percentage slider → verify override mode
- Modify config values → verify they persist
- Check logs for errors

**Performance Testing:**
- Monitor coordinator updates every 15 seconds
- Verify no timeout errors
- Check node data updates every 9 seconds
- Check energy data updates every 60 seconds

### Common Development Patterns

**Adding New Number Entity:**
```python
# 1. Check if config param exists in DucoBoxNodeConfig
if config and config.new_parameter:
    param = config.new_parameter
    entities.append(
        DucoBoxNumberEntity(
            coordinator=coordinator,
            device_id=device_id,
            node_id=node_id,
            parameter="NewParameter",
            name="Friendly Name",
            icon="mdi:icon-name",
            native_min_value=param.min,
            native_max_value=param.max,
            native_step=param.inc,
            native_unit_of_measurement="unit",
        )
    )

# 2. Set method in number.py already handles it (no change needed)
await self.coordinator.api.async_set_node_config(
    self._node_id, self._parameter, value
)
```

**Adding New Sensor:**
```python
# Check if data exists before creating
if coordinator.data.new_field is not None:
    entities.append(
        DucoBoxSensor(
            coordinator=coordinator,
            device_id=device_id,
            sensor_type="new_field",
            name="New Field Name",
            icon="mdi:icon",
            native_unit_of_measurement="unit",
            device_class=SensorDeviceClass.TYPE,
            state_class=SensorStateClass.MEASUREMENT,
        )
    )
```

**Entity Lifecycle:**
1. Coordinator polls API
2. Data updated in `coordinator.data`
3. Entity reads data via `self.coordinator.data.field`
4. Entity updates state automatically (coordinator notifies listeners)

### Release Process

**GitHub Release Naming Convention:**
- Release title format: `DucoBox Integration v{VERSION}` (e.g., "DucoBox Integration v1.0.1")
- Tag format: `v{VERSION}` (e.g., "v1.0.1")

**Steps to Create a Release:**
1. Update version in `custom_components/ducobox/manifest.json`
2. Commit: `git commit -m "Bump version to {VERSION}"`
3. Create tag: `git tag v{VERSION}`
4. Push: `git push origin main && git push origin v{VERSION}`
5. Create GitHub release: `gh release create v{VERSION} --title "DucoBox Integration v{VERSION}" --notes "Release notes here"`

**HACS Note:** HACS displays the README from the release tag, not from the main branch. Documentation updates require a new release to be visible in HACS.

### Version History

**v1.0.1** (2026-01-22)
- Documentation updates for HACS default repository listing
- Updated badges to reflect HACS default repository status
- Expanded installation instructions

**v1.0.0** (2026-01-15)
- First independent release of danielpetrovic/ha-ducobox fork
- ❌ **BREAKING:** Removed Connectivity Board 2.0 support
- Rebranded as Communication Print-only integration
- Removed Connectivity Board-specific features (iaq_rh sensor)
- Replaced all "legacy" terminology with "Communication Print"
- Updated all documentation and URLs to danielpetrovic/ha-ducobox fork
- Clean surgical removal (231 lines deleted from api.py, zero entity changes)

**Pre-fork Development**
- ➕ Added Communication Print support
- ➕ Added differential polling strategy
- ➕ Added comprehensive configuration entities
- ➕ Added room node discovery
- ➕ Added Zeroconf discovery
- 📝 Expanded from 7 to 40+ entities
- All development done while still part of degeens/ha-ducobox

### Original Source

**Original Repository:** https://github.com/degeens/ha-ducobox
- Maintainer: @degeens
- Focus: Connectivity Board 2.0 hardware
- Status: Active, supports Connectivity Board only

**This Independent Fork:** https://github.com/danielpetrovic/ha-ducobox
- Maintainer: @danielpetrovic
- Focus: Communication Print (0000-4251) hardware only
- First release: v1.0.0 (2026-01-15)
- **Permanent independent fork** - changes will never be merged back
- Reason for split: Original maintainer couldn't test Communication Print changes (doesn't have hardware)

**For Users:**
- Communication Print (0000-4251) users → Use this fork
- Connectivity Board users → Use original repository
- These are separate projects with no cross-compatibility

## API Response Examples

### Device Info
```json
{
  "devtype": "0000-4251",
  "location": "Meterkast",
  "serialnb": "12345678",
  "swversion": "V1.2.3",
  "state": "AUTO",
  "mode": "AUTO"
}
```

### Box State Data
```json
{
  "state": "MAN1",
  "mode": "MANU",
  "trgt": 75,
  "rh": 55,
  "cntdwn": 3600,
  "endtime": 1234567890
}
```

### Energy Info
```json
{
  "EnergyInfo": {
    "TempODA": 150,           // 15.0°C
    "TempSUP": 210,           // 21.0°C
    "TempETA": 215,           // 21.5°C
    "TempEHA": 145,           // 14.5°C
    "BypassStatus": 50,       // 50%
    "FilterRemainingTime": 45 // 45 days
  },
  "EnergyFan": {
    "SupplyFanSpeed": 1500,   // 1500 RPM
    "SupplyFanPwmPercentage": 65,
    "ExhaustFanSpeed": 1450,  // 1450 RPM
    "ExhaustFanPwmPercentage": 63
  }
}
```

### Node Info (Room Sensor)
```json
{
  "location": "Woonkamer",
  "devtype": "UCCO2",
  "temp": 212,              // 21.2°C
  "co2": 850,               // 850 ppm
  "rh": 55,                 // 55%
  "state": "AUTO",
  "mode": "AUTO",
  "swversion": "V1.2.3",
  "serialnb": "87654321",
  "rssi_n2m": -45,          // -45 dBm
  "hop_via": 0,             // Direct connection
  "cerr": 2                 // 2 comm errors
}
```

### Node Config
```json
{
  "CO2Setpoint": {
    "Val": 900,
    "Min": 400,
    "Max": 2000,
    "Inc": 50
  },
  "RHSetpoint": {
    "Val": 60,
    "Min": 30,
    "Max": 90,
    "Inc": 5
  },
  "Manual1": {
    "Val": 30,
    "Min": 0,
    "Max": 100,
    "Inc": 5
  }
}
```

## Troubleshooting

**Integration won't detect device:**
- Check device is Communication Print (0000-4251)
- Verify `/nodeinfoget?node=1` endpoint responds
- Check firewall allows HTTP access to device
- Connectivity Board devices not supported (use upstream)

**Entities not appearing:**
- Energy sensors: Check `/boxinfoget` endpoint works
- Room sensors: Check nodes 2-10 respond to `/nodeinfoget`
- Config entities: Check `/boxconfigget` and `/nodeconfigget` work

**Timeout errors:**
- Differential polling should prevent this
- Check device isn't overloaded with other requests
- Verify network latency is reasonable (<500ms)

**Configuration changes not saving:**
- Check `/boxconfigset` or `/nodeconfigset` return HTTP 200
- Verify parameter name matches API exactly (case sensitive)
- Some parameters may have min/max validation on device side
