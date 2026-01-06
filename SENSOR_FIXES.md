# Marstek Sensor Issues - Fixes Applied

## Issues Identified and Fixed

### 1. Temperature Scaling Issue (290°C instead of 29°C)
**Problem**: Battery temperature showing 290°C instead of correct 29°C
**Root Cause**: Raw sensor data is in 0.1°C units but wasn't being scaled
**Fix**: Updated `battery_temperature` sensor to divide by 10.0

```python
# Before (WRONG):
value_fn=lambda data: data.get("bat_temp"),

# After (FIXED):
value_fn=lambda data: data.get("bat_temp") / 10.0 if data.get("bat_temp") is not None else None,
```

### 2. "Unknown" Sensor Values
**Problem**: Many sensors showing "Unknown" instead of values
**Root Causes**:
- API timeouts due to short timeout values
- No data caching when API calls fail
- Poor error handling in sensor value functions

**Fixes Applied**:

#### A. Improved API Timeouts and Retry Logic
- Increased timeouts from 5s to 8-10s for better reliability
- Increased max_attempts from 1 to 2-3 for first updates
- Added multiple parameter format attempts for API calls

#### B. Data Caching System
- Added `_cached_data` to preserve previous successful values
- When API calls fail, sensors continue showing last known good values
- Prevents sensors from jumping to "Unknown" during temporary communication issues

#### C. Enhanced Error Handling
- Added try-catch blocks in sensor value functions
- Better handling of None/missing data scenarios
- Debug logging for troubleshooting without crashing sensors

#### D. Multiple API Parameter Formats
- Updated key API methods to try different parameter formats:
  - `{"id": 0}`
  - `{"ble_mac": "0"}`
  - `None` (no parameters)
  - `{}` (empty parameters)

This improves compatibility with different device firmware versions.

## Files Modified

1. **sensor.py**:
   - Fixed temperature scaling
   - Enhanced error handling in `native_value` property

2. **__init__.py** (DataUpdateCoordinator):
   - Added data caching system
   - Improved timeout values
   - Better error recovery

3. **marstek_api.py**:
   - Added multi-format parameter attempts for API calls
   - Improved retry logic for key methods

## Expected Results

After these fixes:
- ✅ Battery temperature should show ~29°C instead of 290°C
- ✅ Fewer sensors showing "Unknown" - they'll retain last known values
- ✅ Better communication reliability with the device
- ✅ Sensors will be more stable during network hiccups

## Testing the Fixes

To test the temperature fix:
```bash
python test_temperature_fix.py
```

To restart Home Assistant with the fixes:
1. Restart Home Assistant
2. Monitor the sensors - temperature should be corrected immediately
3. Watch for reduced "Unknown" values over time as caching takes effect

## Additional Troubleshooting

If you still see many "Unknown" values, check:

1. **Network connectivity**: Ensure your Home Assistant can reach `192.168.0.144:30000`
2. **Device state**: The Marstek device might be in a sleep/standby mode
3. **Firmware version**: Your device shows firmware ver 153 - some API calls might not be supported
4. **Log analysis**: Check Home Assistant logs for Marstek-related errors

The caching system means that once a sensor gets a good reading, it will keep that value even if subsequent API calls fail, reducing the "Unknown" problem significantly.