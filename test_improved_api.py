#!/usr/bin/env python3
"""
Test script to demonstrate the improved Marstek API with better timeout handling.
This script shows the key improvements over the original implementation.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the custom component to Python path
sys.path.insert(0, str(Path(__file__).parent / "custom_components" / "marstek"))

from marstek_api import MarstekAPI

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_device_connection(ip_address: str):
    """Test the improved API implementation."""
    print(f"\n🔧 Testing Improved Marstek API with device at {ip_address}")
    print("="*70)
    
    api = MarstekAPI(host=ip_address, port=30000, timeout=15.0)
    
    try:
        print("\n1. 🔌 Connecting to device...")
        await api.connect()
        print("   ✅ Connected successfully!")
        
        print(f"\n2. 📋 Getting device information...")
        start_time = time.time()
        device_info = await api.get_device_info(timeout=10, max_attempts=3)
        elapsed = time.time() - start_time
        
        if device_info:
            print(f"   ✅ Device info retrieved in {elapsed:.2f}s")
            print(f"   📱 Device: {device_info.get('device', 'Unknown')}")
            print(f"   📶 WiFi MAC: {device_info.get('wifi_mac', 'N/A')}")
            print(f"   🔷 BLE MAC: {device_info.get('ble_mac', 'N/A')}")
            print(f"   📍 IP: {device_info.get('ip', ip_address)}")
        else:
            print(f"   ❌ Failed to get device info after {elapsed:.2f}s")
            return
        
        # Test multiple API calls with proper delays
        print(f"\n3. 🔋 Testing multiple API calls with retry logic...")
        
        test_calls = [
            ("Battery Status", api.get_battery_status),
            ("Energy System Status", api.get_es_status),
            ("WiFi Status", api.get_wifi_status),
            ("PV Status", api.get_pv_status),
            ("Energy System Mode", api.get_es_mode),
        ]
        
        success_count = 0
        total_time = 0
        
        for name, method in test_calls:
            print(f"   📊 {name}...")
            start_time = time.time()
            
            try:
                result = await method(timeout=15, max_attempts=3)
                elapsed = time.time() - start_time
                total_time += elapsed
                
                if result:
                    print(f"      ✅ Success in {elapsed:.2f}s")
                    success_count += 1
                    
                    # Show some key data points
                    if name == "Battery Status" and isinstance(result, dict):
                        soc = result.get('soc')
                        if soc is not None:
                            print(f"         🔋 SOC: {soc}%")
                    
                    elif name == "Energy System Status" and isinstance(result, dict):
                        bat_power = result.get('bat_power')
                        if bat_power is not None:
                            print(f"         ⚡ Battery Power: {bat_power}W")
                else:
                    print(f"      ❌ No data returned in {elapsed:.2f}s")
                    
            except Exception as err:
                elapsed = time.time() - start_time  
                total_time += elapsed
                print(f"      ❌ Error in {elapsed:.2f}s: {err}")
            
            # Small delay between calls to be kind to the device
            await asyncio.sleep(0.5)
        
        print(f"\n4. 📈 Results Summary:")
        print(f"   ✅ Success Rate: {success_count}/{len(test_calls)} ({success_count/len(test_calls)*100:.1f}%)")
        print(f"   ⏱️  Total Time: {total_time:.2f}s")
        print(f"   🚀 Average per call: {total_time/len(test_calls):.2f}s")
        
        # Show command statistics
        print(f"\n5. 📊 Command Statistics:")
        stats = api.get_all_command_stats()
        for method, method_stats in stats.items():
            total_attempts = method_stats.get('total_attempts', 0)
            total_success = method_stats.get('total_success', 0)
            total_timeouts = method_stats.get('total_timeouts', 0)
            last_latency = method_stats.get('last_latency')
            
            success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
            print(f"   📋 {method}:")
            print(f"      • Success: {total_success}/{total_attempts} ({success_rate:.1f}%)")
            print(f"      • Timeouts: {total_timeouts}")
            if last_latency is not None:
                print(f"      • Last latency: {last_latency:.2f}s")
        
    except Exception as err:
        print(f"   ❌ Connection failed: {err}")
        
    finally:
        print(f"\n6. 🔌 Disconnecting...")
        try:
            await api.disconnect()
            print("   ✅ Disconnected successfully!")
        except Exception as err:
            print(f"   ⚠️  Disconnect error: {err}")

async def test_discovery():
    """Test device discovery."""
    print(f"\n🔍 Testing Device Discovery")
    print("="*50)
    
    api = MarstekAPI(host=None, port=30000)  # No host for discovery
    
    try:
        await api.connect()
        print("📡 Broadcasting discovery packets...")
        
        devices = await api.discover_devices(timeout=9)
        
        if devices:
            print(f"✅ Found {len(devices)} device(s):")
            for i, device in enumerate(devices, 1):
                print(f"   {i}. {device.get('device', 'Unknown')} at {device.get('ip', 'Unknown IP')}")
                print(f"      MAC: {device.get('wifi_mac', device.get('ble_mac', 'N/A'))}")
            return devices[0]['ip']  # Return first device IP
        else:
            print("❌ No devices found")
            return None
            
    except Exception as err:
        print(f"❌ Discovery failed: {err}")
        return None
    finally:
        try:
            await api.disconnect()
        except:
            pass

async def main():
    """Main test function."""
    print("🚀 Marstek API Improvement Test")
    print("This test demonstrates the key improvements over the original implementation:")
    print("  • Async UDP communication with shared sockets")
    print("  • Proper retry logic with exponential backoff")
    print("  • Connection pooling and reuse")
    print("  • Tiered polling intervals")
    print("  • Comprehensive error handling and statistics")
    print("")
    
    # First try discovery
    ip_address = await test_discovery()
    
    if not ip_address:
        # Fallback to manual IP if discovery fails
        ip_address = input("\nEnter device IP address (or press Enter to exit): ").strip()
        if not ip_address:
            print("Exiting...")
            return
    
    # Test the connection
    await test_device_connection(ip_address)
    
    print(f"\n🎉 Test completed!")
    print(f"\nKey improvements demonstrated:")
    print(f"  ✅ Async/await instead of blocking socket operations")
    print(f"  ✅ Shared UDP sockets with connection pooling") 
    print(f"  ✅ Exponential backoff retry logic")
    print(f"  ✅ Comprehensive timeout and error handling")
    print(f"  ✅ Command statistics and diagnostics")
    print(f"  ✅ Proper resource cleanup")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()