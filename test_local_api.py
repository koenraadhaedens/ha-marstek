"""
Quick test script to verify Marstek Local API is enabled
Run this AFTER enabling Local API via Marstek Venus Monitor tool
"""

import socket
import json
import time

def test_marstek_after_enable(host, port=30000):
    """Test if Local API is now enabled on the device."""
    print(f"Testing Marstek Local API on {host}:{port}")
    print("(Run this AFTER enabling Local API via Marstek Venus Monitor)")
    print("-" * 60)
    
    # Test the standard API call
    request = {
        "id": 1,
        "method": "Marstek.GetDevice",
        "params": {"ble_mac": "0"}
    }
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        
        message = json.dumps(request).encode("utf-8")
        print(f"Sending API request...")
        sock.sendto(message, (host, port))
        
        # Try to receive response
        data, addr = sock.recvfrom(4096)
        response = json.loads(data.decode("utf-8"))
        
        print(f"SUCCESS! Device responded:")
        print(f"  Response: {response}")
        
        if 'result' in response:
            result = response['result']
            print(f"\n  Device Info:")
            if 'device' in result:
                print(f"    Model: {result['device']}")
            if 'ver' in result:
                print(f"    Firmware: v{result['ver']}")
            if 'ble_mac' in result:
                print(f"    BLE MAC: {result['ble_mac']}")
            if 'wifi_mac' in result:
                print(f"    WiFi MAC: {result['wifi_mac']}")
        
        print(f"\n✅ Local API is working! You can now set up Home Assistant integration.")
        sock.close()
        return True
        
    except socket.timeout:
        print(f"❌ No response - Local API may not be enabled yet")
        print(f"   Please use Marstek Venus Monitor to enable Local API first")
        return False
    except json.JSONDecodeError as e:
        print(f"⚠️ Got response but couldn't parse JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("MARSTEK LOCAL API VERIFICATION")
    print("=" * 60)
    
    # Test your device
    result = test_marstek_after_enable("192.168.0.144")
    
    print("\n" + "=" * 60)
    if result:
        print("NEXT STEPS:")
        print("1. ✅ Local API is enabled and working")
        print("2. You can now add your device to Home Assistant")
        print("3. Use IP: 192.168.0.144 and port: 30000")
    else:
        print("REQUIRED ACTION:")
        print("1. Visit: https://rweijnen.github.io/marstek-venus-monitor/latest/")
        print("2. Connect to your device at 192.168.0.144")
        print("3. Enable 'Local API / Open API' option") 
        print("4. Save settings")
        print("5. Run this test script again to verify")
    print("=" * 60)