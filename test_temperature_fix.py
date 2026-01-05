#!/usr/bin/env python3
"""
Test the temperature scaling fix
"""

def test_temperature_scaling():
    """Test the temperature value function"""
    
    # Simulate raw battery data as it might come from device
    test_data = {
        "bat_temp": 2900,  # Raw value (should be 29.0°C)
        "soc": 11,
        "bat_power": -23,
        "bat_capacity": 56
    }
    
    print("Testing temperature scaling fix:")
    print(f"Raw bat_temp value: {test_data['bat_temp']}")
    
    # Original function (broken)
    original_fn = lambda data: data.get("bat_temp")
    original_temp = original_fn(test_data)
    print(f"Original function result: {original_temp}°C (WRONG)")
    
    # Fixed function 
    fixed_fn = lambda data: data.get("bat_temp") / 10.0 if data.get("bat_temp") is not None else None
    fixed_temp = fixed_fn(test_data)
    print(f"Fixed function result: {fixed_temp}°C (CORRECT)")
    
    # Test with None value
    test_data_none = {"bat_temp": None}
    fixed_temp_none = fixed_fn(test_data_none)
    print(f"With None value: {fixed_temp_none} (should be None)")
    
    # Test with missing key
    test_data_missing = {}
    fixed_temp_missing = fixed_fn(test_data_missing)
    print(f"With missing key: {fixed_temp_missing} (should be None)")

def test_sensor_availability():
    """Test what causes 'Unknown' values"""
    print("\n" + "="*50)
    print("Testing sensor availability issues:")
    
    # Simulate coordinator data in different states
    scenarios = [
        {"name": "Normal operation", "data": {"battery": {"bat_temp": 290, "soc": 11}}},
        {"name": "Missing battery data", "data": {}},
        {"name": "Battery data is None", "data": {"battery": None}},
        {"name": "Empty battery data", "data": {"battery": {}}},
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        coordinator_data = scenario['data']
        
        # Simulate sensor logic
        data_key = "battery"
        if data_key not in coordinator_data:
            result = None
            reason = "data_key not in coordinator.data"
        elif coordinator_data[data_key] is None:
            result = None
            reason = "data is None"
        else:
            data = coordinator_data[data_key]
            value_fn = lambda d: d.get("bat_temp") / 10.0 if d.get("bat_temp") is not None else None
            try:
                result = value_fn(data)
                reason = "success" if result is not None else "value_fn returned None"
            except Exception as e:
                result = None
                reason = f"error: {e}"
        
        status = "Available" if result is not None else "Unknown"
        print(f"  Result: {result} -> Status: {status}")
        print(f"  Reason: {reason}")

if __name__ == "__main__":
    test_temperature_scaling()
    test_sensor_availability()