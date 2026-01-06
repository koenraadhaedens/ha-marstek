"""Config flow for Marstek integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_PORT, CONF_UPDATE_INTERVAL, DEFAULT_UDP_PORT, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .marstek_api import MarstekAPI, MarstekAPIError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_UDP_PORT): int,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = MarstekAPI(data[CONF_HOST], data.get(CONF_PORT, DEFAULT_UDP_PORT))
    
    try:
        device_info = await api.get_device_info()
        device_model = device_info.get("device", "Unknown")
        return {
            "title": f"Marstek {device_model} ({data[CONF_HOST]})", 
            "device_info": device_info
        }
    except MarstekAPIError as exc:
        _LOGGER.exception("Failed to connect to Marstek device: %s", exc)
        raise CannotConnect from exc
    except Exception as exc:
        _LOGGER.exception("Unexpected error connecting to Marstek device: %s", exc)
        raise CannotConnect from exc


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Marstek."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
