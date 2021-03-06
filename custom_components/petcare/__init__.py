"""Support for Sure Petcare cat/pet flaps."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .petcare import Petcare, LockState
from .const import (
    ATTR_FLAP_ID,
    ATTR_LOCK_STATE,
    DOMAIN,
    SERVICE_SET_LOCK_STATE,
)

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
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "sensor"
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

    if not await petcare_data_handler.login():
        return False

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )

    print("pet")

    async def handle_set_lock_state(call):
        """Call when setting the lock state."""
        await petcare_data_handler.locking(call.data[ATTR_FLAP_ID], call.data[ATTR_LOCK_STATE])
        await petcare_data_handler.get_device_data(force_update=True)

    lock_state_service_schema = vol.Schema(
        {
            vol.Required(ATTR_FLAP_ID): vol.All(
                cv.positive_int, vol.In(petcare_data_handler.get_flaps().keys())
            ),
            vol.Required(ATTR_LOCK_STATE): vol.All(
                cv.string,
                vol.Lower,
                vol.In(
                    [
                        LockState.UNLOCKED.name.lower(),
                        LockState.LOCKED_IN.name.lower(),
                        LockState.LOCKED_OUT.name.lower(),
                        LockState.LOCKED_ALL.name.lower(),
                    ]
                ),
            ),
        }
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LOCK_STATE,
        handle_set_lock_state,
        schema=lock_state_service_schema,
    )

    return True
