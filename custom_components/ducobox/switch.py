"""Switch platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DucoBoxConfigEntry
from .const import DOMAIN
from .coordinator import DucoBoxCoordinator
from .models import DucoBoxNodeConfigParam, DucoBoxNodeData


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox switch entities."""
    coordinator = entry.runtime_data

    entities: list[SwitchEntity] = []

    # Fetch DucoBox main unit configuration (node 1)
    ducobox_config = await coordinator.api.async_get_node_config(1)
    if ducobox_config:
        # Add BypassAdaptive switch for main DucoBox
        if ducobox_config.bypass_adaptive is not None:
            entities.append(
                DucoBoxMainConfigSwitch(
                    coordinator,
                    entry,
                    "BypassAdaptive",
                    "bypass_adaptive",
                    ducobox_config.bypass_adaptive,
                    "mdi:valve",
                )
            )

    # Add configuration switches for UCCO2 and UCRH nodes
    if coordinator.data and coordinator.data.nodes:
        for node in coordinator.data.nodes:
            node_config = None

            if node.devtype and ("UCCO2" in node.devtype or "UCRH" in node.devtype):
                # Fetch node configuration from the API
                node_config = await coordinator.api.async_get_node_config(node.node_id)

            if node_config:
                # Add TempDependent switch for UCCO2 nodes
                if node_config.temp_dependent is not None:
                    entities.append(
                        DucoBoxNodeConfigSwitch(
                            coordinator,
                            node,
                            entry,
                            "TempDependent",
                            "temp_dependent",
                            node_config.temp_dependent,
                            "mdi:thermometer-auto",
                        )
                    )

                # Add RHDelta switch for UCRH nodes
                if node_config.rh_delta is not None:
                    entities.append(
                        DucoBoxNodeConfigSwitch(
                            coordinator,
                            node,
                            entry,
                            "RHDelta",
                            "rh_delta",
                            node_config.rh_delta,
                            "mdi:delta",
                        )
                    )

    async_add_entities(entities)


class DucoBoxNodeConfigSwitch(CoordinatorEntity[DucoBoxCoordinator], SwitchEntity):
    """Switch entity for node configuration settings."""

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
        icon: str,
    ) -> None:
        """Initialize node configuration switch."""
        super().__init__(coordinator)

        self._node_id = node.node_id
        self._location = node.location
        self._entry = entry
        self._parameter_name = parameter_name
        self._attr_icon = icon

        # Store the current value
        self._current_value = bool(param.val)

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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._current_value

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set the switch state."""
        # Update the API (1 for on, 0 for off)
        success = await self.coordinator.api.async_set_node_config(
            self._node_id, self._parameter_name, 1 if state else 0
        )

        if success:
            # Update stored current value and trigger state update
            self._current_value = state
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Config data is fetched separately, just trigger state update
        self.async_write_ha_state()


class DucoBoxMainConfigSwitch(CoordinatorEntity[DucoBoxCoordinator], SwitchEntity):
    """Switch entity for main DucoBox configuration settings."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DucoBoxCoordinator,
        entry: DucoBoxConfigEntry,
        parameter_name: str,
        translation_key: str,
        param: DucoBoxNodeConfigParam,
        icon: str,
    ) -> None:
        """Initialize main DucoBox configuration switch."""
        super().__init__(coordinator)

        self._entry = entry
        self._parameter_name = parameter_name
        self._attr_icon = icon

        # Store the current value
        self._current_value = bool(param.val)

        # Set unique ID
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_ducobox_{translation_key}"
        )

        # Set translation key
        self._attr_translation_key = f"ducobox_{translation_key}"

        # Attach to the main DucoBox device
        from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._current_value

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set the switch state."""
        # Update the API (1 for on, 0 for off) - node 1 is the main DucoBox
        success = await self.coordinator.api.async_set_node_config(
            1, self._parameter_name, 1 if state else 0
        )

        if success:
            # Update stored current value and trigger state update
            self._current_value = state
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Config data is fetched separately, just trigger state update
        self.async_write_ha_state()
