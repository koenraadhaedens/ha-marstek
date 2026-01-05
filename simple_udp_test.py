import socket
import json
import time

def simple_udp_test(host, port=30000):
    """Simple UDP test to get raw sensor data"""
    print(f"Testing UDP communication with {host}:{port}")
    
    # Test different methods
    methods = [
        "Marstek.GetDevice",
        "Bat.GetStatus", 
        "PV.GetStatus",
        "ES.GetStatus",
        "EM.GetStatus",
        "Wifi.GetStatus"
    ]
    
    for method in methods:
        print(f"\n--- Testing {method} ---")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            
            request = {"id": 1, "method": method, "params": {"id": 0}}
            message = json.dumps(request)
            print(f"Sending: {message}")
            
            sock.sendto(message.encode(), (host, port))
            
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode())
            
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Check for specific data
            if 'result' in response:
                result = response['result']
                if method == "Bat.GetStatus" and 'bat_temp' in result:
                    temp = result['bat_temp']
                    print(f"Battery temperature raw: {temp} (should be ~{temp/10}°C)")
                
        except socket.timeout:
            print("No response (timeout)")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            sock.close()
        
        time.sleep(1)  # Brief delay between requests

if __name__ == "__main__":
    simple_udp_test("192.168.0.144")