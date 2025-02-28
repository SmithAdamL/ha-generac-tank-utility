import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .const import DOMAIN, CONF_DEVICES

# Import the Home Assistant constants module and retrieve required constants with fallbacks.
import homeassistant.const as ha_const

PERCENTAGE = getattr(ha_const, "PERCENTAGE", "%")
try:
    TEMP_FAHRENHEIT = ha_const.TEMP_FAHRENHEIT
except AttributeError:
    TEMP_FAHRENHEIT = "°F"
try:
    DEVICE_CLASS_TEMPERATURE = ha_const.DEVICE_CLASS_TEMPERATURE
except AttributeError:
    DEVICE_CLASS_TEMPERATURE = "temperature"
try:
    DEVICE_CLASS_BATTERY = ha_const.DEVICE_CLASS_BATTERY
except AttributeError:
    DEVICE_CLASS_BATTERY = "battery"

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Generac Tank Utility sensors for each tank device."""
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
        entities.append(TankLevelSensor(coord, entry, device_id, name))
        entities.append(TankTemperatureSensor(coord, entry, device_id, name))
        entities.append(TankBatterySensor(coord, entry, device_id, name))
    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d sensor entities", len(entities))

class TankUtilitySensorBase(CoordinatorEntity, SensorEntity):
    """Base sensor entity for Generac Tank Utility."""
    def __init__(self, coordinator, config_entry, device_id: str, device_name: str):
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "manufacturer": "Generac",
            "model": "Tank Utility Monitor"
        }
        self._attr_unique_id = f"{device_id}_{self.__class__.__name__}"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None

class TankLevelSensor(TankUtilitySensorBase):
    """Sensor for tank fuel level percentage."""
    def __init__(self, coordinator, config_entry, device_id, device_name):
        super().__init__(coordinator, config_entry, device_id, device_name)
        self._attr_name = f"{device_name} Fuel Level"
        self._attr_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:propane-tank"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        data = self.coordinator.data
        if not data or "tank" not in data:
            return None
        try:
            return round(data["tank"], 1)
        except (ValueError, TypeError):
            return data["tank"]

    @property
    def extra_state_attributes(self):
        attrs = {}
        data = self.coordinator.data or {}
        for key in ("capacity", "fuelType", "orientation", "status", "time_iso"):
            if key in data:
                attrs[key] = data[key]
        if "time_iso" in data:
            attrs["last_update"] = data["time_iso"]
        return attrs

class TankTemperatureSensor(TankUtilitySensorBase):
    """Sensor for tank temperature in °F."""
    def __init__(self, coordinator, config_entry, device_id, device_name):
        super().__init__(coordinator, config_entry, device_id, device_name)
        self._attr_name = f"{device_name} Temperature"
        self._attr_unit_of_measurement = TEMP_FAHRENHEIT
        self._attr_device_class = DEVICE_CLASS_TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        data = self.coordinator.data
        if not data or "temperature" not in data:
            return None
        try:
            return round(data["temperature"], 1)
        except (ValueError, TypeError):
            return data["temperature"]

    @property
    def available(self) -> bool:
        return super().available and "temperature" in (self.coordinator.data or {})

class TankBatterySensor(TankUtilitySensorBase):
    """Sensor for monitor battery level."""
    def __init__(self, coordinator, config_entry, device_id, device_name):
        super().__init__(coordinator, config_entry, device_id, device_name)
        self._attr_name = f"{device_name} Battery"
        self._attr_unit_of_measurement = PERCENTAGE
        self._attr_device_class = DEVICE_CLASS_BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        data = self.coordinator.data
        if not data or "battery_level" not in data:
            return None
        # Battery level is now returned as a string (e.g., "good", "low")
        return data["battery_level"]
    
    @property
    def available(self) -> bool:
        return super().available and "battery_level" in (self.coordinator.data or {})
