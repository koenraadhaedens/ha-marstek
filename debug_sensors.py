#!/usr/bin/env python3
"""
Debug script to see raw API responses and identify data parsing issues.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the custom component to Python path
sys.path.insert(0, str(Path(__file__).parent / "custom_components" / "marstek"))

from marstek_api import MarstekAPI

logging.basicConfig(level=logging.INFO)

async def debug_raw_data(ip_address: str):
    """Get raw data from all API endpoints and show the structure."""
    print(f"🔍 Debugging raw API data from {ip_address}")
    print("="*70)
    
    api = MarstekAPI(host=ip_address, port=30000, timeout=10.0)
    
    try:
        await api.connect()
        
        # Test all endpoints and show raw data
        endpoints = {
            "Device Info": api.get_device_info,
            "Battery Status": api.get_battery_status,
            "PV Status": api.get_pv_status,
            "ES Status": api.get_es_status,
            "ES Mode": api.get_es_mode,
            "EM Status": api.get_em_status,
            "WiFi Status": api.get_wifi_status,
            "BLE Status": api.get_ble_status,
        }
        
        for name, func in endpoints.items():
            print(f"\n📡 {name}:")
            try:
                result = await func(timeout=5, max_attempts=1)
                if result:
                    print(json.dumps(result, indent=2))
                    
                    # Specific checks for problematic data
                    if name == "Battery Status" and "bat_temp" in result:
                        temp = result["bat_temp"]
                        print(f"   🌡️ Raw temperature value: {temp} (type: {type(temp)})")
                        if isinstance(temp, (int, float)) and temp > 100:
                            print(f"   ⚠️ Temperature seems too high: {temp}°C")
                            print(f"   💡 Corrected (÷10): {temp / 10}°C")
                else:
                    print("   ❌ No data returned")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await api.disconnect()

if __name__ == "__main__":
    ip = input("Enter device IP address: ").strip()
    if ip:
        asyncio.run(debug_raw_data(ip))
    else:
        print("No IP address provided")