"""Standalone test script to verify Marstek device connectivity."""
import asyncio
import json
import logging
import random
import socket
import time

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Constants
DEFAULT_UDP_PORT = 30000
COMMAND_TIMEOUT = 5
COMMAND_MAX_ATTEMPTS = 3
COMMAND_BACKOFF_BASE = 0.5
COMMAND_BACKOFF_FACTOR = 2.0
COMMAND_BACKOFF_MAX = 8.0
COMMAND_BACKOFF_JITTER = 0.1
METHOD_GET_DEVICE = "Marstek.GetDevice"
METHOD_BATTERY_STATUS = "Bat.GetStatus"

# Shared transports and protocols per port
_shared_transports = {}
_shared_protocols = {}
_transport_refcounts = {}
_clients_by_port = {}


class MarstekAPIError(Exception):
    """Exception for Marstek API errors."""
    pass


class MarstekProtocol(asyncio.DatagramProtocol):
    """Protocol for handling UDP datagrams."""

    def __init__(self) -> None:
        """Initialize the protocol."""
        self.port = None

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        """Handle received datagram."""
        if self.port is None:
            for port, protocol in _shared_protocols.items():
                if protocol is self:
                    self.port = port
                    break

        if self.port and self.port in _clients_by_port:
            for client in _clients_by_port[self.port]:
                asyncio.create_task(client._handle_message(data, addr))
        else:
            _LOGGER.warning("Received message but no clients registered for port %s", self.port)

    def error_received(self, exc: Exception) -> None:
        """Handle protocol errors."""
        _LOGGER.error("UDP protocol error: %s", exc)


class MarstekUDPClient:
    """UDP client for Marstek Local API communication."""

    def __init__(self, host: str | None = None, port: int = DEFAULT_UDP_PORT, remote_port: int | None = None) -> None:
        """Initialize the UDP client."""
        self.host = host
        self.port = port
        self.remote_port = remote_port or DEFAULT_UDP_PORT
        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: MarstekProtocol | None = None
        self._handlers: list = []
        self._connected = False
        self._msg_id_counter = 0

    async def connect(self) -> None:
        """Connect to the UDP socket."""
        if self._connected and self.transport:
            _LOGGER.debug("Already connected on port %s", self.port)
            return

        loop = asyncio.get_event_loop()

        _LOGGER.info(
            "Connecting UDP socket: local_port=%s, remote_host=%s, remote_port=%s",
            self.port, self.host or "broadcast", self.remote_port
        )

        try:
            if self.port not in _shared_transports:
                import sys
                endpoint_kwargs = {
                    "local_addr": ("0.0.0.0", self.port),
                    "allow_broadcast": True,
                }
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

            self.transport = _shared_transports[self.port]
            self.protocol = _shared_protocols[self.port]
            _transport_refcounts[self.port] += 1

            if self.port not in _clients_by_port:
                _clients_by_port[self.port] = []
            if self not in _clients_by_port[self.port]:
                _clients_by_port[self.port].append(self)

            self._connected = True
            sock = self.transport.get_extra_info('socket')
            _LOGGER.info(
                "UDP socket connected: local_port=%s, socket=%s, refcount=%d, clients=%d",
                self.port, sock.getsockname() if sock else "unknown",
                _transport_refcounts[self.port], len(_clients_by_port[self.port])
            )
        except Exception as err:
            _LOGGER.error("Failed to connect UDP socket on port %s: %s", self.port, err, exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the UDP socket."""
        if not self._connected:
            return

        if self.port in _transport_refcounts:
            if self.port in _clients_by_port and self in _clients_by_port[self.port]:
                _clients_by_port[self.port].remove(self)

            _transport_refcounts[self.port] -= 1

            if _transport_refcounts[self.port] <= 0:
                if self.transport:
                    try:
                        self.transport.close()
                    except Exception as err:
                        _LOGGER.warning("Error closing transport: %s", err)

                if self.port in _shared_transports:
                    del _shared_transports[self.port]
                if self.port in _shared_protocols:
                    del _shared_protocols[self.port]
                if self.port in _transport_refcounts:
                    del _transport_refcounts[self.port]
                if self.port in _clients_by_port:
                    del _clients_by_port[self.port]
                _LOGGER.debug("Closed shared UDP socket on port %s", self.port)

        self.transport = None
        self.protocol = None
        self._connected = False

    def register_handler(self, handler) -> None:
        """Register a message handler."""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unregister_handler(self, handler) -> None:
        """Unregister a message handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def _handle_message(self, data: bytes, addr: tuple) -> None:
        """Handle incoming UDP message."""
        try:
            message = json.loads(data.decode())
            _LOGGER.debug("Received UDP message from %s:%s: %s", addr[0], addr[1], message)

            for handler in self._handlers:
                try:
                    result = handler(message, addr)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as err:
                    _LOGGER.error("Error in message handler: %s", err, exc_info=True)

        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to decode JSON message from %s: %s", addr, err)

    async def send_command(self, method: str, params: dict | None = None, timeout: int | None = None, max_attempts: int | None = None) -> dict | None:
        """Send a command and wait for response."""
        if not self._connected:
            await self.connect()

        if params is None:
            params = {"id": 0}

        effective_timeout = timeout if timeout is not None else COMMAND_TIMEOUT
        attempt_limit = max_attempts if max_attempts is not None else COMMAND_MAX_ATTEMPTS

        self._msg_id_counter = (self._msg_id_counter + 1) % 1000000
        msg_id = self._msg_id_counter
        payload = {
            "id": msg_id,
            "method": method,
            "params": params,
        }
        payload_str = json.dumps(payload)

        _LOGGER.debug("Sending command: method=%s, id=%s, host=%s, port=%s", method, msg_id, self.host, self.remote_port)

        response_event = asyncio.Event()
        response_data: dict = {}

        def handler(message, addr):
            """Handle command response."""
            if message.get("id") == msg_id:
                if self.host and addr[0] != self.host:
                    _LOGGER.debug("Ignoring response from wrong host: %s (expected %s)", addr[0], self.host)
                    return
                _LOGGER.debug("Matched response for %s from %s", method, addr)
                response_data.clear()
                response_data.update(message)
                response_event.set()

        self.register_handler(handler)

        try:
            for attempt in range(1, attempt_limit + 1):
                response_event.clear()
                response_data.clear()

                try:
                    _LOGGER.debug("Sending payload (attempt %d/%d) to %s:%s: %s", attempt, attempt_limit, self.host or "broadcast", self.remote_port, payload_str)
                    await asyncio.sleep(0)
                    await self._send_to_host(payload_str)

                    await asyncio.wait_for(response_event.wait(), timeout=effective_timeout)

                    if "error" in response_data:
                        error = response_data["error"]
                        error_code = error.get('code')
                        error_msg = error.get('message')
                        raise MarstekAPIError(f"API error {error_code}: {error_msg}")

                    _LOGGER.debug("Command %s completed successfully (attempt %d)", method, attempt)
                    return response_data.get("result")

                except asyncio.TimeoutError:
                    _LOGGER.warning("Command %s timed out after %ss (attempt %d/%d, host=%s)", method, effective_timeout, attempt, attempt_limit, self.host)
                except MarstekAPIError:
                    raise
                except Exception as err:
                    _LOGGER.error("Error sending command %s to %s on attempt %d/%d: %s", method, self.host, attempt, attempt_limit, err, exc_info=True)

                if attempt < attempt_limit:
                    delay = COMMAND_BACKOFF_BASE * (COMMAND_BACKOFF_FACTOR ** (attempt - 1))
                    delay = min(delay, COMMAND_BACKOFF_MAX)
                    if COMMAND_BACKOFF_JITTER > 0:
                        delay += random.uniform(0, COMMAND_BACKOFF_JITTER)
                    _LOGGER.debug("Waiting %.2fs before retrying %s (attempt %d/%d)", delay, method, attempt + 1, attempt_limit)
                    await asyncio.sleep(delay)

        finally:
            self.unregister_handler(handler)

        _LOGGER.error("Command %s failed after %d attempt(s)", method, attempt_limit)
        return None

    async def _send_to_host(self, message: str) -> None:
        """Send message to specific host."""
        if not self.transport:
            raise MarstekAPIError("Not connected")

        self.transport.sendto(message.encode(), (self.host, self.remote_port))

    async def get_device_info(self) -> dict | None:
        """Get device information."""
        return await self.send_command(METHOD_GET_DEVICE, {"ble_mac": "0"})

    async def get_battery_status(self) -> dict | None:
        """Get battery status."""
        return await self.send_command(METHOD_BATTERY_STATUS)


async def test_connection():
    """Test connection to Marstek device."""
    host = "192.168.0.144"
    port = 30000
    
    api = MarstekUDPClient(host=host, port=port, remote_port=port)
    
    try:
        print(f"Connecting to Marstek device at {host}:{port}...")
        await api.connect()
        print("✅ Connected successfully!")
        
        print("Getting device info...")
        device_info = await api.get_device_info()
        if device_info:
            print(f"✅ Device info: {device_info}")
        else:
            print("❌ No device info received")
        
        print("Getting battery status...")
        battery_info = await api.get_battery_status()
        if battery_info:
            print(f"✅ Battery info: {battery_info}")
        else:
            print("❌ No battery info received")
        
    except MarstekAPIError as err:
        print(f"❌ Marstek API Error: {err}")
    except Exception as err:
        print(f"❌ Unexpected error: {err}")
        import traceback
        traceback.print_exc()
    finally:
        await api.disconnect()
        print("Disconnected from device")


if __name__ == "__main__":
    asyncio.run(test_connection())