"""Fan platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DucoBoxConfigEntry
from .const import DOMAIN
from .coordinator import DucoBoxCoordinator
from .entity import DucoBoxEntity
from .models import DucoBoxNodeData

# Preset mode constants
PRESET_MODE_AUTO = "Auto"
PRESET_MODE_AWAY = "Away"

# Devtypes that get per-node fan control entities
_VLV_DEVTYPES = {"VLVCO2", "VLVCO2RH"}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox fan based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([DucoBoxFan(coordinator)])

    # Track which VLV node IDs already have fan entities created.
    known_vlv_node_ids: set[int] = set()

    # Create fan entities for any VLV nodes already known at startup.
    if coordinator.data and coordinator.data.nodes:
        initial_entities = []
        for node in coordinator.data.nodes:
            if node.devtype in _VLV_DEVTYPES:
                initial_entities.append(DucoBoxNodeFan(coordinator, node))
                known_vlv_node_ids.add(node.node_id)
        if initial_entities:
            async_add_entities(initial_entities)

    @callback
    def _async_add_vlv_node_fans() -> None:
        """Create fan entities for newly discovered VLV nodes."""
        if not coordinator.data or not coordinator.data.nodes:
            return
        new_entities = []
        for node in coordinator.data.nodes:
            if node.devtype in _VLV_DEVTYPES and node.node_id not in known_vlv_node_ids:
                new_entities.append(DucoBoxNodeFan(coordinator, node))
                known_vlv_node_ids.add(node.node_id)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_vlv_node_fans))


class DucoBoxFan(DucoBoxEntity, FanEntity):
    """Defines a DucoBox fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_translation_key = "ventilation"

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
    ) -> None:
        """Initialize DucoBox fan."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_fan"

        # All available preset modes (Auto, Away, Manual 1-3, Manual 1-3 Forced)
        self._attr_preset_modes = coordinator.ventilation_state_options

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        return (
            self.coordinator.data.state != PRESET_MODE_AWAY
            if self.coordinator.data
            else True
        )

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.coordinator.data:
            return None

        # Return the target flow level as percentage (0-100)
        return self.coordinator.data.flow_lvl_tgt

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if not self.coordinator.data:
            return None

        # When in override mode (EXTN), no preset is active
        if self.coordinator.data.mode == "EXTN":
            return None

        # Return the current state as preset mode
        return self.coordinator.data.state

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the flow override percentage (0-100)."""
        await self.coordinator.async_set_flow_override(percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        # First clear any existing override so the preset can take full control
        await self.coordinator.async_set_flow_override(255)
        # Then set the preset mode
        await self.coordinator.async_set_ventilation_state(preset_mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default to Auto when turned on
            await self.coordinator.async_set_ventilation_state(PRESET_MODE_AUTO)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan (set to Away mode)."""
        await self.coordinator.async_set_ventilation_state(PRESET_MODE_AWAY)


class DucoBoxNodeFan(CoordinatorEntity[DucoBoxCoordinator], FanEntity):
    """Per-node fan entity for independently controllable VLV valves."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_translation_key = "node_ventilation"

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        node: DucoBoxNodeData,
    ) -> None:
        """Initialize node fan entity."""
        super().__init__(coordinator)

        self._node_id = node.node_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_node_{node.node_id}_fan"
        )
        self._attr_preset_modes = coordinator.ventilation_state_options

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

    def _get_node(self) -> DucoBoxNodeData | None:
        """Find this node in the current coordinator data."""
        if not self.coordinator.data or not self.coordinator.data.nodes:
            return None
        for node in self.coordinator.data.nodes:
            if node.node_id == self._node_id:
                return node
        return None

    @property
    def available(self) -> bool:
        """Always available — show last known state instead of unavailable."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if the valve is active (not in Away mode)."""
        node = self._get_node()
        if node is None:
            return True
        return node.state != PRESET_MODE_AWAY

    @property
    def percentage(self) -> int | None:
        """Return the current actual airflow percentage."""
        node = self._get_node()
        return node.actl if node else None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        node = self._get_node()
        if node is None:
            return None
        # When in override mode (EXTN), no preset is active
        if node.mode == "EXTN":
            return None
        return node.state

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the flow override percentage for this valve (0-100)."""
        await self.coordinator.async_set_node_flow_override(self._node_id, percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode for this valve."""
        # Clear any existing override first so the preset takes full control
        await self.coordinator.async_set_node_flow_override(self._node_id, 255)
        await self.coordinator.async_set_node_ventilation_state(
            self._node_id, preset_mode
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the valve."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.coordinator.async_set_node_ventilation_state(
                self._node_id, PRESET_MODE_AUTO
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the valve (set override to 0 = fully closed)."""
        await self.coordinator.async_set_node_flow_override(self._node_id, 0)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
