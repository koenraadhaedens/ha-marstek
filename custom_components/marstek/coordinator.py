"""Data update coordinator for Marstek integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .marstek_api import MarstekUDPClient, MarstekAPIError

_LOGGER = logging.getLogger(__name__)


class MarstekDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Marstek device."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        update_interval: int,
    ) -> None:
        """Initialize."""
        self.api = MarstekUDPClient(hass, host=host, port=port, remote_port=port)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            return await self.api.get_all_data()
        except MarstekAPIError as exception:
            raise UpdateFailed(f"Error communicating with Marstek device: {exception}") from exception
        except Exception as exception:
            raise UpdateFailed(f"Unexpected error: {exception}") from exception

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect the API client."""
        await self.api.disconnect()
