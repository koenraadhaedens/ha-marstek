"""Marstek API implementation using UDP JSON-RPC protocol with async support and proper retry logic."""
import asyncio
import json
import logging
import random
import time
from typing import Any, Callable
from copy import deepcopy

_LOGGER = logging.getLogger(__name__)

# Configuration constants
DEFAULT_PORT = 30000
DEFAULT_TIMEOUT = 15.0
DISCOVERY_TIMEOUT = 9
DISCOVERY_BROADCAST_INTERVAL = 2
COMMAND_TIMEOUT = 15
COMMAND_MAX_ATTEMPTS = 3
COMMAND_BACKOFF_BASE = 1.5
COMMAND_BACKOFF_FACTOR = 2.0
COMMAND_BACKOFF_MAX = 12.0
COMMAND_BACKOFF_JITTER = 0.4
UNAVAILABLE_THRESHOLD = 120
ERROR_METHOD_NOT_FOUND = -32601

# API Methods
METHOD_GET_DEVICE = "Marstek.GetDevice"
METHOD_WIFI_STATUS = "Wifi.GetStatus"
METHOD_BLE_STATUS = "BLE.GetStatus"
METHOD_BATTERY_STATUS = "Bat.GetStatus"
METHOD_PV_STATUS = "PV.GetStatus"
METHOD_ES_STATUS = "ES.GetStatus"
METHOD_ES_MODE = "ES.GetMode"
METHOD_ES_SET_MODE = "ES.SetMode"
METHOD_EM_STATUS = "EM.GetStatus"


class MarstekAPIError(Exception):
    """Exception raised for API errors."""
    pass


class MarstekProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for Marstek communication."""
    
    def __init__(self):
        self.transport = None
        self.clients = []
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data: bytes, addr: tuple):
        """Handle incoming UDP datagram."""
        try:
            message = json.loads(data.decode('utf-8'))
            # Dispatch to all registered clients
            for client in self.clients:
                asyncio.create_task(client._handle_message(data, addr))
        except Exception as err:
            _LOGGER.debug("Failed to parse UDP message from %s: %s", addr, err)
    
    def error_received(self, exc):
        _LOGGER.error("UDP protocol error: %s", exc)


# Shared resources for connection pooling
_shared_transports = {}
_shared_protocols = {}
_transport_refcounts = {}
_clients_by_port = {}


class MarstekAPI:
    """Advanced async API client for Marstek devices using UDP JSON-RPC."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self.remote_port = port  # Send to same port
        self.timeout = timeout
        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: MarstekProtocol | None = None
        self._handlers: list = []
        self._connected = False
        self._msg_id_counter = 0
        self._command_stats: dict[str, dict[str, Any]] = {}
        self._stale_message_counter = 0
        self._loop = None

    async def connect(self) -> None:
        """Connect to the UDP socket using shared transport."""
        if self._connected and self.transport:
            _LOGGER.debug("Already connected on port %s", self.port)
            return

        loop = asyncio.get_event_loop()
        self._loop = loop

        _LOGGER.info(
            "Connecting UDP socket: local_port=%s, remote_host=%s, remote_port=%s",
            self.port, self.host or "broadcast", self.remote_port
        )

        try:
            # Use shared transport/protocol for this port
            if self.port not in _shared_transports:
                # Create shared UDP endpoint for this port
                import sys
                endpoint_kwargs = {
                    "local_addr": ("0.0.0.0", self.port),
                    "allow_broadcast": True,
                }
                # reuse_port is not supported on Windows
                if sys.platform != "win32":
                    endpoint_kwargs["reuse_port"] = True
                    
                transport, protocol = await loop.create_datagram_endpoint(
                    lambda: MarstekProtocol(),
                    **endpoint_kwargs,
                )
                _shared_transports[self.port] = transport
                _shared_protocols[self.port] = protocol
                _transport_refcounts[self.port] = 0

                _LOGGER.info("Created shared UDP socket on port %s", self.port)

            # Use the shared transport/protocol
            self.transport = _shared_transports[self.port]
            self.protocol = _shared_protocols[self.port]
            _transport_refcounts[self.port] += 1

            # Register this client for message dispatching
            if self.port not in _clients_by_port:
                _clients_by_port[self.port] = []
            if self not in _clients_by_port[self.port]:
                _clients_by_port[self.port].append(self)
            
            # Add this client to the protocol's client list
            if self not in self.protocol.clients:
                self.protocol.clients.append(self)

            self._connected = True
            sock = self.transport.get_extra_info('socket')
            _LOGGER.info(
                "UDP socket connected: local_port=%s, socket=%s, refcount=%d, clients=%d",
                self.port, sock.getsockname() if sock else "unknown",
                _transport_refcounts[self.port], len(_clients_by_port[self.port])
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to connect UDP socket on port %s: %s",
                self.port, err, exc_info=True
            )
            raise

    async def disconnect(self) -> None:
        """Disconnect from the UDP socket."""
        if not self._connected:
            return

        try:
            # Remove this client from protocol's client list
            if self.protocol and self in self.protocol.clients:
                self.protocol.clients.remove(self)
                
            # Remove from port client list
            if self.port in _clients_by_port and self in _clients_by_port[self.port]:
                _clients_by_port[self.port].remove(self)

            # Decrease reference count and potentially close shared transport
            if self.port in _transport_refcounts:
                _transport_refcounts[self.port] -= 1
                if _transport_refcounts[self.port] <= 0:
                    # Last client, close the shared transport
                    if self.port in _shared_transports:
                        _shared_transports[self.port].close()
                        del _shared_transports[self.port]
                        del _shared_protocols[self.port]
                        del _transport_refcounts[self.port]
                        if self.port in _clients_by_port:
                            del _clients_by_port[self.port]
                        _LOGGER.info("Closed shared UDP socket on port %s", self.port)

            self.transport = None
            self.protocol = None
            self._connected = False
            _LOGGER.debug("UDP socket disconnected on port %s", self.port)
        except Exception as err:
            _LOGGER.error("Error during disconnect: %s", err)
    
    def register_handler(self, handler: Callable) -> None:
        """Register a message handler."""
        if handler not in self._handlers:
            self._handlers.append(handler)
    
    def unregister_handler(self, handler: Callable) -> None:
        """Unregister a message handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    async def _handle_message(self, data: bytes, addr: tuple) -> None:
        """Handle incoming UDP message."""
        try:
            message = json.loads(data.decode('utf-8'))
            # Call all registered handlers
            for handler in self._handlers:
                try:
                    handler(message, addr)
                except Exception as err:
                    _LOGGER.debug("Handler error: %s", err)
        except Exception as err:
            _LOGGER.debug("Failed to parse message from %s: %s", addr, err)

    async def send_command(
        self,
        method: str,
        params: dict | None = None,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Send a command and wait for response with retry logic."""
        if not self._connected:
            await self.connect()

        if params is None:
            params = {"id": 0}

        effective_timeout = timeout if timeout is not None else COMMAND_TIMEOUT
        attempt_limit = max_attempts if max_attempts is not None else COMMAND_MAX_ATTEMPTS

        # Generate unique integer message ID
        self._msg_id_counter = (self._msg_id_counter + 1) % 1000000
        msg_id = self._msg_id_counter
        payload = {
            "id": msg_id,
            "method": method,
            "params": params,
        }
        payload_str = json.dumps(payload)

        _LOGGER.debug(
            "Sending command: method=%s, id=%s, host=%s, port=%s, transport=%s",
            method, msg_id, self.host, self.remote_port, self.transport is not None
        )

        # Shared response tracking for all attempts
        response_event = asyncio.Event()
        response_data: dict[str, Any] = {}
        last_exception: Exception | None = None

        # Allow the event loop to process any pending datagrams before we start
        await asyncio.sleep(0)

        def handler(message, addr):
            """Handle command response."""
            if message.get("id") == msg_id:
                if self.host and addr[0] != self.host:
                    _LOGGER.debug("Ignoring response from wrong host: %s (expected %s)", addr[0], self.host)
                    return  # Wrong device
                _LOGGER.debug("Matched response for %s from %s", method, addr)
                response_data.clear()
                response_data.update(message)
                response_event.set()
            else:
                # Track stray messages so we know if queues are backing up
                self._stale_message_counter += 1
                if self._stale_message_counter <= 5 or self._stale_message_counter % 25 == 0:
                    _LOGGER.debug(
                        "Ignoring stale message while waiting for %s: got id=%s from %s (total stales=%d)",
                        method,
                        message.get("id"),
                        addr[0],
                        self._stale_message_counter,
                    )

        # Register temporary handler
        self.register_handler(handler)

        try:
            loop = asyncio.get_running_loop()

            for attempt in range(1, attempt_limit + 1):
                response_event.clear()
                response_data.clear()
                attempt_started = loop.time()

                try:
                    _LOGGER.debug(
                        "Sending payload (attempt %d/%d) to %s:%s: %s",
                        attempt,
                        attempt_limit,
                        self.host or "broadcast",
                        self.remote_port,
                        payload_str,
                    )
                    # Yield once more to ensure pending packets are processed before sending
                    await asyncio.sleep(0)
                    await self._send_to_host(payload_str)

                    await asyncio.wait_for(response_event.wait(), timeout=effective_timeout)

                    # Check for API errors in response
                    if "error" in response_data:
                        error = response_data["error"]
                        error_code = error.get('code')
                        error_msg = error.get('message')
                        # Record the error with its code for diagnostics
                        self._record_command_result(
                            method,
                            success=False,
                            attempt=attempt,
                            latency=None,
                            timeout=False,
                            error=error_msg,
                            error_code=error_code,
                        )
                        raise MarstekAPIError(
                            f"API error {error_code}: {error_msg}"
                        )

                    latency = loop.time() - attempt_started
                    self._stale_message_counter = 0
                    self._record_command_result(
                        method,
                        success=True,
                        attempt=attempt,
                        latency=latency,
                        timeout=False,
                        error=None,
                        error_code=None,
                        response=response_data,
                    )
                    _LOGGER.debug(
                        "Command %s completed successfully in %.2fs (attempt %d)",
                        method,
                        latency,
                        attempt,
                    )
                    return response_data.get("result")

                except asyncio.TimeoutError:
                    self._record_command_result(
                        method,
                        success=False,
                        attempt=attempt,
                        latency=None,
                        timeout=True,
                        error="timeout",
                    )
                    _LOGGER.warning(
                        "Command %s timed out after %ss (attempt %d/%d, host=%s)",
                        method,
                        effective_timeout,
                        attempt,
                        attempt_limit,
                        self.host,
                    )
                    last_exception = None
                except MarstekAPIError:
                    # Error already recorded in the if "error" block above
                    raise
                except Exception as err:
                    self._record_command_result(
                        method,
                        success=False,
                        attempt=attempt,
                        latency=None,
                        timeout=False,
                        error=str(err),
                    )
                    _LOGGER.error(
                        "Error sending command %s to %s on attempt %d/%d: %s",
                        method,
                        self.host,
                        attempt,
                        attempt_limit,
                        err,
                        exc_info=True,
                    )
                    last_exception = err

                # Wait before retrying
                if attempt < attempt_limit:
                    delay = self._compute_backoff_delay(attempt)
                    _LOGGER.debug(
                        "Waiting %.2fs before retrying %s (attempt %d/%d)",
                        delay,
                        method,
                        attempt + 1,
                        attempt_limit,
                    )
                    await asyncio.sleep(delay)

        finally:
            self.unregister_handler(handler)

        if last_exception:
            raise last_exception

        _LOGGER.error(
            "Command %s failed after %d attempt(s); returning no result",
            method,
            attempt_limit,
        )
        return None

    async def _send_to_host(self, message: str) -> None:
        """Send message to specific host or broadcast."""
        if not self.transport:
            raise MarstekAPIError("Not connected")

        if self.host:
            # Send to specific host on remote port
            self.transport.sendto(
                message.encode(),
                (self.host, self.remote_port)
            )
        else:
            # Broadcast
            await self.broadcast(message)

    def _compute_backoff_delay(self, attempt: int) -> float:
        """Compute exponential backoff with jitter for retries."""
        base_delay = COMMAND_BACKOFF_BASE * (COMMAND_BACKOFF_FACTOR ** (attempt - 1))
        capped = min(base_delay, COMMAND_BACKOFF_MAX)
        if COMMAND_BACKOFF_JITTER > 0:
            return capped + random.uniform(0, COMMAND_BACKOFF_JITTER)
        return capped

    def _record_command_result(
        self,
        method: str,
        *,
        success: bool,
        attempt: int,
        latency: float | None,
        timeout: bool,
        error: str | None,
        error_code: int | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Track command attempt statistics for diagnostics."""
        stats = self._command_stats.setdefault(
            method,
            {
                "total_attempts": 0,
                "total_success": 0,
                "total_timeouts": 0,
                "total_failures": 0,
                "last_success": None,
                "last_attempt": None,
                "last_latency": None,
                "last_timeout": False,
                "last_error": None,
                "last_error_code": None,
                "last_updated": None,
                "last_success_at": None,
                "last_success_payload": None,
                "unsupported_error_count": 0,
                "supported": None,  # None=unknown, True=supported, False=unsupported
            },
        )

        stats["total_attempts"] += 1
        if success:
            stats["total_success"] += 1
            stats["supported"] = True  # Command works on this device
        elif timeout:
            stats["total_timeouts"] += 1
        else:
            stats["total_failures"] += 1

        stats["last_success"] = success
        stats["last_attempt"] = attempt
        stats["last_latency"] = latency
        stats["last_timeout"] = timeout
        stats["last_error"] = error
        stats["last_error_code"] = error_code
        stats["last_updated"] = time.time()
        if success:
            stats["last_success_at"] = stats["last_updated"]
            stats["last_success_payload"] = deepcopy(response) if response is not None else None

        # Track "Method not found" errors to detect unsupported commands
        if error_code == ERROR_METHOD_NOT_FOUND:
            stats["unsupported_error_count"] += 1
            if stats["unsupported_error_count"] >= 2:
                stats["supported"] = False  # Likely unsupported

    async def broadcast(self, message: str) -> None:
        """Broadcast a message."""
        if not self.transport:
            raise MarstekAPIError("Not connected")
        
        # Get broadcast addresses
        broadcast_addrs = self._get_broadcast_addresses()
        for broadcast_addr in broadcast_addrs:
            self.transport.sendto(
                message.encode(),
                (broadcast_addr, self.remote_port)
            )

    def _get_broadcast_addresses(self) -> list[str]:
        """Get all broadcast addresses for available networks."""
        # Simple implementation - can be enhanced based on the working repository
        return ["255.255.255.255"]

    async def discover_devices(self, timeout: int = DISCOVERY_TIMEOUT) -> list[dict]:
        """Discover Marstek devices on the network."""
        devices = []
        discovered_macs = set()

        def handler(message, addr):
            """Handle discovery responses."""
            if message.get("id") == 0 and "result" in message:
                result = message["result"]
                mac = result.get("wifi_mac") or result.get("ble_mac")
                if mac and mac not in discovered_macs:
                    discovered_macs.add(mac)
                    device_info = dict(result)
                    device_info["ip"] = addr[0]
                    devices.append(device_info)
                    _LOGGER.debug("Discovered device: %s at %s", device_info.get("device", "Unknown"), addr[0])

        # Register handler
        self.register_handler(handler)

        try:
            # Get all broadcast addresses
            broadcast_addrs = self._get_broadcast_addresses()
            _LOGGER.debug("Broadcasting to networks: %s", broadcast_addrs)

            # Broadcast discovery message repeatedly on all networks
            end_time = asyncio.get_event_loop().time() + timeout
            message = json.dumps({
                "id": 0,
                "method": METHOD_GET_DEVICE,
                "params": {"ble_mac": "0"}
            })

            while asyncio.get_event_loop().time() < end_time:
                # Broadcast to all networks
                for broadcast_addr in broadcast_addrs:
                    if self.transport:
                        self.transport.sendto(
                            message.encode(),
                            (broadcast_addr, self.remote_port)
                        )
                await asyncio.sleep(DISCOVERY_BROADCAST_INTERVAL)

            # Wait a bit longer for any delayed responses
            _LOGGER.debug("Waiting for delayed responses...")
            await asyncio.sleep(2)

        finally:
            self.unregister_handler(handler)
            _LOGGER.info("Discovery complete - found %d device(s)", len(devices))

        return devices

    # API method helpers
    async def get_device_info(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get device information."""
        return await self.send_command(
            METHOD_GET_DEVICE,
            {"ble_mac": "0"},
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_wifi_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get WiFi status."""
        return await self.send_command(
            METHOD_WIFI_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_ble_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get Bluetooth status."""
        return await self.send_command(
            METHOD_BLE_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_battery_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get battery status."""
        return await self.send_command(
            METHOD_BATTERY_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_pv_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get PV (solar) status."""
        return await self.send_command(
            METHOD_PV_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_es_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get energy system status."""
        return await self.send_command(
            METHOD_ES_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_es_mode(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get energy system mode."""
        return await self.send_command(
            METHOD_ES_MODE,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def get_em_status(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = None,
    ) -> dict | None:
        """Get energy meter status."""
        return await self.send_command(
            METHOD_EM_STATUS,
            timeout=timeout,
            max_attempts=max_attempts,
        )

    async def set_es_mode_auto(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = 5,
    ) -> bool:
        """Set energy system to Auto mode."""
        params = {
            "id": 0,
            "config": {
                "mode": "Auto",
                "auto_cfg": {"enable": 1},
            },
        }
        result = await self.send_command(
            METHOD_ES_SET_MODE, 
            params,
            timeout=timeout,
            max_attempts=max_attempts
        )
        return result is not None and result.get("set_result", False)

    async def set_es_mode_ai(
        self,
        *,
        timeout: int | None = None,
        max_attempts: int | None = 5,
    ) -> bool:
        """Set energy system to AI mode."""
        params = {
            "id": 0,
            "config": {
                "mode": "AI",
                "ai_cfg": {"enable": 1},
            },
        }
        result = await self.send_command(
            METHOD_ES_SET_MODE, 
            params,
            timeout=timeout,
            max_attempts=max_attempts
        )
        return result is not None and result.get("set_result", False)

    async def set_es_mode_manual(
        self,
        time_num: int,
        start_time: str,
        end_time: str,
        week_set: int,
        power: int,
        enable: int = 1,
        *,
        timeout: int | None = None,
        max_attempts: int | None = 5,
    ) -> bool:
        """Set energy system to Manual mode."""
        params = {
            "id": 0,
            "config": {
                "mode": "Manual",
                "manual_cfg": {
                    "time_num": time_num,
                    "start_time": start_time,
                    "end_time": end_time,
                    "week_set": week_set,
                    "power": power,
                    "enable": enable,
                },
            },
        }
        result = await self.send_command(
            METHOD_ES_SET_MODE, 
            params,
            timeout=timeout,
            max_attempts=max_attempts
        )
        return result is not None and result.get("set_result", False)

    async def set_es_mode_passive(
        self, 
        power: int, 
        cd_time: int = 300,
        *,
        timeout: int | None = None,
        max_attempts: int | None = 5,
    ) -> bool:
        """Set energy system to Passive mode."""
        params = {
            "id": 0,
            "config": {
                "mode": "Passive",
                "passive_cfg": {
                    "power": power,
                    "cd_time": cd_time,
                },
            },
        }
        result = await self.send_command(
            METHOD_ES_SET_MODE, 
            params,
            timeout=timeout,
            max_attempts=max_attempts
        )
        return result is not None and result.get("set_result", False)

    def get_command_stats(self, method: str) -> dict[str, Any] | None:
        """Return snapshot of command statistics."""
        return self._command_stats.get(method)

    def get_all_command_stats(self) -> dict[str, dict[str, Any]]:
        """Return snapshot of all command statistics."""
        return dict(self._command_stats)

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._connected
