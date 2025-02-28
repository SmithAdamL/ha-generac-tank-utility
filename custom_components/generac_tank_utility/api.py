import asyncio
import json
import logging
from aiohttp import BasicAuth, ClientResponse
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

# API endpoints for Tank Utility
API_BASE = "https://data.tankutility.com/api"
GET_TOKEN_ENDPOINT = f"{API_BASE}/getToken"
DEVICES_ENDPOINT = f"{API_BASE}/devices"
DEVICE_DATA_ENDPOINT = f"{API_BASE}/devices/{{device_id}}"

class TankUtilityError(HomeAssistantError):
    """Base exception for Tank Utility API errors."""

class InvalidAuth(TankUtilityError):
    """Raised when authentication fails due to invalid credentials."""

class TankUtilityClient:
    """Asynchronous client for interacting with the Tank Utility API using BasicAuth."""

    def __init__(self, hass, email: str, password: str):
        self.hass = hass
        self.email = email
        self.password = password
        self._token = None
        self._lock = asyncio.Lock()
        self._session = async_get_clientsession(hass)

    async def async_get_token(self, force_refresh: bool = False) -> str:
        """Retrieve (and cache) the API token."""
        if self._token and not force_refresh:
            return self._token
        async with self._lock:
            if self._token and not force_refresh:
                return self._token
            _LOGGER.debug("Requesting new API token for Tank Utility")
            try:
                resp: ClientResponse = await self._session.get(
                    GET_TOKEN_ENDPOINT, auth=BasicAuth(self.email, self.password)
                )
            except Exception as err:
                _LOGGER.error("Error connecting to Tank Utility API for token: %s", err)
                raise TankUtilityError("API connection error") from err
            if resp.status == 401:
                _LOGGER.error("Tank Utility authentication failed (HTTP 401)")
                raise InvalidAuth("Invalid Tank Utility credentials")
            if resp.status != 200:
                _LOGGER.error("Token request failed, HTTP %s: %s", resp.status, await resp.text())
                raise TankUtilityError(f"Token request failed with status {resp.status}")
            try:
                data = await resp.json(content_type=None)
            except Exception as e:
                _LOGGER.warning("JSON decode failed with unexpected mimetype, trying fallback: %s", e)
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception as e2:
                    _LOGGER.error("Fallback JSON decoding failed: %s", e2)
                    raise TankUtilityError("Failed to decode token response") from e2
            token = data.get("token")
            if not token:
                _LOGGER.error("No token received from Tank Utility API")
                raise TankUtilityError("No token in response")
            self._token = token
            _LOGGER.debug("Obtained API token")
            return self._token

    async def async_list_devices(self) -> list:
        """Retrieve the list of device IDs associated with the account."""
        token = await self.async_get_token()
        url = f"{DEVICES_ENDPOINT}?token={token}"
        try:
            resp = await self._session.get(url)
        except Exception as err:
            _LOGGER.error("Error fetching device list: %s", err)
            raise TankUtilityError("API connection error") from err
        if resp.status != 200:
            _LOGGER.error("Failed to fetch device list, HTTP %s: %s", resp.status, await resp.text())
            if resp.status == 401:
                raise InvalidAuth("Token expired or invalid for device list")
            raise TankUtilityError(f"Device list request failed with status {resp.status}")
        try:
            data = await resp.json(content_type=None)
        except Exception as e:
            _LOGGER.warning("JSON decode failed for device list, using fallback: %s", e)
            text = await resp.text()
            try:
                data = json.loads(text)
            except Exception as e2:
                _LOGGER.error("Fallback JSON decoding for device list failed: %s", e2)
                raise TankUtilityError("Failed to decode device list response") from e2
        devices = data.get("devices", [])
        _LOGGER.debug("Device list: %s", devices)
        return devices

    async def async_get_device_data(self, device_id: str) -> dict:
        """Retrieve the latest data for a specific tank device."""
        token = await self.async_get_token()
        url = f"{DEVICE_DATA_ENDPOINT.format(device_id=device_id)}?token={token}"
        try:
            resp = await self._session.get(url)
        except Exception as err:
            _LOGGER.error("Error fetching data for device %s: %s", device_id, err)
            raise TankUtilityError("API connection error") from err
        if resp.status == 401:
            _LOGGER.warning("Token expired for device %s, refreshing token", device_id)
            await self.async_get_token(force_refresh=True)
            resp = await self._session.get(url)
        if resp.status != 200:
            _LOGGER.error("Failed to fetch data for device %s (HTTP %s)", device_id, resp.status)
            if resp.status == 401:
                raise InvalidAuth("Unauthorized for device data")
            raise TankUtilityError(f"Device data request failed with status {resp.status}")
        try:
            raw_data = await resp.json(content_type=None)
        except Exception as e:
            _LOGGER.warning("JSON decode failed for device data, using fallback: %s", e)
            text = await resp.text()
            try:
                raw_data = json.loads(text)
            except Exception as e2:
                _LOGGER.error("Fallback JSON decoding for device data failed: %s", e2)
                raise TankUtilityError("Failed to decode device data response") from e2
        device_info = raw_data.get("device", {})
        last_reading = device_info.pop("lastReading", {}) if isinstance(device_info, dict) else {}
        data = {**device_info, **last_reading}
        _LOGGER.debug("Fetched data for device %s: %s", device_id, data)
        return data
