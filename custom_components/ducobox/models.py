"""Data models for DucoBox."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DucoBoxDeviceInfo:
    """Device information from DucoBox."""

    model: str
    api_version: str
    serial_number: str
    mac_address: str


@dataclass
class DucoBoxNodeData:
    """Data from a single DucoBox node (room sensor)."""

    node_id: int
    location: str
    devtype: str
    temp: float | None = None
    co2: int | None = None
    rh: float | None = None
    state: str | None = None
    mode: str | None = None
    swversion: str | None = None  # Software version
    serialnb: str | None = None  # Serial number
    error: str | None = None  # Error status
    ovrl: int | None = None  # Override level
    netw: str | None = None  # Network type (WI = wired, RF = radio frequency)
    cntdwn: int | None = None  # Countdown timer
    endtime: int | None = None  # End time timestamp
    rssi_n2m: int | None = None  # RSSI node to main (signal strength)
    rssi_n2h: int | None = None  # RSSI node to hop (signal strength)
    hop_via: int | None = None  # Node ID that this node hops through
    asso: int | None = None  # Association status (1 = associated)
    cerr: int | None = None  # Communication error count


@dataclass
class DucoBoxEnergyInfo:
    """Energy information from DucoBox."""

    temp_oda: float | None = None  # Outdoor air temp (°C)
    temp_sup: float | None = None  # Supply air temp (°C)
    temp_eta: float | None = None  # Extract air temp (°C)
    temp_eha: float | None = None  # Exhaust air temp (°C)
    bypass_status: int | None = None  # Bypass status (%)
    filter_remaining_time: int | None = None  # Filter remaining days
    supply_fan_speed: int | None = None  # Supply fan RPM
    supply_fan_pwm_percentage: int | None = None  # Supply fan PWM (%)
    exhaust_fan_speed: int | None = None  # Exhaust fan RPM
    exhaust_fan_pwm_percentage: int | None = None  # Exhaust fan PWM (%)


@dataclass
class DucoBoxNodeConfigParam:
    """Configuration parameter for a DucoBox node."""

    val: int | float
    min: int | float
    max: int | float
    inc: int | float


@dataclass
class DucoBoxNodeConfig:
    """Configuration data for a DucoBox node."""

    node_id: int
    co2_setpoint: DucoBoxNodeConfigParam | None = None
    rh_setpoint: DucoBoxNodeConfigParam | None = None
    manual1: DucoBoxNodeConfigParam | None = None
    manual2: DucoBoxNodeConfigParam | None = None
    manual3: DucoBoxNodeConfigParam | None = None
    manual_timeout: DucoBoxNodeConfigParam | None = None
    temp_dependent: DucoBoxNodeConfigParam | None = None
    rh_delta: DucoBoxNodeConfigParam | None = None
    sensor_visu_level: DucoBoxNodeConfigParam | None = None
    auto_min: DucoBoxNodeConfigParam | None = None
    auto_max: DucoBoxNodeConfigParam | None = None
    capacity: DucoBoxNodeConfigParam | None = None
    bypass_mode: DucoBoxNodeConfigParam | None = None
    bypass_adaptive: DucoBoxNodeConfigParam | None = None
    comfort_temperature: DucoBoxNodeConfigParam | None = None
    filter_reset: DucoBoxNodeConfigParam | None = None
    calib_pin_max: DucoBoxNodeConfigParam | None = None
    calib_pout_max: DucoBoxNodeConfigParam | None = None
    calib_qout: DucoBoxNodeConfigParam | None = None
    program_mode_zone1: DucoBoxNodeConfigParam | None = None
    program_mode_zone2: DucoBoxNodeConfigParam | None = None
    location: str | None = None


@dataclass
class DucoBoxData:
    """Data from DucoBox."""

    state: str | None = None
    time_state_remain: int | None = None
    time_state_end: int | None = None
    mode: str | None = None
    flow_lvl_tgt: int | None = None
    rh: int | None = None
    energy_info: DucoBoxEnergyInfo | None = None
    nodes: list[DucoBoxNodeData] = field(default_factory=list)
