import asyncio
import datetime
import json
import logging
from enum import IntEnum
from http import HTTPStatus
from uuid import uuid1

import async_timeout

RATE_LIMIT_SECONDS = 300

ACCEPT = "Accept"
ACCEPT_ENCODING = "Accept-Encoding"
ACCEPT_LANGUAGE = "Accept-Language"
AUTHORIZATION = "Authorization"
CONNECTION = "Connection"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT_PLAIN = "text/plain"
ETAG = "Etag"
HOST = "Host"
HTTP_HEADER_X_REQUESTED_WITH = "X-Requested-With"
ORIGIN = "Origin"
REFERER = "Referer"
USER_AGENT = "User-Agent"
SURE_BATT_VOLTAGE_FULL = 1.6  # voltage
SURE_BATT_VOLTAGE_LOW = 1.25  # voltage
SURE_BATT_VOLTAGE_DIFF = SURE_BATT_VOLTAGE_FULL - SURE_BATT_VOLTAGE_LOW

BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{flap_id}/control"
PET_RESOURCE: str = (
    "{BASE_RESOURCE}/pet?with%5B%5D=photo&with%5B%5D=breed&"
    "with%5B%5D=conditions&with%5B%5D=tag&with%5B%5D=food_type"
    "&with%5B%5D=species&with%5B%5D=position&with%5B%5D=status"
)
POSITION_RESOURCE: str = "{BASE_RESOURCE}/pet/{pet_id}/position"

_LOGGER = logging.getLogger(__name__)


class SureEnum(IntEnum):
    """Sure base enum."""

    def __str__(self) -> str:
        return self.name.title()


class EntityType(SureEnum):
    """Sure Entity Types."""

    PET = 0  # artificial ID, not used by the Sure Petcare API
    HUB = 1  # Hub
    REPEATER = 2  # Repeater
    PET_FLAP = 3  # Pet Door Connect
    FEEDER = 4  # Microchip Pet Feeder Connect
    PROGRAMMER = 5  # Programmer
    CAT_FLAP = 6  # Cat Flap Connect


class LockState(SureEnum):
    """Sure Petcare API State IDs."""

    UNLOCKED = 0
    LOCKED_IN = 1
    LOCKED_OUT = 2
    LOCKED_ALL = 3
    CURFEW = 4
    CURFEW_LOCKED = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN = -3


class Location(SureEnum):
    """Sure Locations."""

    INSIDE = 1
    OUTSIDE = 2
    UNKNOWN = -1


class Event(SureEnum):
    """Sure Petcare API Events."""

    MOVE = 0
    MOVE_UID = 7
    BAT_WARN = 1
    LOCK_ST = 6
    USR_IFO = 12
    USR_NEW = 17
    CURFEW = 20


class Petcare:
    """Define a Petcare object."""

    def __init__(self, email, password, websession) -> None:
        """Initialize the Sure Petcare object."""
        self.email = email
        self.password = password
        self.websession = websession

        self._device_id = str(uuid1())
        self._timeout = 35
        self._prev_data_request = datetime.datetime.utcnow() - datetime.timedelta(
            hours=10
        )
        self._prev_login_request = datetime.datetime.utcnow() - datetime.timedelta(
            hours=10
        )
        self._prev_timeline_request = datetime.datetime.utcnow() - datetime.timedelta(
            hours=10
        )

        self._auth_token = None
        self._etags = {}

        self._data = {}
        self._hubs = {}
        self._flaps = {}
        self._pets = {}

        self._fetch_lock = asyncio.Lock()
        self._data_lock = asyncio.Lock()
        self._timeline_lock = asyncio.Lock()
        self._login_lock = asyncio.Lock()

    def _generate_headers(self):
        """Build a HTTP header accepted by the API"""
        return {
            HOST: "app.api.surehub.io",
            CONNECTION: "keep-alive",
            ACCEPT: f"{CONTENT_TYPE_JSON}, {CONTENT_TYPE_TEXT_PLAIN}, */*",
            ORIGIN: "https://surepetcare.io",
            REFERER: "https://surepetcare.io",
            ACCEPT_ENCODING: "gzip, deflate",
            ACCEPT_LANGUAGE: "en-US,en-GB;q=0.9",
            HTTP_HEADER_X_REQUESTED_WITH: "com.sureflap.surepetcare",
            AUTHORIZATION: f"Bearer {self._auth_token}",
            "X-Device-Id": self._device_id,
        }

    async def login(self):
        async with self._login_lock:
            if (
                self._auth_token
                and datetime.datetime.utcnow() - self._prev_login_request
                < datetime.timedelta(seconds=RATE_LIMIT_SECONDS)
            ):
                return self._data

            authentication_data = dict(
                email_address=self.email,
                password=self.password,
                device_id=self._device_id,
            )
            with async_timeout.timeout(self._timeout):
                response = await self.websession.post(
                    url=AUTH_RESOURCE,
                    data=authentication_data,
                    headers=self._generate_headers(),
                )
            if response.status != HTTPStatus.OK:
                self._auth_token = None
                return False

            json_data = await response.json()
            self._auth_token = json_data.get("data", {}).get("token")
            self._prev_login_request = datetime.datetime.utcnow()
            return True

    async def fetch(
        self,
        method: str,
        resource: str,
        data=None,
        retry=3,
    ):
        try:
            headers = self._generate_headers()

            if resource in self._etags:
                headers[ETAG] = str(self._etags.get(resource))

            async with self._fetch_lock:
                with async_timeout.timeout(self._timeout):
                    await self.websession.options(resource, headers=headers)
                    response = await self.websession.request(
                        method, resource, headers=headers, data=data
                    )

            if (
                response.status == HTTPStatus.OK
                or response.status == HTTPStatus.CREATED
            ):
                json_data = await response.json()
                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')
                return json_data
            elif response.status == HTTPStatus.UNAUTHORIZED:
                self._auth_token = None
                if retry > 0:
                    if await self.login():
                        return await self.fetch(method, resource, data, retry - 1)
        except asyncio.TimeoutError:
            if retry > 0:
                await asyncio.sleep(10)
                return await self.fetch(method, resource, data, retry - 1)
            raise
        return None

    def get_flaps(self):
        return self._flaps

    def get_hubs(self):
        return self._hubs

    def get_pets(self):
        return self._pets

    def get_device(self, device_id):
        for val in self._hubs:
            if val.get("id") == device_id:
                return val
        for val in self._flaps:
            if val.get("id") == device_id:
                return val
        for val in self._pets:
            if val.get("id") == device_id:
                return val
        return None

    async def get_device_data(self, force_update=False):
        async with self._data_lock:
            if (
                not force_update
                and datetime.datetime.utcnow() - self._prev_data_request
                < datetime.timedelta(seconds=RATE_LIMIT_SECONDS)
            ):
                return self._data
            self._data = await self.fetch(method="GET", resource=MESTART_RESOURCE)
            _LOGGER.debug("data %s", self._data)
            self._prev_data_request = datetime.datetime.utcnow()
            self._hubs = [
                {
                    "id": val.get("id"),
                    "household_id": val.get("household_id"),
                    "name": val.get("name"),
                    "state": val.get("status").get("led_mode"),
                    "available": val.get("status").get("online"),
                    "attributes": {
                        "firmware": val.get("status")
                        .get("version")
                        .get("device")
                        .get("firmware"),
                    },
                }
                for val in self._data["data"]["devices"]
                if val.get("product_id") == EntityType.HUB
            ]
            self._flaps = [
                {
                    "id": val.get("id"),
                    "household_id": val.get("household_id"),
                    "name": val.get("name"),
                    "state": LockState(val.get("control").get("locking")).name,
                    "available": val.get("status").get("online"),
                    "attributes": {
                        "lock": LockState(val.get("control").get("locking")).name,
                        "voltage": val.get("status").get("battery"),
                        "voltage_per_battery": val.get("status").get("battery", 0) / 4,
                        "battery": min(
                            int(
                                (
                                    val.get("status").get("battery", 0) / 4
                                    - SURE_BATT_VOLTAGE_LOW
                                )
                                / SURE_BATT_VOLTAGE_DIFF
                                * 100
                            ),
                            100,
                        ),
                        "signal": val.get("status").get("signal").get("device_rssi"),
                        "control": str(val.get("control", {}).get("curfew", ""))
                    },
                }
                for val in self._data["data"]["devices"]
                if val.get("product_id") in [EntityType.CAT_FLAP, EntityType.PET_FLAP]
            ]

            self._pets = [
                {
                    "id": val.get("id"),
                    "tag_id": val.get("tag_id"),
                    "household_id": val.get("household_id"),
                    "name": val.get("name"),
                    "state": Location(val.get("position").get("where")).name,
                    "available": val.get("position").get("where") is not None,
                    "attributes": {
                        "since": val.get("position").get("since"),
                    },
                }
                for val in self._data["data"]["pets"]
            ]

            await self.get_timeline()

            return self._data

    async def get_timeline(self, force_update=False):
        async with self._timeline_lock:
            if (
                not force_update
                and datetime.datetime.utcnow() - self._prev_timeline_request
                < datetime.timedelta(seconds=RATE_LIMIT_SECONDS)
            ):
                return
            household_ids = []
            for device in self._data.get("data").get("devices"):
                household_id = device.get("household_id")
                if household_id in household_ids:
                    continue
                household_ids.append(household_id)
                data = await self.fetch(
                    method="GET",
                    resource=f"{TIMELINE_RESOURCE}/household/{household_id}/",
                )
                _LOGGER.debug("tl data %s", data)
                for val in data.get("data"):
                    for pet in self._pets:
                        try:
                            if (
                                val.get("type") == Event.MOVE
                                and val.get("devices") is not None
                                and val.get("tags")[0].get("id") == pet["tag_id"]
                                and val.get("movements") is not None
                            ):
                                if (
                                    val.get("movements")[0].get("direction") == 0
                                    and pet["attributes"].get("looked_through") is None
                                ):
                                    pet["attributes"]["looked_through"] = val[
                                        "created_at"
                                    ]
                                elif (
                                    val.get("movements")[0].get("direction") == 1
                                    and pet["attributes"].get("entered") is None
                                ):
                                    pet["attributes"]["entered"] = val["created_at"]
                                elif (
                                    val.get("movements")[0].get("direction") == 2
                                    and pet["attributes"].get("left") is None
                                ):
                                    pet["attributes"]["left"] = val["created_at"]
                        except KeyError:
                            continue

                    for flap in self._flaps:
                        # if val.get("devices")[0]["id"] == flap["id"]:
                        # if val.get("devices")[0]["id"] == flap["id"]:
                        #     print(val)
                        try:
                            if (
                                val.get("type") == Event.LOCK_ST
                                and flap["attributes"].get("event") is None
                                and val.get("devices")[0]["id"] == flap["id"]
                            ):
                                flap["attributes"]["event"] = (
                                    f'{LockState(json.loads(val["data"])["mode"]).name.lower()} '
                                    f'by {val["users"][0]["name"]} '
                                    f'at {val["updated_at"]}'
                                )
                        except KeyError:
                            continue

            self._prev_timeline_request = datetime.datetime.utcnow()

    async def get_pet(self, pet_id: int):
        """Retrieve the pet data/state."""
        response = await self.fetch(
            method="GET",
            resource=PET_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, pet_id=pet_id),
        )
        if response:
            return response.get("data")
        return None

    async def locking(self, flap_id: int, mode: LockState):
        """Retrieve the flap data/state."""
        resource = CONTROL_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, flap_id=flap_id)
        data = {"locking": int(mode.value)}

        if (
            response := await self.fetch(method="PUT", resource=resource, data=data)
        ) and (response_data := response.get("data")):

            desired_state = data.get("locking")
            state = response_data.get("locking")

            # check if the state is correctly updated
            if state == desired_state:
                return response
        return None
