"""Button platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
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
    """Set up DucoBox button entities."""
    coordinator = entry.runtime_data

    entities: list[ButtonEntity] = []

    # Fetch DucoBox main unit configuration (node 1)
    ducobox_config = await coordinator.api.async_get_node_config(1)
    if ducobox_config:
        # Add FilterReset button for main DucoBox
        if ducobox_config.filter_reset is not None:
            entities.append(
                DucoBoxFilterResetButton(
                    coordinator,
                    entry,
                )
            )

    async_add_entities(entities)


class DucoBoxFilterResetButton(CoordinatorEntity[DucoBoxCoordinator], ButtonEntity):
    """Button entity to reset the filter timer."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:air-filter"

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        entry: DucoBoxConfigEntry,
    ) -> None:
        """Initialize filter reset button."""
        super().__init__(coordinator)

        self._entry = entry

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ducobox_filter_reset"
        )

        # Set translation key
        self._attr_translation_key = "ducobox_filter_reset"

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

    async def async_press(self) -> None:
        """Handle the button press - reset the filter timer."""
        # Send the reset command to the API (node 1 is the main DucoBox)
        # FilterReset parameter with value 1 triggers the reset
        await self.coordinator.api.async_set_node_config(1, "FilterReset", 1)
