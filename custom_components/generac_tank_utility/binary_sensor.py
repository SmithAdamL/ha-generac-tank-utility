import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
try:
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass
except ImportError:
    BinarySensorDeviceClass = type("BinarySensorDeviceClass", (), {"BATTERY": "battery", "PROBLEM": "problem"})

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOW_FUEL_THRESHOLD, LOW_BATTERY_THRESHOLD, CONF_DEVICES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary sensors for low fuel and low battery alerts."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinators = data["coordinators"]
    devices = entry.data.get(CONF_DEVICES, [])
    entities = []
    for device in devices:
        device_id = device["id"]
        name = device.get("name", f"Tank {device_id[:6]}")
        coord = coordinators.get(device_id)
        if not coord:
            continue
        entities.append(TankLowFuelBinarySensor(coord, device_id, name))
        entities.append(TankLowBatteryBinarySensor(coord, device_id, name))
    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d binary sensor entities", len(entities))

class TankUtilityBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor for Generac Tank Utility."""
    def __init__(self, coordinator, device_id: str, device_name: str):
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "manufacturer": "Generac",
            "model": "Tank Utility Monitor"
        }

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

class TankLowFuelBinarySensor(TankUtilityBinarySensorBase):
    """Binary sensor that is on when fuel level is low."""
    def __init__(self, coordinator, device_id, device_name):
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Low Fuel"
        self._attr_unique_id = f"{device_id}_low_fuel"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        data = self.coordinator.data
        if not data or "tank" not in data:
            return False
        try:
            return float(data["tank"]) <= LOW_FUEL_THRESHOLD
        except (ValueError, TypeError):
            return False

    @property
    def available(self):
        return super().available and "tank" in (self.coordinator.data or {})

class TankLowBatteryBinarySensor(TankUtilityBinarySensorBase):
    """Binary sensor that is on when battery level is low."""
    def __init__(self, coordinator, device_id, device_name):
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Low Battery"
        self._attr_unique_id = f"{device_id}_low_battery"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY

    @property
    def is_on(self):
        data = self.coordinator.data
        if not data or "battery_level" not in data:
            return False
        value = data["battery_level"]
        if isinstance(value, (int, float)):
            return float(value) <= LOW_BATTERY_THRESHOLD
        elif isinstance(value, str):
            # Consider battery status as "low" or "critical" to trigger the binary sensor
            return value.lower() in ["low", "critical"]
        return False

    @property
    def available(self):
        return super().available and "battery_level" in (self.coordinator.data or {})
