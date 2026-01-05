"""The Marstek Battery System integration."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

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

    api = MarstekAPI(
        host=entry.data["host"],
        port=entry.data.get("port", 30000),
    )

    coordinator = MarstekDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator and coordinator.api:
        try:
            await coordinator.api.disconnect()
        except Exception as err:
            _LOGGER.debug("Error during API cleanup: %s", err)
    
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
        self._first_update = True
        self.update_count = 0
        self.category_last_updated = {}
        self._cached_data = {}  # Cache previous successful data

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library with tiered polling strategy."""
        try:
            # Ensure API is connected
            if not self.api.is_connected:
                await self.api.connect()
                
            data = {}
            had_success = False
            is_first_update = self._first_update
            
            # Start with cached data to preserve previous values
            data.update(self._cached_data)
            
            def _command_kwargs() -> dict[str, Any]:
                """Use shorter timeouts/attempts during the very first refresh."""
                if is_first_update and not had_success:
                    return {"timeout": min(8, 15), "max_attempts": 2}
                return {"timeout": 10, "max_attempts": 3}

            def _command_delay() -> float:
                """Back off a little between calls; go faster while probing initial contact."""
                return 0.2 if is_first_update and not had_success else 1.0
            
            # Get device info (only on first update and every 10th update)
            if self.device_info is None or self.update_count % 10 == 0:
                try:
                    if self.update_count > 0:
                        await asyncio.sleep(_command_delay())
                    device_info = await self.api.get_device_info(**_command_kwargs())
                    if device_info:
                        self.device_info = device_info
                        data["device_info"] = device_info
                        self.category_last_updated["device"] = time.time()
                        had_success = True
                        _LOGGER.debug("Updated device info")
                except Exception as err:
                    if is_first_update:
                        _LOGGER.warning("Failed to get device info on first update: %s", err)
                    else:
                        _LOGGER.debug("Failed to get device info: %s", err)
            elif self.device_info:
                data["device_info"] = self.device_info
                
            # High priority - every update (~30s)
            try:
                await asyncio.sleep(_command_delay())
                bat_status = await self.api.get_battery_status(**_command_kwargs())
                if bat_status:
                    data["battery"] = bat_status
                    self._cached_data["battery"] = bat_status  # Cache successful data
                    self.category_last_updated["battery"] = time.time()
                    had_success = True
            except Exception as err:
                _LOGGER.debug("Failed to get battery status: %s", err)

            try:
                await asyncio.sleep(_command_delay())
                es_status = await self.api.get_es_status(**_command_kwargs())
                if es_status:
                    data["es"] = es_status
                    self._cached_data["es"] = es_status
                    self.category_last_updated["es"] = time.time()
                    had_success = True
            except Exception as err:
                _LOGGER.debug("Failed to get ES status: %s", err)

            # Medium priority - every 5th update (150s)
            if self.update_count % 5 == 0:
                try:
                    await asyncio.sleep(_command_delay())
                    pv_status = await self.api.get_pv_status(**_command_kwargs())
                    if pv_status:
                        data["pv"] = pv_status
                        self._cached_data["pv"] = pv_status
                        self.category_last_updated["pv"] = time.time()
                        had_success = True
                except Exception as err:
                    _LOGGER.debug("Failed to get PV status: %s", err)

                try:
                    await asyncio.sleep(_command_delay())
                    es_mode = await self.api.get_es_mode(**_command_kwargs())
                    if es_mode:
                        data["es_mode"] = es_mode
                        self._cached_data["es_mode"] = es_mode
                        self.category_last_updated["es_mode"] = time.time()
                        had_success = True
                except Exception as err:
                    _LOGGER.debug("Failed to get ES mode: %s", err)

                try:
                    await asyncio.sleep(_command_delay())
                    em_status = await self.api.get_em_status(**_command_kwargs())
                    if em_status:
                        data["em"] = em_status
                        self._cached_data["em"] = em_status
                        self.category_last_updated["em"] = time.time()
                        had_success = True
                except Exception as err:
                    _LOGGER.debug("Failed to get EM status: %s", err)

            # Low priority - every 10th update (300s)
            if self.update_count % 10 == 0:
                try:
                    await asyncio.sleep(_command_delay())
                    wifi_status = await self.api.get_wifi_status(**_command_kwargs())
                    if wifi_status:
                        data["wifi"] = wifi_status
                        self._cached_data["wifi"] = wifi_status
                        self.category_last_updated["wifi"] = time.time()
                        had_success = True
                except Exception as err:
                    _LOGGER.debug("Failed to get wifi status: %s", err)

                try:
                    await asyncio.sleep(_command_delay())
                    ble_status = await self.api.get_ble_status(**_command_kwargs())
                    if ble_status:
                        data["ble"] = ble_status
                        self._cached_data["ble"] = ble_status
                        self.category_last_updated["ble"] = time.time()
                        had_success = True
                except Exception as err:
                    _LOGGER.debug("Failed to get BLE status: %s", err)
            
            self.update_count += 1
            self._first_update = False
            
            if not had_success and is_first_update:
                raise UpdateFailed("Could not retrieve any data from device on first update")
            
            return data

        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
