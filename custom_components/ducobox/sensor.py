"""Sensor platform for DucoBox."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONF_HOST,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import UTC

from . import DucoBoxConfigEntry
from .const import DOMAIN, DUCOBOX_VENTILATION_MODES
from .coordinator import DucoBoxCoordinator
from .entity import DucoBoxEntity
from .models import DucoBoxData, DucoBoxNodeData


@dataclass(frozen=True, kw_only=True)
class DucoBoxSensorEntityDescription(SensorEntityDescription):
    """Describes DucoBox sensor entity."""

    value_fn: Callable[[DucoBoxData], StateType | datetime]


SENSORS: tuple[DucoBoxSensorEntityDescription, ...] = (
    DucoBoxSensorEntityDescription(
        key="time_state_remain",
        translation_key="time_state_remain",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        suggested_display_precision=0,
        icon="mdi:timer-sand",
        value_fn=lambda data: (
            data.time_state_remain
            if data.time_state_remain
            and data.time_state_remain > 0
            and data.mode != "EXTN"
            else 0
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="time_state_end",
        translation_key="time_state_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-end",
        value_fn=lambda data: (
            datetime.fromtimestamp(data.time_state_end, tz=UTC)
            if data.time_state_end and data.time_state_end > 0 and data.mode != "EXTN"
            else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="state",
        translation_key="state",
        device_class=SensorDeviceClass.ENUM,
        options=[],  # Will be set dynamically from coordinator
        icon="mdi:fan",
        value_fn=lambda data: data.state,
    ),
    DucoBoxSensorEntityDescription(
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=DUCOBOX_VENTILATION_MODES,
        icon="mdi:cog",
        value_fn=lambda data: data.mode,
    ),
    DucoBoxSensorEntityDescription(
        key="flow_lvl_tgt",
        translation_key="flow_lvl_tgt",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_fn=lambda data: data.flow_lvl_tgt,
    ),
    DucoBoxSensorEntityDescription(
        key="rh",
        translation_key="rh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.rh,
    ),
    # Energy info sensors
    DucoBoxSensorEntityDescription(
        key="temp_oda",
        translation_key="temp_oda",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.energy_info.temp_oda if data.energy_info else None,
    ),
    DucoBoxSensorEntityDescription(
        key="temp_sup",
        translation_key="temp_sup",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.energy_info.temp_sup if data.energy_info else None,
    ),
    DucoBoxSensorEntityDescription(
        key="temp_eta",
        translation_key="temp_eta",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.energy_info.temp_eta if data.energy_info else None,
    ),
    DucoBoxSensorEntityDescription(
        key="temp_eha",
        translation_key="temp_eha",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.energy_info.temp_eha if data.energy_info else None,
    ),
    DucoBoxSensorEntityDescription(
        key="bypass_status",
        translation_key="bypass_status",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:valve",
        value_fn=lambda data: (
            data.energy_info.bypass_status if data.energy_info else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="filter_remaining_time",
        translation_key="filter_remaining_time",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda data: (
            data.energy_info.filter_remaining_time if data.energy_info else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="supply_fan_speed",
        translation_key="supply_fan_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda data: (
            data.energy_info.supply_fan_speed if data.energy_info else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="supply_fan_pwm",
        translation_key="supply_fan_pwm",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_fn=lambda data: (
            data.energy_info.supply_fan_pwm_percentage if data.energy_info else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="exhaust_fan_speed",
        translation_key="exhaust_fan_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda data: (
            data.energy_info.exhaust_fan_speed if data.energy_info else None
        ),
    ),
    DucoBoxSensorEntityDescription(
        key="exhaust_fan_pwm",
        translation_key="exhaust_fan_pwm",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_fn=lambda data: (
            data.energy_info.exhaust_fan_pwm_percentage if data.energy_info else None
        ),
    ),
)


_ENERGY_SENSOR_KEYS = {
    "temp_oda",
    "temp_sup",
    "temp_eta",
    "temp_eha",
    "bypass_status",
    "filter_remaining_time",
    "supply_fan_speed",
    "supply_fan_pwm",
    "exhaust_fan_speed",
    "exhaust_fan_pwm",
}

_CORE_SENSOR_KEYS = {"state", "mode", "flow_lvl_tgt", "rh"}


async def async_setup_entry(  # noqa: PLR0915
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox sensor based on a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []

    # Collect energy sensor descriptions for lazy creation; add all others now.
    energy_descriptions: dict[str, DucoBoxSensorEntityDescription] = {}

    for description in SENSORS:
        if description.key in _ENERGY_SENSOR_KEYS:
            energy_descriptions[description.key] = description
            continue
        if coordinator.data:
            value = description.value_fn(coordinator.data)
            if value is not None or description.key in _CORE_SENSOR_KEYS:
                entities.append(DucoBoxSensor(coordinator, description))

    # Track created energy sensor keys to avoid duplicates across coordinator ticks.
    created_energy_keys: set[str] = set()

    def _async_add_energy_sensors() -> None:
        """Create energy sensor entities the first time their value is non-None."""
        if not coordinator.data:
            return
        new_entities: list[SensorEntity] = []
        for key, description in energy_descriptions.items():
            if key in created_energy_keys:
                continue
            if description.value_fn(coordinator.data) is not None:
                new_entities.append(DucoBoxSensor(coordinator, description))
                created_energy_keys.add(key)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_energy_sensors))

    # Track which node IDs we've already created entities for, so the coordinator
    # listener below can add entities for nodes discovered later (e.g. weak RF
    # nodes that missed the initial boot scan).
    known_node_ids: set[int] = set()

    def _entities_for_node(node: DucoBoxNodeData) -> list[SensorEntity]:
        has_sensors = (
            (node.temp is not None and node.temp != 0)
            or (node.co2 is not None and node.co2 > 0)
            or (node.rh is not None and node.rh > 0)
            or node.trgt is not None
            or node.actl is not None
        )
        if not has_sensors:
            return []
        node_entities: list[SensorEntity] = []
        if node.temp is not None and node.temp != 0:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "temp"))
        if node.co2 is not None and node.co2 > 0:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "co2"))
        if node.rh is not None and node.rh > 0:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "rh"))
        if node.trgt is not None:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "trgt"))
        if node.actl is not None:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "actl"))
        if node.rssi_n2m is not None:
            node_entities.append(DucoBoxNodeSensor(coordinator, node, "rssi"))
        node_entities.append(DucoBoxNodeSensor(coordinator, node, "cerr"))
        return node_entities

    # Add room node sensors found at initial setup
    if coordinator.data and coordinator.data.nodes:
        for node in coordinator.data.nodes:
            node_entities = _entities_for_node(node)
            if node_entities:
                entities.extend(node_entities)
                known_node_ids.add(node.node_id)

    async_add_entities(entities)

    # Register a coordinator listener to dynamically add entities for nodes that
    # were not present during initial setup (e.g. weak RF nodes that missed the
    # initial discovery scan but appear during periodic re-discovery).
    def _async_add_new_nodes() -> None:
        if not coordinator.data or not coordinator.data.nodes:
            return
        new_entities: list[SensorEntity] = []
        for node in coordinator.data.nodes:
            if node.node_id not in known_node_ids:
                node_entities = _entities_for_node(node)
                if node_entities:
                    new_entities.extend(node_entities)
                    known_node_ids.add(node.node_id)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_nodes))


class DucoBoxSensor(DucoBoxEntity, RestoreSensor):
    """Defines a DucoBox sensor."""

    entity_description: DucoBoxSensorEntityDescription

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        description: DucoBoxSensorEntityDescription,
    ) -> None:
        """Initialize DucoBox sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self.entity_description = description
        self._last_value: StateType | datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last known value on startup."""
        # Restore BEFORE super() so _last_value is populated before CoordinatorEntity
        # registers its listener and fires write_ha_state() immediately.
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._last_value = last_data.native_value
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Always available — show last known value or unknown instead of unavailable."""
        return True

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor, falling back to last known value."""
        value = self.entity_description.value_fn(self.coordinator.data)
        opts = self.options
        if value is not None:
            # Reject placeholder values the DucoBox returns when not yet ready
            if opts and value not in opts:
                value = None
        if value is not None:
            self._last_value = value
        # Also validate cached/restored value — stale invalid values can be
        # persisted by RestoreSensor from a previous session before this fix.
        if opts and self._last_value is not None and self._last_value not in opts:
            self._last_value = None
        return self._last_value

    @property
    def options(self) -> list[str] | None:
        """Return the list of available options for enum sensors."""
        if self.entity_description.key == "state":
            return self.coordinator.ventilation_state_options
        return self.entity_description.options


class DucoBoxNodeSensor(CoordinatorEntity[DucoBoxCoordinator], RestoreSensor):
    """Defines a DucoBox node (room) sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        node: DucoBoxNodeData,
        sensor_type: str,
    ) -> None:
        """Initialize DucoBox node sensor."""
        super().__init__(coordinator)

        self._node_id = node.node_id
        self._location = node.location
        self._sensor_type = sensor_type
        self._last_value: StateType | None = None

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_node_{node.node_id}_{sensor_type}"
        )

        # Create a separate device for this room node
        main_device_serial = coordinator.device_info.serial_number
        node_identifier = f"{main_device_serial}_node_{node.node_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, node_identifier)},
            name=node.location,
            manufacturer="Duco",
            model=node.devtype,
            sw_version=node.swversion,
            serial_number=node.serialnb,
            via_device=(DOMAIN, main_device_serial),
            configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}",
        )

        # Set translation key based on sensor type
        if sensor_type == "temp":
            self._attr_translation_key = "node_temperature"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1
        elif sensor_type == "co2":
            self._attr_translation_key = "node_co2"
            self._attr_device_class = SensorDeviceClass.CO2
            self._attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "rh":
            self._attr_translation_key = "node_rh"
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1
        elif sensor_type == "trgt":
            self._attr_translation_key = "node_trgt"
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:gauge"
        elif sensor_type == "actl":
            self._attr_translation_key = "node_actl"
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:gauge"
        elif sensor_type == "rssi":
            self._attr_translation_key = "node_rssi"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = "dBm"
            self._attr_icon = "mdi:wifi-strength-2"
            self._attr_entity_registry_enabled_default = False
        elif sensor_type == "cerr":
            self._attr_translation_key = "node_cerr"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_icon = "mdi:counter"
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """Restore last known value on startup."""
        # Restore BEFORE super() so _last_value is populated before CoordinatorEntity
        # registers its listener and fires write_ha_state() immediately.
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._last_value = last_data.native_value
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Always available — show last known value or unknown instead of unavailable."""
        return True

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor, falling back to last known value."""
        value = self._current_value()
        if value is not None:
            self._last_value = value
        return self._last_value

    def _current_value(self) -> StateType | None:
        """Read the current value from coordinator data."""
        if not self.coordinator.data or not self.coordinator.data.nodes:
            return None

        # Find the node in the current data
        for node in self.coordinator.data.nodes:
            if node.node_id == self._node_id:
                if self._sensor_type == "temp":
                    if node.temp is None:
                        return None
                    # Apply temperature offset if configured
                    options = self.coordinator.config_entry.options or {}
                    offsets = options.get("temp_offset", {})
                    offset = offsets.get(str(self._node_id), 0.0)
                    return round(node.temp + offset, 1)
                if self._sensor_type == "co2":
                    return node.co2
                if self._sensor_type == "rh":
                    return node.rh
                if self._sensor_type == "trgt":
                    return node.trgt
                if self._sensor_type == "actl":
                    return node.actl
                if self._sensor_type == "rssi":
                    return node.rssi_n2m
                if self._sensor_type == "cerr":
                    return node.cerr

        return None

    @property
    def extra_state_attributes(self) -> dict[str, any] | None:
        """Return additional state attributes for diagnostic sensors."""
        if (
            self._sensor_type != "rssi"
            or not self.coordinator.data
            or not self.coordinator.data.nodes
        ):
            return None

        # Find the node in the current data
        for node in self.coordinator.data.nodes:
            if node.node_id == self._node_id:
                attrs = {}
                if node.rssi_n2h is not None:
                    attrs["rssi_to_hop"] = node.rssi_n2h
                if node.hop_via is not None and node.hop_via > 0:
                    attrs["hop_via_node"] = node.hop_via
                if node.netw:
                    attrs["network_type"] = node.netw
                return attrs or None

        return None
