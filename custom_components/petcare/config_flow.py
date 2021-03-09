"""Adds config flow for Petcare integration."""
import logging

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .petcare import Petcare

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): int, vol.Required(CONF_PASSWORD): str}
)


async def validate_input(hass: core.HomeAssistant, email, password):
    """Validate the user input allows us to connect."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data[CONF_USERNAME] == email:
            raise AlreadyConfigured

    token = await Petcare(email, password, async_get_clientsession(hass)).login()
    if token is None:
        _LOGGER.info("Petcare: Failed to login to retrieve token")
        raise CannotConnect


class PetcareConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Petcare integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_import(self, import_info):
        """Set the config entry up from yaml."""
        return await self.async_step_user(import_info)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                email = user_input[CONF_USERNAME]
                password = user_input[CONF_PASSWORD].replace(" ", "")
                await validate_input(self.hass, email, password)
                unique_id = email
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=unique_id,
                    data={CONF_USERNAME: email, CONF_PASSWORD: password},
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate host is already configured."""
