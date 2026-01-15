"""Select platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DucoBoxConfigEntry
from .const import DOMAIN
from .coordinator import DucoBoxCoordinator


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox select based on a config entry."""
    coordinator = entry.runtime_data

    entities: list[SelectEntity] = []

    # Fetch DucoBox main unit configuration (node 1)
    ducobox_config = await coordinator.api.async_get_node_config(1)
    if ducobox_config and ducobox_config.bypass_mode is not None:
        entities.append(
            DucoBoxBypassModeSelect(
                coordinator,
                entry,
                int(ducobox_config.bypass_mode.val),
            )
        )

    async_add_entities(entities)


class DucoBoxBypassModeSelect(CoordinatorEntity[DucoBoxCoordinator], SelectEntity):
    """Select entity for bypass mode configuration."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:valve"
    _attr_translation_key = "ducobox_bypass_mode"

    # Map option labels to API values
    _option_to_value = {
        "automatic": 0,
        "closed": 1,
        "open": 2,
    }
    _value_to_option = {v: k for k, v in _option_to_value.items()}

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        entry: DucoBoxConfigEntry,
        current_value: int,
    ) -> None:
        """Initialize bypass mode select."""
        super().__init__(coordinator)

        self._entry = entry
        self._current_value = current_value

        # Set options
        self._attr_options = list(self._option_to_value.keys())

        # Set unique ID (same as the old number entity to preserve entity)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ducobox_bypass_mode"
        )

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
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self._value_to_option.get(self._current_value, "automatic")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self._option_to_value.get(option)
        if value is not None:
            success = await self.coordinator.api.async_set_node_config(
                1, "BypassMode", value
            )
            if success:
                self._current_value = value
                self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Config data is fetched separately, just trigger state update
        self.async_write_ha_state()
