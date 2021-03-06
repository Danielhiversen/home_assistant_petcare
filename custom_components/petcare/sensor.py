"""Support for Sure PetCare Flaps/Pets sensors."""
import logging
from typing import Any, Dict, Optional

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD


from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .petcare import Petcare
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Petcare."""
    print("aaa")
    await _setup(hass, config[CONF_USERNAME], config[CONF_PASSWORD], async_add_entities)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Petcare with config flow."""
    print("bbbbaaa")
    await _setup(
        hass, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], async_add_entities
    )


async def _setup(hass, email, password, async_add_entities):
    petcare_data_handler = Petcare(
        email, password, websession=async_get_clientsession(hass)
    )

    await petcare_data_handler.login()
    await petcare_data_handler.get_device_data()

    dev = []
    for pet in petcare_data_handler.get_pets():
        print("pet", pet)
        dev.append(SurePetcareSensor(pet, petcare_data_handler))
    for hub in petcare_data_handler.get_hubs():
        print("hub", hub)
        dev.append(SurePetcareSensor(hub, petcare_data_handler))
    for flap in petcare_data_handler.get_flaps():
        print("flap", flap)
        dev.append(SurePetcareSensor(flap, petcare_data_handler))
    async_add_entities(dev)


class SurePetcareSensor(Entity):
    """A binary sensor implementation for Sure Petcare Entities."""

    def __init__(self, dev, petcare_data_handler):
        """Initialize a Sure Petcare sensor."""

        self._dev = dev
        self.petcare_data_handler: Petcare = petcare_data_handler

        self._name = self._dev['name'].capitalize()

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"{self._dev['household_id']}-{self._dev['id']}"

    @property
    def available(self) -> bool:
        """Return true if entity is available."""
        return bool(self.state)

    async def async_update(self) -> None:
        """Get the latest data and update the state."""
        await self.petcare_data_handler.get_device_data()
        self._dev = self.petcare_data_handler.get_device(self._dev['id'])

    @property
    def state(self) -> Optional[int]:
        """Return battery level in percent."""
        print("state", self._dev)
        return self._dev['state']

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return the state attributes of the device."""
        return self._dev['attributes']
