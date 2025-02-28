import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import api
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DEVICES,
    DEFAULT_SCAN_INTERVAL,
    CONF_ENABLE_MQTT,
    DEFAULT_ENABLE_MQTT
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Generac Tank Utility integration."""
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step where user enters credentials."""
        errors = {}
        if user_input is not None:
            email = user_input.get(CONF_EMAIL)
            password = user_input.get(CONF_PASSWORD)
            client = api.TankUtilityClient(self.hass, email, password)
            try:
                devices = await client.async_list_devices()
            except api.InvalidAuth:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid credentials provided for Tank Utility")
            except Exception as err:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Error connecting to Tank Utility API: %s", err)
            else:
                _LOGGER.info("Authenticated successfully; found %d devices", len(devices))
                device_list = []
                for dev_id in devices:
                    try:
                        data = await client.async_get_device_data(dev_id)
                    except Exception as err:
                        _LOGGER.warning("Could not fetch data for device %s: %s", dev_id, err)
                        data = {"id": dev_id, "name": dev_id}
                    name = data.get("name", f"Tank {dev_id[:6]}")
                    device_list.append({"id": dev_id, "name": name})
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                entry_data = {
                    CONF_EMAIL: email,
                    CONF_PASSWORD: password,
                    CONF_DEVICES: device_list
                }
                _LOGGER.debug("Creating config entry with data: %s", entry_data)
                return self.async_create_entry(title=f"Tank Utility ({email})", data=entry_data)
        schema = vol.Schema({
            vol.Required(CONF_EMAIL): str,
            vol.Required(CONF_PASSWORD): str
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        """Handle reauthentication when credentials fail."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth",
                data_schema=vol.Schema({
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str
                }),
                errors={}
            )
        email = user_input.get(CONF_EMAIL)
        password = user_input.get(CONF_PASSWORD)
        client = api.TankUtilityClient(self.hass, email, password)
        errors = {}
        try:
            await client.async_get_token()
        except api.InvalidAuth:
            errors["base"] = "invalid_auth"
            _LOGGER.warning("Reauthentication failed: invalid credentials")
            return self.async_show_form(
                step_id="reauth",
                data_schema=vol.Schema({
                    vol.Required(CONF_EMAIL, default=email): str,
                    vol.Required(CONF_PASSWORD): str
                }),
                errors=errors
            )
        except Exception as err:
            errors["base"] = "cannot_connect"
            _LOGGER.error("Reauthentication connection error: %s", err)
            return self.async_show_form(
                step_id="reauth",
                data_schema=vol.Schema({
                    vol.Required(CONF_EMAIL, default=email): str,
                    vol.Required(CONF_PASSWORD): str
                }),
                errors=errors
            )
        entry = self.hass.config_entries.async_get_entry(self.context.get("entry_id"))
        if entry:
            new_data = {**entry.data, CONF_EMAIL: email, CONF_PASSWORD: password}
            self.hass.config_entries.async_update_entry(entry, data=new_data)
            _LOGGER.info("Reauthentication successful for %s", email)
        return self.async_abort(reason="reauth_successful")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for configuring per-tank intervals and MQTT publishing."""
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            _LOGGER.debug("Saving options: %s", user_input)
            return self.async_create_entry(title="", data=user_input)
        stored_options = self._config_entry.options
        devices = self._config_entry.data.get(CONF_DEVICES, [])
        schema_fields = {}
        for device in devices:
            dev_id = device["id"]
            default_interval = stored_options.get(f"interval_{dev_id}", DEFAULT_SCAN_INTERVAL)
            schema_fields[vol.Required(f"interval_{dev_id}", default=default_interval)] = int
        # MQTT option is not user configurable at this time.
        schema_fields[vol.Optional(CONF_ENABLE_MQTT, default=False)] = bool
        _LOGGER.debug("MQTT option is coming soon and is not user-configurable at this time.")
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_fields))
