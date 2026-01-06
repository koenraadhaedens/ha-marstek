"""
Advanced Marstek protocol testing
Try different variations based on the working integration analysis
"""

import socket
import json
import time

def test_protocol_variations(host, port=30000):
    """Test different protocol variations to match working application."""
    
    print(f"Testing protocol variations on {host}:{port}")
    print("=" * 50)
    
    # Various request formats based on analysis of working integration
    test_cases = [
        {
            "name": "Standard (current)",
            "request": {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
        },
        {
            "name": "Discovery format (id=0)",
            "request": {"id": 0, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
        },
        {
            "name": "Integer params",
            "request": {"id": 1, "method": "Marstek.GetDevice", "params": {"id": 0}}
        },
        {
            "name": "No params",
            "request": {"id": 1, "method": "Marstek.GetDevice"}
        },
        {
            "name": "Empty params",
            "request": {"id": 1, "method": "Marstek.GetDevice", "params": {}}
        },
        {
            "name": "Different method name",
            "request": {"id": 1, "method": "GetDevice", "params": {"ble_mac": "0"}}
        },
        {
            "name": "With JSON-RPC version",
            "request": {"jsonrpc": "2.0", "id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}}
        },
        {
            "name": "WiFi status test",
            "request": {"id": 1, "method": "Wifi.GetStatus", "params": {"id": 0}}
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Request: {test_case['request']}")
        
        try:
            # Test with different socket configurations
            for bind_attempt in ["same_port", "ephemeral", "reuse_port"]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    
                    if bind_attempt == "same_port":
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        try:
                            sock.bind(('', port))
                            print(f"  → Bound to port {port}")
                        except OSError:
                            continue
                    elif bind_attempt == "reuse_port":
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        if hasattr(socket, 'SO_REUSEPORT'):
                            try:
                                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                                sock.bind(('', port))
                                print(f"  → Bound to port {port} with REUSEPORT")
                            except (OSError, AttributeError):
                                continue
                        else:
                            continue
                    else:  # ephemeral
                        sock.bind(('', 0))
                        local_port = sock.getsockname()[1]
                        print(f"  → Using ephemeral port {local_port}")
                    
                    sock.settimeout(3.0)
                    
                    # Send request
                    message = json.dumps(test_case['request']).encode('utf-8')
                    sock.sendto(message, (host, port))
                    
                    # Try to get response
                    data, addr = sock.recvfrom(4096)
                    response = json.loads(data.decode('utf-8'))
                    
                    print(f"  ✓ SUCCESS with {bind_attempt}!")
                    print(f"    Response: {response}")
                    sock.close()
                    return test_case, bind_attempt, response
                    
                except socket.timeout:
                    print(f"  ✗ Timeout with {bind_attempt}")
                except Exception as e:
                    print(f"  ✗ Error with {bind_attempt}: {e}")
                
                try:
                    sock.close()
                except:
                    pass
                    
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    return None, None, None

def test_raw_udp_scan(host, port=30000):
    """Test if ANY UDP traffic gets a response."""
    print(f"\nTesting raw UDP responses from {host}:{port}")
    
    test_messages = [
        b"ping",
        b"hello", 
        b'{"test": true}',
        b'{"id":1,"method":"ping"}',
        json.dumps({"id": 1, "method": "System.GetInfo"}).encode('utf-8'),
    ]
    
    for msg in test_messages:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(msg, (host, port))
            
            data, addr = sock.recvfrom(1024)
            print(f"  ✓ Response to {msg}: {data}")
            sock.close()
            return True
        except socket.timeout:
            pass
        except Exception as e:
            print(f"  Error with {msg}: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    print("  ✗ No responses to any raw UDP messages")
    return False

if __name__ == "__main__":
    print("ADVANCED MARSTEK PROTOCOL TESTING")
    print("=" * 50)
    
    # Test protocol variations
    success_case, success_method, response = test_protocol_variations("192.168.0.144")
    
    if success_case:
        print(f"\n🎉 FOUND WORKING PROTOCOL!")
        print(f"Method: {success_method}")
        print(f"Request: {success_case['request']}")
        print(f"Response: {response}")
    else:
        print(f"\n❌ No working protocol found")
        
        # Test if device responds to ANY UDP traffic
        if test_raw_udp_scan("192.168.0.144"):
            print("Device responds to some UDP traffic - protocol issue")
        else:
            print("Device doesn't respond to any UDP traffic")
            
    print("\n" + "=" * 50)