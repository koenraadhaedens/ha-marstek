"""Sensor platform for Marstek integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, 
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarstekDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Marstek sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Battery sensors
    sensors = [
        MarstekSensor(
            coordinator,
            "battery",
            "soc",
            "Battery SOC",
            SensorDeviceClass.BATTERY,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "battery",
            "bat_temp",
            "Battery Temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "battery",
            "bat_capacity",
            "Battery Capacity",
            SensorDeviceClass.ENERGY_STORAGE,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "battery",
            "rated_capacity",
            "Battery Rated Capacity",
            SensorDeviceClass.ENERGY_STORAGE,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.MEASUREMENT,
        ),
    ]
    
    # Energy System sensors
    sensors.extend([
        MarstekSensor(
            coordinator,
            "energy_system",
            "bat_soc",
            "System Battery SOC",
            SensorDeviceClass.BATTERY,
            PERCENTAGE,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "bat_cap",
            "System Battery Capacity",
            SensorDeviceClass.ENERGY_STORAGE,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "pv_power",
            "Solar Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "ongrid_power",
            "Grid Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "offgrid_power",
            "Off-Grid Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "bat_power",
            "Battery Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "total_pv_energy",
            "Total Solar Energy",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.TOTAL_INCREASING,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "total_grid_output_energy",
            "Total Grid Output Energy",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.TOTAL_INCREASING,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "total_grid_input_energy",
            "Total Grid Input Energy",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.TOTAL_INCREASING,
        ),
        MarstekSensor(
            coordinator,
            "energy_system",
            "total_load_energy",
            "Total Load Energy",
            SensorDeviceClass.ENERGY,
            UnitOfEnergy.WATT_HOUR,
            SensorStateClass.TOTAL_INCREASING,
        ),
    ])
    
    # Energy Meter sensors
    sensors.extend([
        MarstekSensor(
            coordinator,
            "energy_meter",
            "total_power",
            "Total Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_meter",
            "a_power",
            "Phase A Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_meter",
            "b_power",
            "Phase B Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
        MarstekSensor(
            coordinator,
            "energy_meter",
            "c_power",
            "Phase C Power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
            SensorStateClass.MEASUREMENT,
        ),
    ])
    
    # PV sensors (Venus D only)
    if coordinator.data and coordinator.data.get("pv"):
        sensors.extend([
            MarstekSensor(
                coordinator,
                "pv",
                "pv_power",
                "PV Power",
                SensorDeviceClass.POWER,
                UnitOfPower.WATT,
                SensorStateClass.MEASUREMENT,
            ),
            MarstekSensor(
                coordinator,
                "pv",
                "pv_voltage",
                "PV Voltage",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                SensorStateClass.MEASUREMENT,
            ),
            MarstekSensor(
                coordinator,
                "pv",
                "pv_current",
                "PV Current",
                SensorDeviceClass.CURRENT,
                UnitOfElectricCurrent.AMPERE,
                SensorStateClass.MEASUREMENT,
            ),
        ])
    
    async_add_entities(sensors)


class MarstekSensor(CoordinatorEntity[MarstekDataUpdateCoordinator], SensorEntity):
    """Representation of a Marstek sensor."""

    def __init__(
        self,
        coordinator: MarstekDataUpdateCoordinator,
        component: str,
        sensor_key: str,
        name: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        state_class: SensorStateClass | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._component = component
        self._sensor_key = sensor_key
        self._attr_name = f"Marstek {name}"
        self._attr_unique_id = f"marstek_{component}_{sensor_key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        component_data = self.coordinator.data.get(self._component, {})
        if component_data is None:
            return None
            
        return component_data.get(self._sensor_key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None
            and self.coordinator.data.get(self._component) is not None
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_info = self.coordinator.data.get("device_info", {}) if self.coordinator.data else {}
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.host)},
            "name": f"Marstek {device_info.get('device', 'Device')}",
            "manufacturer": "Marstek",
            "model": device_info.get("device", "Unknown"),
            "sw_version": str(device_info.get("ver", "Unknown")),
            "hw_version": device_info.get("ble_mac", "Unknown"),
        }
