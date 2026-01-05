"""
UDP Traffic Sniffer for Marstek Protocol Analysis
This helps identify what messages work vs don't work with your device.
"""

import socket
import json
import threading
import time
from datetime import datetime

class UDPSniffer:
    def __init__(self, target_ip="192.168.0.144", target_port=30000):
        self.target_ip = target_ip
        self.target_port = target_port
        self.running = False
        
    def start_monitoring(self, duration=30):
        """Monitor UDP traffic for a specified duration."""
        print(f"=== UDP TRAFFIC MONITOR ===")
        print(f"Target: {self.target_ip}:{self.target_port}")
        print(f"Monitoring for {duration} seconds...")
        print("Now use your working application to connect to the device.")
        print("This will capture the UDP packets to see what works.\n")
        
        self.running = True
        
        # Start listener in background
        listener_thread = threading.Thread(target=self._listen_for_responses)
        listener_thread.daemon = True
        listener_thread.start()
        
        # Wait for specified duration
        time.sleep(duration)
        self.running = False
        
        print(f"\nMonitoring complete.")
    
    def _listen_for_responses(self):
        """Listen for UDP responses from the device."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', 0))  # Bind to any available port
            sock.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(4096)
                    if addr[0] == self.target_ip:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"[{timestamp}] RESPONSE from {addr}:")
                        print(f"  Raw bytes: {len(data)} bytes")
                        print(f"  Data: {data}")
                        
                        try:
                            decoded = data.decode('utf-8')
                            print(f"  UTF-8: {decoded}")
                            
                            try:
                                json_data = json.loads(decoded)
                                print(f"  JSON: {json_data}")
                            except json.JSONDecodeError:
                                print("  (Not valid JSON)")
                        except UnicodeDecodeError:
                            print("  (Not UTF-8 text)")
                        
                        print()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"  Listener error: {e}")
            
            sock.close()
        except Exception as e:
            print(f"Listener setup error: {e}")
    
    def test_different_formats(self):
        """Test various message formats to see which one works."""
        print(f"\n=== TESTING DIFFERENT MESSAGE FORMATS ===")
        print(f"Trying various UDP message formats against {self.target_ip}:{self.target_port}")
        
        # Various formats to try based on different Marstek implementations
        test_messages = [
            # Standard JSON-RPC 2.0
            {"jsonrpc": "2.0", "id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
            
            # Simple JSON-RPC
            {"id": 1, "method": "Marstek.GetDevice", "params": {"ble_mac": "0"}},
            
            # Different parameter formats
            {"id": 1, "method": "Marstek.GetDevice", "params": {"id": 0}},
            {"id": 1, "method": "Marstek.GetDevice", "params": {}},
            {"id": 1, "method": "Marstek.GetDevice"},
            
            # Different method names
            {"id": 1, "method": "GetDevice", "params": {"ble_mac": "0"}},
            {"id": 1, "method": "Device.Get", "params": {"ble_mac": "0"}},
            {"id": 1, "method": "get_device", "params": {"ble_mac": "0"}},
            
            # Other common methods
            {"id": 1, "method": "Wifi.GetStatus", "params": {"id": 0}},
            {"id": 1, "method": "System.GetInfo"},
            {"id": 1, "method": "ping"},
            
            # Raw command formats (if it's not JSON-RPC)
            "GET_DEVICE",
            "get_device_info",
            "status",
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\nTest {i}: {message}")
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(3.0)
                
                # Encode message
                if isinstance(message, dict):
                    data = json.dumps(message).encode('utf-8')
                else:
                    data = str(message).encode('utf-8')
                
                # Send message
                sock.sendto(data, (self.target_ip, self.target_port))
                print(f"  Sent: {len(data)} bytes")
                
                # Try to get response
                try:
                    response_data, addr = sock.recvfrom(4096)
                    print(f"  ✓ RESPONSE! {len(response_data)} bytes from {addr}")
                    
                    try:
                        decoded = response_data.decode('utf-8')
                        print(f"  Content: {decoded}")
                        
                        try:
                            json_response = json.loads(decoded)
                            print(f"  Parsed: {json_response}")
                        except json.JSONDecodeError:
                            pass
                    except UnicodeDecodeError:
                        print(f"  Binary data: {response_data}")
                    
                    sock.close()
                    print(f"\n🎉 SUCCESS! This format works: {message}")
                    return message
                    
                except socket.timeout:
                    print(f"  ✗ No response")
                
                sock.close()
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"\n❌ None of the tested formats got a response.")
        return None

def main():
    sniffer = UDPSniffer("192.168.0.144", 30000)
    
    print("Choose an option:")
    print("1. Test different message formats (recommended first)")
    print("2. Monitor UDP traffic (use while your working app is running)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        working_format = sniffer.test_different_formats()
        if working_format:
            print(f"\n✅ Found working format! You can update the Home Assistant integration to use:")
            print(f"   {working_format}")
    elif choice == "2":
        duration = input("Monitor for how many seconds? (default 30): ").strip()
        duration = int(duration) if duration.isdigit() else 30
        sniffer.start_monitoring(duration)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()