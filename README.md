# Marstek Device Integration for Home Assistant

This integration allows you to connect your Marstek energy storage devices (Venus C, Venus E, Venus D) to Home Assistant using the local UDP API.

## Prerequisites

Before installing this integration, you must:

1. **Connect your Marstek device to your network** (WiFi or Ethernet)
2. **Enable the Open API** in the official Marstek mobile app
3. **Set the UDP port** (default is 30000, recommended range: 49152-65535)
4. **Note your device's IP address** (can be found in the app or router settings)

⚠️ **Important**: Enabling the Open API may disable some built-in features of the device to prevent command conflicts.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the "+" button
4. Search for "Marstek Device Integration"
5. Install the integration
6. Restart Home Assistant

### Manual Installation

1. Download this repository
2. Copy the `custom_components/marstek` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Configuration → Integrations
2. Click the "+" button
3. Search for "Marstek Device Integration"
4. Follow the configuration steps:
   - Enter your device's IP address
   - Enter the UDP port (default: 30000)
   - Set update interval (default: 30 seconds)

## Supported Devices

- **Venus C/E**: Battery, Energy System, Energy Meter, WiFi, Bluetooth
- **Venus D**: All of the above plus Photovoltaic (PV) data

## Available Sensors

### Battery Information
- Battery SOC (State of Charge)
- Battery Temperature
- Battery Capacity (current)
- Battery Rated Capacity

### Energy System
- System Battery SOC
- System Battery Capacity
- Solar Power
- Grid Power (on-grid)
- Off-Grid Power
- Battery Power
- Total Solar Energy (lifetime)
- Total Grid Output Energy (lifetime)
- Total Grid Input Energy (lifetime)
- Total Load Energy (lifetime)

### Energy Meter (Power Monitoring)
- Total Power
- Phase A Power
- Phase B Power  
- Phase C Power

### Photovoltaic (Venus D only)
- PV Power
- PV Voltage
- PV Current

## Available Controls (Switches)

### Operating Modes
- Auto Mode
- AI Mode  
- Manual Mode
- Passive Mode

### Battery Controls
- Battery Charging (read-only status)
- Battery Discharge (read-only status)

## Device Discovery

You can also discover devices on your network using the UDP broadcast method:
- The integration will automatically detect your device model
- Multiple devices can be configured if you have more than one Marstek device

## Configuration Options

- **Host**: IP address of your Marstek device
- **UDP Port**: Communication port (default: 30000)
- **Update Interval**: How often to fetch data from the device (in seconds)

## Troubleshooting

### Device Not Found
- Verify the IP address is correct
- Ensure the device is powered on and connected to the network
- Check if the Open API is enabled in the Marstek mobile app
- Verify the UDP port number (default: 30000)

### No Data
- Check that the device is responding to UDP commands
- Try using the device discovery feature
- Verify your Home Assistant can reach the device on the specified port

### Connection Timeouts
- Check network connectivity between Home Assistant and the device
- Try increasing the update interval
- Ensure no firewall is blocking UDP traffic on the specified port

## Technical Details

This integration uses the Marstek Open API Rev 1.0, which communicates via:
- **Protocol**: UDP with JSON-RPC format
- **Default Port**: 30000
- **Authentication**: None required (local network only)
- **Update Method**: Polling

## API Commands Used

- `Marstek.GetDevice` - Device discovery and info
- `Bat.GetStatus` - Battery status
- `ES.GetStatus` - Energy system status
- `ES.GetMode` - Current operating mode
- `ES.SetMode` - Change operating mode
- `EM.GetStatus` - Energy meter readings
- `PV.GetStatus` - Photovoltaic data (Venus D)
- `Wifi.GetStatus` - Network information
- `BLE.GetStatus` - Bluetooth status

## Development

This integration is based on the Marstek Device Open API (Rev 1.0). The main files that handle device communication:

- `marstek_api.py`: UDP JSON-RPC communication
- `sensor.py`: Sensor definitions and data mapping
- `switch.py`: Control switches for device modes
- `coordinator.py`: Data update coordination

## Support

If you encounter any issues:

1. Enable debug logging for `custom_components.marstek`
2. Check the Home Assistant logs for error messages
3. Verify your device's Open API is enabled and accessible
4. Create an issue in this repository with logs and device model info

## License

MIT License
