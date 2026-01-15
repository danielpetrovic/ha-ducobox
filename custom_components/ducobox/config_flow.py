"""Config flow for the DucoBox integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import detect_api_type
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)

    try:
        # Detect which API type the device supports
        api_class = await detect_api_type(data[CONF_HOST], session)
        api = api_class(data[CONF_HOST], session)
        device_info = await api.async_get_device_info()
    except ClientError as err:
        raise CannotConnectError from err

    return {"title": device_info.model, "unique_id": device_info.serial_number}


class DucoBoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DucoBox."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery info: %s", discovery_info)

        # Get the IP address from discovery
        host = discovery_info.host

        # Get MAC address from properties if available
        mac = discovery_info.properties.get("MAC", "").upper()

        # Try to get device info to create unique ID
        session = async_get_clientsession(self.hass)
        try:
            api_class = await detect_api_type(host, session)
            api = api_class(host, session)
            device_info = await api.async_get_device_info()

            unique_id = device_info.serial_number
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

            self._discovered_host = host
            self._discovered_name = device_info.model

        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Failed to connect to discovered device: %s", err)
            return self.async_abort(reason="cannot_connect")

        # Show confirmation form
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name or "DucoBox",
                data={CONF_HOST: self._discovered_host},
            )

        self._set_confirm_only()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._discovered_name or "DucoBox",
                "host": self._discovered_host or "",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])

                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""
