import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TankUtilityClient, TankUtilityError, InvalidAuth
from .const import (
    DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_DEVICES, CONF_ENABLE_MQTT,
    DEFAULT_SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Generac Tank Utility integration from a config entry."""
    _LOGGER.info("Setting up Generac Tank Utility for account %s", entry.data.get(CONF_EMAIL))
    hass.data.setdefault(DOMAIN, {})
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    devices = entry.data.get(CONF_DEVICES, [])
    client = TankUtilityClient(hass, email, password)
    coordinators = {}
    for device in devices:
        device_id = device["id"]
        _LOGGER.debug("Creating coordinator for device %s", device_id)
        interval = DEFAULT_SCAN_INTERVAL  # Use default interval
        coordinators[device_id] = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"generac_tank_utility_{device_id}",
            update_method=lambda dev_id=device_id: _fetch_tank_data(hass, client, dev_id, entry),
            update_interval=timedelta(seconds=interval)
        )
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinators": coordinators,
        "options": entry.options
    }
    # Forward platforms in a background task to avoid blocking the event loop.
    hass.async_create_task(hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"]))
    for coord in coordinators.values():
        await coord.async_config_entry_first_refresh()
    return True

async def _fetch_tank_data(hass: HomeAssistant, client: TankUtilityClient, device_id: str, entry) -> dict:
    """Fetch data for a tank device. MQTT publishing code remains for future use."""
    try:
        data = await client.async_get_device_data(device_id)
    except InvalidAuth as err:
        _LOGGER.error("Authentication failed for device %s: %s", device_id, err)
        raise ConfigEntryAuthFailed from err
    except TankUtilityError as err:
        _LOGGER.error("Error fetching data for device %s: %s", device_id, err)
        raise UpdateFailed(f"Device {device_id} update failed: {err}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected error fetching data for device %s: %s", device_id, err)
        raise UpdateFailed(f"Unexpected error: {err}") from err

    # MQTT publishing code is retained for future use but not enabled via UI.
    if entry.options.get(CONF_ENABLE_MQTT):
        try:
            topic_prefix = f"homeassistant/{DOMAIN}/{device_id}"
            await hass.services.async_call(
                "mqtt", "publish",
                {"topic": f"{topic_prefix}/tank", "payload": str(data.get("tank")), "retain": False},
                blocking=True
            )
            await hass.services.async_call(
                "mqtt", "publish",
                {"topic": f"{topic_prefix}/temperature", "payload": str(data.get("temperature")), "retain": False},
                blocking=True
            )
            if "battery_level" in data:
                await hass.services.async_call(
                    "mqtt", "publish",
                    {"topic": f"{topic_prefix}/battery", "payload": str(data.get("battery_level")), "retain": False},
                    blocking=True
                )
            _LOGGER.debug("Published MQTT data for device %s", device_id)
        except Exception as err:
            _LOGGER.warning("Failed to publish MQTT data for device %s: %s", device_id, err)
    return data

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Generac Tank Utility integration."""
    _LOGGER.info("Unloading Generac Tank Utility for account %s", entry.data.get(CONF_EMAIL))
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "binary_sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
