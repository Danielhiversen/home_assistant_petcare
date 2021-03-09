"""Support for Sure Petcare cat/pet flaps."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .petcare import Petcare

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass, entry):
    """Set up the Petcare."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "lock"))
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "sensor"
    )
    if not unload_ok:
        return False
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "lock"
    )
    return unload_ok


async def async_setup(hass, config) -> bool:
    """Initialize the Sure Petcare component."""
    conf = config[DOMAIN]

    # sure petcare api connection
    petcare_data_handler = Petcare(
        conf[CONF_USERNAME],
        conf[CONF_PASSWORD],
        async_get_clientsession(hass),
    )

    hass.data[DOMAIN] = petcare_data_handler

    if not await petcare_data_handler.login():
        return False

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )

    return True
