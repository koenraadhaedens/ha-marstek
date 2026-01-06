"""API client for Marstek device using UDP JSON-RPC protocol."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any

_LOGGER = logging.getLogger(__name__)


class MarstekAPI:
    """API client for Marstek device using UDP JSON-RPC."""

    def __init__(self, host: str, port: int = 30000) -> None:
        """Initialize the API client."""
        self.host = host
        self.port = port
        self.command_id = 1
        self.timeout = 5.0

    async def _send_command(self, method: str, params: Any = None) -> dict[str, Any]:
        """Send a JSON-RPC command via UDP and get response."""
        command = {
            "id": self.command_id,
            "method": method,
            "params": params or {}
        }
        
        self.command_id += 1
        
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            
            # Send command
            message = json.dumps(command).encode('utf-8')
            sock.sendto(message, (self.host, self.port))
            
            # Receive response
            data, addr = sock.recvfrom(4096)
            sock.close()
            
            response = json.loads(data.decode('utf-8'))
            
            if "error" in response:
                error = response["error"]
                raise MarstekAPIError(f"API Error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
            
        except socket.timeout:
            raise MarstekAPIError(f"Timeout communicating with device at {self.host}:{self.port}")
        except json.JSONDecodeError as exc:
            raise MarstekAPIError(f"Invalid JSON response: {exc}")
        except Exception as exc:
            _LOGGER.error("Error communicating with Marstek device: %s", exc)
            raise MarstekAPIError(f"Communication error: {exc}")

    async def discover_device(self, ble_mac: str = None) -> dict[str, Any]:
        """Discover Marstek device using broadcast."""
        params = {}
        if ble_mac:
            params["ble_mac"] = ble_mac
        
        return await self._send_command("Marstek.GetDevice", params)

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information."""
        return await self.discover_device()

    async def get_wifi_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get WiFi status."""
        return await self._send_command("Wifi.GetStatus", {"id": instance_id})

    async def get_ble_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get Bluetooth status."""
        return await self._send_command("BLE.GetStatus", {"id": instance_id})

    async def get_battery_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get battery status."""
        return await self._send_command("Bat.GetStatus", {"id": instance_id})

    async def get_pv_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get photovoltaic status."""
        return await self._send_command("PV.GetStatus", {"id": instance_id})

    async def get_energy_system_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get energy system status."""
        return await self._send_command("ES.GetStatus", {"id": instance_id})

    async def get_energy_system_mode(self, instance_id: int = 0) -> dict[str, Any]:
        """Get energy system mode."""
        return await self._send_command("ES.GetMode", {"id": instance_id})

    async def set_energy_system_mode(self, instance_id: int, mode_config: dict[str, Any]) -> dict[str, Any]:
        """Set energy system mode."""
        params = {
            "id": instance_id,
            "config": mode_config
        }
        return await self._send_command("ES.SetMode", params)

    async def get_energy_meter_status(self, instance_id: int = 0) -> dict[str, Any]:
        """Get energy meter status."""
        return await self._send_command("EM.GetStatus", {"id": instance_id})

    async def get_all_data(self) -> dict[str, Any]:
        """Get all available data from the device."""
        try:
            data = {}
            
            # Get device info
            data["device_info"] = await self.get_device_info()
            
            # Get all component statuses
            data["wifi"] = await self.get_wifi_status()
            data["ble"] = await self.get_ble_status()
            data["battery"] = await self.get_battery_status()
            data["energy_system"] = await self.get_energy_system_status()
            data["energy_system_mode"] = await self.get_energy_system_mode()
            data["energy_meter"] = await self.get_energy_meter_status()
            
            # Try to get PV status (Venus D only)
            try:
                data["pv"] = await self.get_pv_status()
            except MarstekAPIError:
                # PV not supported on this model
                data["pv"] = None
            
            return data
            
        except Exception as exc:
            _LOGGER.error("Error fetching all data from Marstek device: %s", exc)
            raise


class MarstekAPIError(Exception):
    """Exception for Marstek API errors."""
    pass
