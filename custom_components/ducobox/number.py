"""Number platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import CONF_HOST, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DucoBoxConfigEntry
from .const import DOMAIN
from .coordinator import DucoBoxCoordinator
from .models import DucoBoxNodeConfigParam, DucoBoxNodeData

CONF_TEMP_OFFSET = "temp_offset"


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox number entities."""
    coordinator = entry.runtime_data

    entities: list[NumberEntity] = []

    # Add temperature offset number entities for each room with temperature sensor
    if coordinator.data and coordinator.data.nodes:
        for node in coordinator.data.nodes:
            if node.temp is not None and node.temp != 0:
                entities.append(
                    DucoBoxTemperatureOffsetNumber(coordinator, node, entry)
                )

    # Fetch DucoBox main unit configuration (node 1)
    ducobox_config = await coordinator.api.async_get_node_config(1)
    if ducobox_config:
        # Add AutoMin, AutoMax, and Capacity for main DucoBox
        if ducobox_config.auto_min:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "AutoMin",
                    "auto_min",
                    ducobox_config.auto_min,
                    PERCENTAGE,
                    "mdi:fan-auto",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.auto_max:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "AutoMax",
                    "auto_max",
                    ducobox_config.auto_max,
                    PERCENTAGE,
                    "mdi:fan-auto",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.capacity:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "Capacity",
                    "capacity",
                    ducobox_config.capacity,
                    "m³/h",
                    "mdi:air-filter",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.comfort_temperature:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "ComfortTemperature",
                    "comfort_temperature",
                    ducobox_config.comfort_temperature,
                    UnitOfTemperature.CELSIUS,
                    "mdi:thermometer",
                    mode=NumberMode.BOX,
                    use_deciselsius=True,
                    temperature_offset=8,
                )
            )

        if ducobox_config.calib_pin_max:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "CalibPinMax",
                    "calib_pin_max",
                    ducobox_config.calib_pin_max,
                    "PWM",
                    "mdi:gauge",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.calib_pout_max:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "CalibPoutMax",
                    "calib_pout_max",
                    ducobox_config.calib_pout_max,
                    "PWM",
                    "mdi:gauge",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.calib_qout:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "CalibQout",
                    "calib_qout",
                    ducobox_config.calib_qout,
                    "m³/h",
                    "mdi:air-filter",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.program_mode_zone1:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "ProgramModeZone1",
                    "program_mode_zone1",
                    ducobox_config.program_mode_zone1,
                    None,
                    "mdi:home-thermometer",
                    mode=NumberMode.BOX,
                )
            )

        if ducobox_config.program_mode_zone2:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "ProgramModeZone2",
                    "program_mode_zone2",
                    ducobox_config.program_mode_zone2,
                    None,
                    "mdi:home-thermometer",
                    mode=NumberMode.BOX,
                )
            )

        # Add Manual speed levels for main DucoBox
        for i, param in enumerate(
            [ducobox_config.manual1, ducobox_config.manual2, ducobox_config.manual3], 1
        ):
            if param:
                entities.append(
                    DucoBoxMainConfigNumber(
                        coordinator,
                        entry,
                        f"Manual{i}",
                        f"manual{i}",
                        param,
                        PERCENTAGE,
                        "mdi:fan-speed-1"
                        if i == 1
                        else "mdi:fan-speed-2"
                        if i == 2
                        else "mdi:fan-speed-3",
                        mode=NumberMode.BOX,
                    )
                )

        # Add Manual Timeout for main DucoBox
        if ducobox_config.manual_timeout:
            entities.append(
                DucoBoxMainConfigNumber(
                    coordinator,
                    entry,
                    "ManualTimeout",
                    "manual_timeout",
                    ducobox_config.manual_timeout,
                    "min",
                    "mdi:timer-outline",
                    mode=NumberMode.BOX,
                )
            )

    # Add node-specific configuration entities
    if coordinator.data and coordinator.data.nodes:
        for node in coordinator.data.nodes:
            # Add configuration entities for UCCO2 and UCRH nodes
            if node.devtype and ("UCCO2" in node.devtype or "UCRH" in node.devtype):
                # Fetch node configuration from the API
                node_config = await coordinator.api.async_get_node_config(node.node_id)

                if node_config:
                    # Add CO2 Setpoint number (UCCO2 only)
                    if node_config.co2_setpoint:
                        entities.append(
                            DucoBoxNodeConfigNumber(
                                coordinator,
                                node,
                                entry,
                                "CO2Setpoint",
                                "co2_setpoint",
                                node_config.co2_setpoint,
                                "ppm",
                                "mdi:molecule-co2",
                                mode=NumberMode.BOX,
                            )
                        )

                    # Add RH Setpoint number (UCRH only)
                    if node_config.rh_setpoint:
                        entities.append(
                            DucoBoxNodeConfigNumber(
                                coordinator,
                                node,
                                entry,
                                "RHSetpoint",
                                "rh_setpoint",
                                node_config.rh_setpoint,
                                PERCENTAGE,
                                "mdi:water-percent",
                                mode=NumberMode.BOX,
                            )
                        )

                    # Add Manual speed levels
                    for i, param in enumerate(
                        [node_config.manual1, node_config.manual2, node_config.manual3],
                        1,
                    ):
                        if param:
                            entities.append(
                                DucoBoxNodeConfigNumber(
                                    coordinator,
                                    node,
                                    entry,
                                    f"Manual{i}",
                                    f"manual{i}",
                                    param,
                                    PERCENTAGE,
                                    "mdi:fan-speed-1"
                                    if i == 1
                                    else "mdi:fan-speed-2"
                                    if i == 2
                                    else "mdi:fan-speed-3",
                                    mode=NumberMode.BOX,
                                )
                            )

                    # Add Manual Timeout
                    if node_config.manual_timeout:
                        entities.append(
                            DucoBoxNodeConfigNumber(
                                coordinator,
                                node,
                                entry,
                                "ManualTimeout",
                                "manual_timeout",
                                node_config.manual_timeout,
                                "min",
                                "mdi:timer-outline",
                                mode=NumberMode.BOX,
                            )
                        )

                    # Add Sensor Visualization Level
                    if node_config.sensor_visu_level:
                        entities.append(
                            DucoBoxNodeConfigNumber(
                                coordinator,
                                node,
                                entry,
                                "SensorVisuLevel",
                                "sensor_visu_level",
                                node_config.sensor_visu_level,
                                PERCENTAGE,
                                "mdi:gauge",
                                mode=NumberMode.BOX,
                            )
                        )

    async_add_entities(entities)


class DucoBoxTemperatureOffsetNumber(
    CoordinatorEntity[DucoBoxCoordinator], NumberEntity
):
    """Temperature offset number entity for a DucoBox node."""

    _attr_has_entity_name = True
    _attr_native_min_value = -3.0
    _attr_native_max_value = 3.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        node: DucoBoxNodeData,
        entry: DucoBoxConfigEntry,
    ) -> None:
        """Initialize temperature offset number."""
        super().__init__(coordinator)

        self._node_id = node.node_id
        self._location = node.location
        self._entry = entry

        # Track optimistic value for immediate UI updates
        self._optimistic_value: float | None = None

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_node_{node.node_id}_temp_offset"
        )

        # Set translation key
        self._attr_translation_key = "node_temp_offset"

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

    @property
    def native_value(self) -> float:
        """Return the current offset value."""
        # Use optimistic value if set (for immediate UI updates)
        if self._optimistic_value is not None:
            return self._optimistic_value

        options = self._entry.options or {}
        offsets = options.get(CONF_TEMP_OFFSET, {})
        return offsets.get(str(self._node_id), 0.0)

    async def async_set_native_value(self, value: float) -> None:
        """Set the offset value."""
        # Set optimistic value for immediate UI update
        self._optimistic_value = value
        self.async_write_ha_state()

        # Persist to config entry (for restarts)
        entry = self.coordinator.config_entry
        options = dict(entry.options or {})
        offsets = dict(options.get(CONF_TEMP_OFFSET, {}))
        offsets[str(self._node_id)] = value
        options[CONF_TEMP_OFFSET] = offsets

        self.hass.config_entries.async_update_entry(
            entry,
            options=options,
        )

        # Clear optimistic value after successful save
        # so future reads come from config entry options
        self._optimistic_value = None
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Temperature offset doesn't come from coordinator data, just trigger state update
        self.async_write_ha_state()


class DucoBoxNodeConfigNumber(CoordinatorEntity[DucoBoxCoordinator], NumberEntity):
    """Number entity for UCCO2 node configuration parameters."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        node: DucoBoxNodeData,
        entry: DucoBoxConfigEntry,
        parameter_name: str,
        translation_key: str,
        param: DucoBoxNodeConfigParam,
        unit: str | None,
        icon: str | None,
        mode: NumberMode = NumberMode.SLIDER,
    ) -> None:
        """Initialize node configuration number."""
        super().__init__(coordinator)

        self._node_id = node.node_id
        self._location = node.location
        self._entry = entry
        self._parameter_name = parameter_name

        # Set min/max/step from API data
        self._attr_native_min_value = param.min
        self._attr_native_max_value = param.max
        self._attr_native_step = param.inc
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_mode = mode

        # Set display precision to 0 for whole number units (no decimals)
        if unit in (PERCENTAGE, "ppm", "min"):
            self._attr_suggested_display_precision = 0

        # Store the current value
        self._current_value = param.val

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_node_{node.node_id}_{translation_key}"
        )

        # Set translation key
        self._attr_translation_key = f"node_{translation_key}"

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

    @property
    def native_value(self) -> int | float | None:
        """Return the current value."""
        # Return as int if it's a whole number to avoid decimal display
        if self._current_value is not None and self._current_value == int(
            self._current_value
        ):
            return int(self._current_value)
        return self._current_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the configuration value."""
        # Update the API
        success = await self.coordinator.api.async_set_node_config(
            self._node_id, self._parameter_name, value
        )

        if success:
            # Update stored current value and trigger state update
            self._current_value = value
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Config data is fetched separately, just trigger state update
        self.async_write_ha_state()


class DucoBoxMainConfigNumber(CoordinatorEntity[DucoBoxCoordinator], NumberEntity):
    """Number entity for main DucoBox configuration parameters."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        entry: DucoBoxConfigEntry,
        parameter_name: str,
        translation_key: str,
        param: DucoBoxNodeConfigParam,
        unit: str | None,
        icon: str | None,
        mode: NumberMode = NumberMode.SLIDER,
        use_deciselsius: bool = False,
        temperature_offset: int = 0,
    ) -> None:
        """Initialize main DucoBox configuration number."""
        super().__init__(coordinator)

        self._entry = entry
        self._parameter_name = parameter_name
        self._use_deciselsius = use_deciselsius
        self._temperature_offset = temperature_offset

        # If using deciselsius conversion, apply offset and divide by 10 for display
        # Formula: (value - offset) / 10 = °C
        divisor = 10 if use_deciselsius else 1

        # Set min/max/step from API data
        self._attr_native_min_value = (param.min - temperature_offset) / divisor
        self._attr_native_max_value = (param.max - temperature_offset) / divisor
        self._attr_native_step = param.inc / divisor
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_mode = mode

        # Set display precision to 0 for whole number units (no decimals)
        if unit in (PERCENTAGE, "ppm", "min"):
            self._attr_suggested_display_precision = 0

        # Store the current value (in API units - with offset if applicable)
        self._current_value = param.val

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ducobox_{translation_key}"
        )

        # Set translation key
        self._attr_translation_key = f"ducobox_{translation_key}"

        # Attach to the main DucoBox device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_info.serial_number)},
            manufacturer="Duco",
            name="DucoBox",
            model=coordinator.device_info.model,
            sw_version=coordinator.device_info.api_version,
            serial_number=coordinator.device_info.serial_number,
            connections=(
                {(CONNECTION_NETWORK_MAC, coordinator.device_info.mac_address)}
                if coordinator.device_info.mac_address
                else set()
            ),
            configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self) -> int | float | None:
        """Return the current value."""
        if self._current_value is None:
            return None

        # Convert from deciselsius to Celsius if needed
        # Formula: (value - offset) / 10 = °C
        if self._use_deciselsius:
            value = (self._current_value - self._temperature_offset) / 10
        else:
            value = self._current_value

        # Return as int if it's a whole number to avoid decimal display
        if value == int(value):
            return int(value)
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Set the configuration value."""
        # Convert from Celsius to deciselsius if needed
        # Formula: °C * 10 + offset = value
        if self._use_deciselsius:
            api_value = value * 10 + self._temperature_offset
        else:
            api_value = value

        # Update the API (node 1 is the main DucoBox)
        success = await self.coordinator.api.async_set_node_config(
            1, self._parameter_name, api_value
        )

        if success:
            # Update stored current value (store in API units) and trigger state update
            self._current_value = api_value
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Config data is fetched separately, just trigger state update
        self.async_write_ha_state()
