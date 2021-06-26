"""Support for Sure PetCare Flaps/Pets sensors."""
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .petcare import Petcare, Location

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Petcare."""
    await _setup(hass, async_add_entities)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Petcare with config flow."""
    await _setup(hass, async_add_entities)


async def _setup(hass, async_add_entities):
    petcare_data_handler = hass.data[DOMAIN]

    await petcare_data_handler.login()
    await petcare_data_handler.get_device_data()

    devices = []
    pet_names = []
    for pet in petcare_data_handler.get_pets():
        devices.append(SurePetcareSensor(pet, petcare_data_handler))
        pet_names.append(pet["name"].capitalize())
    for hub in petcare_data_handler.get_hubs():
        devices.append(SurePetcareSensor(hub, petcare_data_handler))
    for flap in petcare_data_handler.get_flaps():
        devices.append(SurePetcareSensor(flap, petcare_data_handler))
    async_add_entities(devices)

    set_pet_location_schema = vol.Schema(
        {
            vol.Optional("pet_name"): vol.In(pet_names),
            vol.Required("location"): vol.In(["inside", "outside"]),
        }
    )

    _LOGGER.error("petcare names %s ", pet_names)

    async def service_set_pet_location_handle(service):
        """Handle for services."""
        pet_name = service.data.get("pet_name")
        location = service.data.get("location")
        _LOGGER.error("petcare %s %s", pet_name, location)
        for _dev in devices:
            if pet_name.lower() == _dev.name.lower():
                enum_location = (
                    Location.INSIDE if location == "inside" else Location.OUTSIDE
                )
                res = await petcare_data_handler.set_pet_location(
                    _dev.dev["id"], enum_location
                )
                _LOGGER.error(
                    "petcare %s %s %s %s",
                    _dev.entity_id,
                    _dev.dev["id"],
                    enum_location,
                    res,
                )
                return

    hass.services.async_register(
        DOMAIN,
        "set_pet_location",
        service_set_pet_location_handle,
        schema=set_pet_location_schema,
    )


class SurePetcareSensor(Entity):
    """A binary sensor implementation for Sure Petcare Entities."""

    def __init__(self, dev, petcare_data_handler):
        """Initialize a Sure Petcare sensor."""

        self.dev = dev
        self.petcare_data_handler: Petcare = petcare_data_handler

        self._name = self.dev["name"].capitalize()

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"{self.dev['household_id']}-{self.dev['id']}"

    @property
    def available(self) -> bool:
        """Return true if entity is available."""
        return self.dev["available"]

    async def async_update(self) -> None:
        """Get the latest data and update the state."""
        await self.petcare_data_handler.get_device_data()
        self.dev = self.petcare_data_handler.get_device(self.dev["id"])

    @property
    def state(self) -> Optional[int]:
        """Return battery level in percent."""
        return self.dev["state"]

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return the state attributes of the device."""
        return self.dev["attributes"]
