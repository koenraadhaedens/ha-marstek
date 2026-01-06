"""The Marstek Battery System integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .marstek_api import MarstekAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
]

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Marstek Battery System from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Use longer timeout and enable retries for more reliable communication
    api = MarstekAPI(
        host=entry.data["host"],
        port=entry.data.get("port", 30000),
        timeout=10.0,  # Increased to 10 seconds to match error logs
        retries=3,     # Add retry support
    )

    coordinator = MarstekDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class MarstekDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Marstek data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MarstekAPI,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry
        self.device_info = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        data = {}
        api_errors = []
        
        # Get device info (only once)
        if self.device_info is None:
            try:
                self.device_info = await self.hass.async_add_executor_job(
                    self.api.get_device_info
                )
            except Exception as err:
                api_errors.append(f"Device info: {err}")
        
        # Get all status information - continue even if some calls fail
        async def safe_api_call(api_method, data_key):
            try:
                result = await self.hass.async_add_executor_job(api_method)
                if result:
                    data[data_key] = result
            except Exception as err:
                api_errors.append(f"{data_key}: {err}")
                _LOGGER.debug("API call failed for %s: %s", data_key, err)

        # Execute all API calls
        await safe_api_call(self.api.get_wifi_status, "wifi")
        await safe_api_call(self.api.get_ble_status, "ble")
        await safe_api_call(self.api.get_battery_status, "battery")
        await safe_api_call(self.api.get_pv_status, "pv")
        await safe_api_call(self.api.get_es_status, "es")
        await safe_api_call(self.api.get_es_mode, "es_mode")
        await safe_api_call(self.api.get_em_status, "em")

        data["device_info"] = self.device_info
        
        # Only raise UpdateFailed if we got no data at all
        if not data or (len(data) == 1 and "device_info" in data):
            raise UpdateFailed(f"All API calls failed. Errors: {'; '.join(api_errors)}")
        
        # Log warnings if some calls failed but we got partial data
        if api_errors:
            _LOGGER.warning("Some API calls failed: %s", '; '.join(api_errors))
        
        return data
