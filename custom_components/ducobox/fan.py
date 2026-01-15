"""Fan platform for DucoBox."""

from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DucoBoxConfigEntry
from .coordinator import DucoBoxCoordinator
from .entity import DucoBoxEntity

# Preset mode constants
PRESET_MODE_AUTO = "Auto"
PRESET_MODE_AWAY = "Away"


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: DucoBoxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DucoBox fan based on a config entry."""
    coordinator = entry.runtime_data

    async_add_entities([DucoBoxFan(coordinator)])


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
