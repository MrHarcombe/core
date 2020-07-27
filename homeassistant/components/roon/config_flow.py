"""Config flow for roon integration."""
import asyncio
import logging

from roon import RoonApi
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_API_KEY, CONF_HOST

from .const import DEFAULT_NAME, DOMAIN, ROON_APPINFO  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({"host": str})

TIMEOUT = 120


class RoonHub:
    """Interact with roon during config flow."""

    def __init__(self, host):
        """Initialize."""
        self._host = host

    async def authenticate(self, hass) -> bool:
        """Test if we can authenticate with the host."""
        token = None
        secs = 0
        try:
            roonapi = RoonApi(ROON_APPINFO, None, self._host, blocking_init=False)
            while secs < TIMEOUT:
                token = roonapi.token
                secs += 5
                if token:
                    break
                await asyncio.sleep(5)

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception %s", error)
            raise CannotConnect

        token = roonapi.token
        roonapi.stop()
        return token


async def authenticate(hass: core.HomeAssistant, host):
    """Connect and authenticate home assistant."""

    hub = RoonHub(host)
    token = await hub.authenticate(hass)
    if token is None:
        raise InvalidAuth

    return {CONF_HOST: host, CONF_API_KEY: token}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for roon."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the Roon flow."""
        self._host = None

    async def async_step_user(self, user_input=None):
        """Handle getting host details from the user."""

        errors = {}
        if user_input is not None:
            try:
                self._host = user_input["host"]
                return await self.async_step_link()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_link(self, user_input=None):
        """Handle linking and authenticting with the roon server."""

        errors = {}
        if user_input is not None:
            try:
                info = await authenticate(self.hass, self._host)
                return self.async_create_entry(title=DEFAULT_NAME, data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(step_id="link", errors=errors)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
