"""Test script to verify Marstek device connectivity."""
import asyncio
import logging
import sys
import os

# Add the custom components directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import from the custom components directory
from custom_components.marstek.marstek_api import MarstekUDPClient, MarstekAPIError

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

class MockHass:
    """Mock Home Assistant for testing."""
    pass

async def test_connection():
    """Test connection to Marstek device."""
    host = "192.168.0.144"
    port = 30000
    
    hass = MockHass()
    api = MarstekUDPClient(hass, host=host, port=port, remote_port=port)
    
    try:
        print(f"Connecting to Marstek device at {host}:{port}...")
        await api.connect()
        print("✅ Connected successfully!")
        
        print("Getting device info...")
        device_info = await api.get_device_info()
        print(f"✅ Device info: {device_info}")
        
        print("Getting battery status...")
        battery_info = await api.get_battery_status()
        print(f"✅ Battery info: {battery_info}")
        
        print("Getting all data...")
        all_data = await api.get_all_data()
        print(f"✅ All data keys: {list(all_data.keys())}")
        
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