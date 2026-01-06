# Marstek Integration - Troubleshooting Guide

## Common Timeout Issues and Solutions

### Understanding the Error Messages

The error messages you're seeing indicate communication problems:

```
Command BLE.GetStatus timed out after 10s (attempt 1/3, host=192.168.0.144)
Command BLE.GetStatus timed out after 10s (attempt 2/3, host=192.168.0.144)
Command BLE.GetStatus timed out after 10s (attempt 3/3, host=192.168.0.144)
Command Bat.GetStatus timed out after 10s (attempt 1/1, host=192.168.0.144)
```

This means:
- The integration is trying to communicate with your device
- Each command gets 10 seconds to complete
- It retries up to 3 times for most commands
- The device at IP 192.168.0.144 is not responding within the timeout

## Step-by-Step Troubleshooting

### 1. Check Device Status
- Open the Marstek mobile app
- Verify your device shows as "Online"
- Check the device's IP address matches what's configured
- Ensure "Open API" is still enabled

### 2. Network Connectivity Test
From your Home Assistant host, test network connectivity:

```bash
# Ping the device
ping 192.168.0.144

# Test UDP port connectivity (if you have nmap installed)
nmap -sU -p 30000 192.168.0.144

# Alternative test with telnet (won't fully work for UDP but shows basic connectivity)
telnet 192.168.0.144 30000
```

### 3. Check Network Configuration

**WiFi Signal Strength:**
- Weak WiFi can cause intermittent timeouts
- Check signal strength in the Marstek app
- Consider moving closer to WiFi router or using WiFi extender

**Network Congestion:**
- High network traffic can cause delays
- Try testing at different times of day
- Consider using wired Ethernet if available

**Router Issues:**
- Some routers have UDP packet filtering
- Check router logs for dropped packets
- Temporarily disable router firewall to test

### 4. Device-Specific Solutions

**Static IP Address:**
Ensure the device has a static IP to prevent IP changes:
1. In your router: Reserve the IP for the device's MAC address
2. Or in Marstek app: Set static IP (if supported)

**Firmware Updates:**
- Check for device firmware updates in the Marstek app
- Older firmware may have communication issues

**Device Restart:**
- Power cycle the Marstek device
- Wait 2 minutes after restart before testing

### 5. Integration Configuration

**Reload Integration:**
1. Go to Settings → Devices & Services
2. Find "Marstek Battery System"
3. Click the three dots → "Reload"

**Reconfigure with Different Settings:**
1. Remove the integration
2. Re-add with modified settings:
   - Try a different UDP port (49152-65535)
   - Verify IP address is correct

### 6. Advanced Network Diagnostics

**Check UDP Traffic (Linux/Mac):**
```bash
# Monitor UDP traffic to/from the device
sudo tcpdump -i any -n udp and host 192.168.0.144

# Check if packets are being sent/received
sudo netstat -su | grep -i udp
```

**Windows Network Test:**
```powershell
# Test network path
Test-NetConnection 192.168.0.144 -Port 30000 -InformationLevel Detailed

# Check UDP connectivity
Test-NetConnection 192.168.0.144 -Port 30000 -Protocol UDP
```

### 7. Home Assistant Logs Analysis

Enable debug logging to see detailed information:

```yaml
# Add to configuration.yaml
logger:
  default: info
  logs:
    custom_components.marstek: debug
    custom_components.marstek.marstek_api: debug
```

Look for these patterns in logs:
- "Sent request:" - Shows requests being sent
- "Received response:" - Shows successful responses
- "Command ... timed out" - Shows failed attempts
- Socket errors - Indicates network problems

### 8. Firewall and Security

**Home Assistant Host Firewall:**
- Ensure outbound UDP traffic is allowed
- Check iptables rules (Linux) or Windows Firewall

**Router Firewall:**
- Some routers block inter-device communication
- Look for "AP Isolation" or "Client Isolation" settings
- Ensure devices are on same VLAN

### 9. Alternative Solutions

**If timeouts persist:**

**Option 1: Increase Update Interval**
Edit `custom_components/marstek/__init__.py`:
```python
SCAN_INTERVAL = timedelta(seconds=60)  # Change from 30 to 60 seconds
```

**Option 2: Use Ethernet Instead of WiFi**
- Connect device via wired Ethernet if possible
- More reliable than WiFi for consistent communication

**Option 3: Network Optimization**
- Use 2.4GHz WiFi (better range than 5GHz)
- Position device closer to router
- Reduce interference from other devices

## Quick Fix Checklist

Try these in order:

1. ✅ **Power cycle the Marstek device** (wait 2 minutes)
2. ✅ **Check device is online in Marstek app**
3. ✅ **Verify IP address hasn't changed**
4. ✅ **Reload the integration in HA**
5. ✅ **Check WiFi signal strength**
6. ✅ **Test ping to device from HA host**
7. ✅ **Restart Home Assistant**
8. ✅ **Check router logs for issues**

## When to Seek Help

Contact support if:
- All troubleshooting steps have been tried
- Device works fine in Marstek app but not HA
- Issues started after specific changes (router firmware, etc.)
- Multiple Marstek devices on same network all have issues

## Prevention Tips

**For Stable Operation:**
- Use static IP addresses
- Regular firmware updates
- Monitor WiFi signal strength
- Use wired connection when possible
- Schedule device reboots monthly
- Keep HA and integration updated

## Performance Monitoring

Create a simple automation to track communication health:

```yaml
automation:
  - alias: "Marstek: Log Communication Health"
    trigger:
      - platform: time_pattern
        minutes: "/10"  # Every 10 minutes
    action:
      - service: logbook.log
        data:
          name: "Marstek Health Check"
          message: >
            Battery SOC: {{ states('sensor.marstek_battery_state_of_charge') }}%
            Last Updated: {{ as_timestamp(states.sensor.marstek_battery_state_of_charge.last_updated) | timestamp_custom('%H:%M:%S') }}
```

This helps track when communication issues occur and identify patterns.