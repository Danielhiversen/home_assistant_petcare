"""Support for Sure PetCare Flaps/Pets sensors."""
import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.components.lock import LockEntity

from .const import DOMAIN
from .petcare import LockState, Petcare

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

    dev = []
    for flap in petcare_data_handler.get_flaps():
        for lock_state in [
            LockState.LOCKED_IN,
            LockState.LOCKED_OUT,
            LockState.LOCKED_ALL,
        ]:
            dev.append(SurePetcareLock(flap, petcare_data_handler, lock_state))
    async_add_entities(dev)


class SurePetcareLock(LockEntity):
    """A binary sensor implementation for Sure Petcare Entities."""

    def __init__(self, dev, petcare_data_handler, lock_state):
        """Initialize a Sure Petcare switch."""

        self._dev = dev
        self.petcare_data_handler: Petcare = petcare_data_handler
        self._lock_state = lock_state

        self._name = f"{lock_state}_{self._dev['name'].capitalize()}"

    async def handle_set_lock_state(self):
        """Call when setting the lock state."""
        await self.petcare_data_handler.locking(self._dev["id"], self._lock_state)
        await asyncio.sleep(20)
        await self.petcare_data_handler.get_device_data(force_update=True)

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"lock-{self._dev['household_id']}-{self._dev['id']}-{self._lock_state}"

    @property
    def available(self) -> bool:
        """Return true if entity is available."""
        return self._dev["available"]

    @property
    def is_locked(self):
        """Return true if the lock is locked."""
        return self._dev["state"] == self._lock_state.name

    async def async_lock(self, **kwargs):
        """Lock the lock."""
        if self.is_locked:
            return
        await self.petcare_data_handler.locking(self._dev["id"], self._lock_state)
        await self.petcare_data_handler.get_device_data(force_update=True)

    async def async_unlock(self, **kwargs):
        """Unlock the lock."""
        if not self.is_locked:
            return
        await self.petcare_data_handler.locking(self._dev["id"], LockState.UNLOCKED)
        await self.petcare_data_handler.get_device_data(force_update=True)

    async def async_update(self) -> None:
        """Get the latest data and update the state."""
        await self.petcare_data_handler.get_device_data()
        self._dev = self.petcare_data_handler.get_device(self._dev["id"])

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return the state attributes of the device."""
        return self._dev["attributes"]
