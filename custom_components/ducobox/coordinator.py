"""DataUpdateCoordinator for DucoBox."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import ClientError, ServerTimeoutError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DucoApiBase
from .const import DOMAIN
from .models import DucoBoxData, DucoBoxDeviceInfo

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class DucoBoxCoordinator(DataUpdateCoordinator[DucoBoxData]):
    """Class to manage fetching DucoBox data."""

    config_entry: ConfigEntry
    device_info: DucoBoxDeviceInfo
    ventilation_state_options: list[str]

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: DucoApiBase,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=config_entry,
            always_update=False,
        )
        self.api = api
        self.config_entry = config_entry
        self._fetch_energy_next = (
            False  # alternate: nodes first on startup, then energy, then nodes...
        )
        self._cached_energy = None
        self._cached_nodes = []

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        try:
            self.device_info = await self.api.async_get_device_info()
            self.ventilation_state_options = (
                await self.api.async_get_ventilation_state_options()
            )
        except ClientError as err:
            msg = f"Failed to setup coordinator: {err}"
            raise UpdateFailed(msg) from err

    async def _async_update_data(self) -> DucoBoxData:
        """Update the data."""
        # Alternate between nodes and energy each tick to avoid simultaneous
        # requests overwhelming the DucoBox embedded HTTP server.
        # Nodes first on startup so room entities are created before energy entities.
        fetch_energy = self._fetch_energy_next
        fetch_nodes = not fetch_energy

        try:
            data = await self.api.async_get_data(
                fetch_energy=fetch_energy,
                fetch_nodes=fetch_nodes,
            )

            # Only flip after success — failed ticks retry the same type next tick
            self._fetch_energy_next = not self._fetch_energy_next

            if fetch_energy:
                if data.energy_info is not None:
                    # Only update cache when we got real data — keep old cache on failure
                    self._cached_energy = data.energy_info
                elif self._cached_energy is not None:
                    # Restore cached value when energy fetch returned nothing
                    data.energy_info = self._cached_energy
            elif self._cached_energy is not None:
                data.energy_info = self._cached_energy

            if fetch_nodes:
                # Merge live results with cache: keep stale data for nodes that
                # didn't respond this tick so sensors show last known value
                # instead of unknown.
                if self._cached_nodes:
                    live = {n.node_id: n for n in data.nodes}
                    merged = []
                    for cached in self._cached_nodes:
                        merged.append(live.get(cached.node_id, cached))
                    # Also add any newly discovered nodes not in the old cache
                    cached_ids = {n.node_id for n in self._cached_nodes}
                    merged.extend(n for n in data.nodes if n.node_id not in cached_ids)
                    data.nodes = merged
                self._cached_nodes = data.nodes
            elif self._cached_nodes:
                data.nodes = self._cached_nodes

        except (TimeoutError, ServerTimeoutError) as err:
            # Timeout errors are common due to network issues - log at debug level
            # and only raise UpdateFailed without logging error
            _LOGGER.debug("Timeout fetching data from DucoBox: %s", err)
            msg = f"Timeout connecting to DucoBox: {err}"
            raise UpdateFailed(msg) from err
        except ClientError as err:
            # Other client errors might indicate real problems - log at warning level
            _LOGGER.warning("Error fetching data from DucoBox: %s", err)
            msg = f"Failed to update coordinator data: {err}"
            raise UpdateFailed(msg) from err

        return data

    async def async_set_ventilation_state(self, state: str) -> None:
        """Set the ventilation state."""
        try:
            success = await self.api.async_set_ventilation_state(state)
            if not success:
                msg = f"Failed to set ventilation state to {state}"
                raise HomeAssistantError(msg)

            await self.async_request_refresh()
        except ClientError as err:
            msg = f"Failed to set ventilation state to {state}: {err}"
            raise HomeAssistantError(msg) from err

    async def async_set_flow_override(self, percentage: int) -> None:
        """Set the flow override percentage (0-100% or 255 to clear)."""
        try:
            success = await self.api.async_set_node_override(1, percentage)
            if not success:
                msg = f"Failed to set flow override to {percentage}%"
                raise HomeAssistantError(msg)

            await self.async_request_refresh()
        except ClientError as err:
            msg = f"Failed to set flow override to {percentage}%: {err}"
            raise HomeAssistantError(msg) from err
