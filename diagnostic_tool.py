#!/usr/bin/env python3
"""
Marstek Device Diagnostic Tool
This script helps diagnose connection issues with Marstek devices.
"""

import socket
import json
import time
import sys
from typing import Optional

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")

def test_basic_connectivity(host: str) -> bool:
    """Test basic network connectivity."""
    print(f"Testing basic network connectivity to {host}...")
    
    try:
        import subprocess
        result = subprocess.run(['ping', '-n', '1', host], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Device responds to ping")
            return True
        else:
            print("✗ Device does not respond to ping")
            return False
    except Exception as e:
        print(f"✗ Ping test failed: {e}")
        return False

def test_tcp_ports(host: str, ports: list) -> list:
    """Test TCP connectivity on various ports."""
    print(f"Testing TCP ports on {host}...")
    open_ports = []
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"  ✓ TCP port {port}: OPEN")
                open_ports.append(port)
            else:
                print(f"  ✗ TCP port {port}: CLOSED")
        except Exception as e:
            print(f"  ✗ TCP port {port}: ERROR ({e})")
    
    return open_ports

def test_udp_marstek_api(host: str, port: int = 30000) -> Optional[dict]:
    """Test Marstek UDP API with various request formats."""
    print(f"Testing Marstek UDP API on {host}:{port}...")
    
    # Various request formats to try
    requests = [
        {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
        {"id": 1, "method": "Marstek.GetDevice", "params": {"id": 0}},
        {"jsonrpc": "2.0", "id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
        {"id": 1, "method": "GetDevice", "params": {"ble_mac": "0"}},
        {"id": 1, "method": "Device.GetInfo"},
        {"id": 1, "method": "Wifi.GetStatus", "params": {"id": 0}},
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"  Attempt {i}: {request['method']}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            
            message = json.dumps(request).encode("utf-8")
            sock.sendto(message, (host, port))
            
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode("utf-8"))
            
            print(f"    ✓ SUCCESS! Response: {response}")
            sock.close()
            return response
            
        except socket.timeout:
            print(f"    ✗ Timeout (no response)")
        except json.JSONDecodeError as e:
            print(f"    ⚠ Got response but invalid JSON: {e}")
            print(f"    Raw data: {data}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    return None

def test_device_discovery(timeout: int = 5) -> list:
    """Test device discovery via broadcast."""
    print(f"Testing device discovery (broadcast for {timeout}s)...")
    
    request = {
        "id": 1,
        "method": "Marstek.GetDevice",
        "params": {"ble_mac": "0"}
    }
    
    devices = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        message = json.dumps(request).encode("utf-8")
        sock.sendto(message, ("255.255.255.255", 30000))
        print("  Broadcast sent, listening for responses...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                response = json.loads(data.decode("utf-8"))
                devices.append((addr[0], response))
                print(f"  ✓ Found device at {addr[0]}: {response}")
            except socket.timeout:
                break
            except Exception as e:
                print(f"  ⚠ Error parsing response: {e}")
        
        sock.close()
        
    except Exception as e:
        print(f"  ✗ Discovery error: {e}")
    
    if not devices:
        print("  ✗ No devices found via discovery")
    
    return devices

def test_web_interface(host: str) -> bool:
    """Test if device has a web interface."""
    print(f"Testing web interface on {host}...")
    
    ports_to_try = [80, 8080, 443, 8000]
    for port in ports_to_try:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"  ✓ Web server found on port {port}")
                print(f"    Try: http://{host}:{port if port != 80 else ''}")
                return True
                
        except Exception:
            pass
    
    print("  ✗ No web interface found")
    return False

def main():
    """Main diagnostic routine."""
    if len(sys.argv) != 2:
        print("Usage: python diagnostic_tool.py <device_ip>")
        print("Example: python diagnostic_tool.py 192.168.0.144")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    
    print_header("MARSTEK DEVICE DIAGNOSTIC TOOL")
    print(f"Target Device: {device_ip}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test basic connectivity
    print_header("1. BASIC CONNECTIVITY TEST")
    connectivity_ok = test_basic_connectivity(device_ip)
    
    if not connectivity_ok:
        print("\n❌ CRITICAL: Device is not reachable on the network!")
        print("   - Check device power and network connection")
        print("   - Verify IP address is correct")
        print("   - Check network cables/WiFi connection")
        return
    
    # Test TCP ports
    print_header("2. TCP PORT SCAN")
    common_ports = [80, 443, 8080, 8000, 22, 23, 502, 1883]
    open_tcp_ports = test_tcp_ports(device_ip, common_ports)
    
    # Test web interface
    print_header("3. WEB INTERFACE TEST")
    has_web = test_web_interface(device_ip)
    
    # Test Marstek UDP API
    print_header("4. MARSTEK UDP API TEST")
    api_response = test_udp_marstek_api(device_ip)
    
    # Test device discovery
    print_header("5. DEVICE DISCOVERY TEST")
    discovered_devices = test_device_discovery()
    
    # Summary and recommendations
    print_header("6. DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    
    if api_response:
        print("✅ SUCCESS: Marstek API is working!")
        print(f"   Device info: {api_response}")
        print("   → You can proceed with Home Assistant integration setup")
    else:
        print("❌ ISSUE: Marstek API is not responding")
        print("\n🔍 TROUBLESHOOTING STEPS:")
        
        if open_tcp_ports:
            print(f"   1. Device has open TCP ports: {open_tcp_ports}")
            if has_web:
                print("      → Try accessing web interface to enable API")
        
        if discovered_devices:
            print(f"   2. Found {len(discovered_devices)} device(s) via discovery:")
            for ip, info in discovered_devices:
                print(f"      → Device at {ip}: {info}")
        
        print("\n   3. Common solutions to try:")
        print("      → Reboot the Marstek device (power cycle)")
        print("      → Check device firmware version (may need update)")
        print("      → Look for 'API Enable' or 'Developer Mode' in device settings")
        print("      → Verify device is in 'Station Mode' not 'AP Mode'")
        print("      → Check if router has 'Client Isolation' enabled (disable it)")
        print("      → Try connecting from device's local network segment")
        
        if not open_tcp_ports and not has_web:
            print("   4. Device may be in a locked-down mode:")
            print("      → Check device documentation for reset procedure")
            print("      → Try accessing via mobile app first")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()