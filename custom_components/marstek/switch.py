"""Switch platform for Marstek integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekDataUpdateCoordinator
from .marstek_api import MarstekAPIError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Marstek switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    switches = [
        MarstekModeSwitch(coordinator, "auto", "Auto Mode"),
        MarstekModeSwitch(coordinator, "ai", "AI Mode"),
        MarstekModeSwitch(coordinator, "manual", "Manual Mode"),
        MarstekModeSwitch(coordinator, "passive", "Passive Mode"),
        MarstekBatterySwitch(coordinator, "charge", "Battery Charging"),
        MarstekBatterySwitch(coordinator, "discharge", "Battery Discharge"),
    ]
    
    async_add_entities(switches)


class MarstekModeSwitch(CoordinatorEntity[MarstekDataUpdateCoordinator], SwitchEntity):
    """Representation of a Marstek mode switch."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        mode: str,
        name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._mode = mode
        self._attr_name = f"Marstek {name}"
        self._attr_unique_id = f"marstek_mode_{mode}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return False
        
        energy_mode = self.coordinator.data.get("energy_system_mode", {})
        current_mode = energy_mode.get("mode", "").lower()
        return current_mode == self._mode

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("energy_system_mode") is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            mode_config = {
                "mode": self._mode.capitalize(),
                f"{self._mode}_cfg": {"enable": 1}
            }
            
            await self.coordinator.api.set_energy_system_mode(0, mode_config)
            await self.coordinator.async_request_refresh()
            
        except MarstekAPIError as exc:
            _LOGGER.error("Failed to set %s mode: %s", self._mode, exc)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # Cannot turn off a mode directly, would need to switch to another mode
        # For now, we'll just log this
        _LOGGER.warning("Cannot turn off %s mode directly. Switch to another mode instead.", self._mode)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_info = self.coordinator.data.get("device_info", {}) if self.coordinator.data else {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.host)},
            "name": f"Marstek {device_info.get('device', 'Device')}",
            "manufacturer": "Marstek",
            "model": device_info.get("device", "Unknown"),
            "sw_version": str(device_info.get("ver", "Unknown")),
            "hw_version": device_info.get("ble_mac", "Unknown"),
        }


class MarstekBatterySwitch(CoordinatorEntity[MarstekDataUpdateCoordinator], SwitchEntity):
    """Representation of a Marstek battery control switch."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        switch_type: str,
        name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._switch_type = switch_type
        self._attr_name = f"Marstek {name}"
        self._attr_unique_id = f"marstek_battery_{switch_type}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return False
        
        battery_data = self.coordinator.data.get("battery", {})
        if self._switch_type == "charge":
            return battery_data.get("charg_flag", False)
        elif self._switch_type == "discharge":
            return battery_data.get("dischrg_flag", False)
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("battery") is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # Note: The API documentation doesn't show how to control battery charge/discharge flags
        # This would need to be implemented based on additional API endpoints
        _LOGGER.warning("Battery control not implemented - API endpoint needed")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # Note: The API documentation doesn't show how to control battery charge/discharge flags
        # This would need to be implemented based on additional API endpoints
        _LOGGER.warning("Battery control not implemented - API endpoint needed")

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_info = self.coordinator.data.get("device_info", {}) if self.coordinator.data else {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.host)},
            "name": f"Marstek {device_info.get('device', 'Device')}",
            "manufacturer": "Marstek",
            "model": device_info.get("device", "Unknown"),
            "sw_version": str(device_info.get("ver", "Unknown")),
            "hw_version": device_info.get("ble_mac", "Unknown"),
        }