import datetime
from enum import IntEnum
from http import HTTPStatus

import async_timeout
from uuid import uuid1

RATE_LIMIT_SECONDS = 180

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
PET_RESOURCE: str = "{BASE_RESOURCE}/pet?with%5B%5D=photo&with%5B%5D=breed&with%5B%5D=conditions&with%5B%5D=tag&with%5B%5D=food_type&with%5B%5D=species&with%5B%5D=position&with%5B%5D=status"
POSITION_RESOURCE: str = "{BASE_RESOURCE}/pet/{pet_id}/position"


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
    DEVICES = (
        13  # artificial ID, Pet Flap + Cat Flap + Feeder = 3 + 6 + 4 = 13  ¯\_(ツ)_/¯
    )


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
        self._timeout = 15
        self._prev_data_request = datetime.datetime.utcnow() - datetime.timedelta(
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
        authentication_data = dict(
            email_address=self.email, password=self.password, device_id=self._device_id
        )
        with async_timeout.timeout(self._timeout):
            response = await self.websession.post(
                url=AUTH_RESOURCE,
                data=authentication_data,
                headers=self._generate_headers(),
            )
        if response.status != HTTPStatus.OK:
            return False

        json_data = await response.json()
        self._auth_token = json_data.get("data", {}).get("token")
        return True

    async def fetch(
        self,
        method: str,
        resource: str,
        data=None,
        retry=3,
    ):
        with async_timeout.timeout(self._timeout):
            headers = self._generate_headers()

            if resource in self._etags:
                headers[ETAG] = str(self._etags.get(resource))

            await self.websession.options(resource, headers=headers)
            response = await self.websession.request(
                method, resource, headers=headers, data=data
            )

        if response.status == HTTPStatus.OK or response.status == HTTPStatus.CREATED:
            json_data = await response.json()
            if ETAG in response.headers:
                self._etags[resource] = response.headers[ETAG].strip('"')
            return json_data
        elif response.status == HTTPStatus.UNAUTHORIZED:
            self._auth_token = None
            if retry > 0:
                if await self.login():
                    return await self.fetch(method, resource, data, retry - 1)
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
        if (
            not force_update
            and datetime.datetime.utcnow() - self._prev_data_request
            < datetime.timedelta(seconds=RATE_LIMIT_SECONDS)
        ):
            return self._data
        self._data = await self.fetch(method="GET", resource=MESTART_RESOURCE)
        self._hubs = [
            {
                "id": val.get("id"),
                "household_id": val.get("household_id"),
                "name": val.get("name"),
                "state": val.get("status").get("led_mode"),
                "attributes": {
                    "online": val.get("status").get("online"),
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
                "attributes": {
                    "voltage": val.get("status").get("battery"),
                    "voltage_per_battery": val.get("status").get("battery") / 4,
                    "battery": min(
                        int(
                            (
                                val.get("status").get("battery") / 4
                                - SURE_BATT_VOLTAGE_LOW
                            )
                            / SURE_BATT_VOLTAGE_DIFF
                            * 100
                        ),
                        100,
                    ),
                    "online": val.get("status").get("online"),
                    "signal": val.get("status").get("signal").get("device_rssi"),
                },
            }
            for val in self._data["data"]["devices"]
            if val.get("product_id") == EntityType.CAT_FLAP
        ]
        self._pets = [
            {
                "id": val.get("id"),
                "household_id": val.get("household_id"),
                "name": val.get("name"),
                "state": Location(val.get("position").get("where")).name,
                "attributes": {
                    "since": val.get("status").get("since"),
                },
            }
            for val in self._data["data"]["pets"]
        ]
        return self._data

    #
    # async def get_timeline(self, force_update=False):
    #     if (not force_update
    #             and datetime.datetime.utcnow() - self._prev_timeline_request
    #             < datetime.timedelta(seconds=RATE_LIMIT_SECONDS)
    #     ):
    #         return
    #
    #     data = await self.fetch(method="GET", resource=TIMELINE_RESOURCE)
    #     for val in data.get("data"):
    #         if val.get('type') == Event.MOVE:
    #             _id = val.get('tags')[0].get('id')
    #             if _id in self._pets:
    #                 updated_at = parse(val.get('devices')[0]['updated_at'])
    #                 updated_at_current = parse(self._pets[_id]['data']['updated_at'])
    #                 if updated_at < updated_at_current:
    #                     continue
    #             self._pets[_id] = {'data': val.get('devices')[0]}
    #         elif val.get('type') == Event.LOCK_ST:
    #             _id = val.get('devices')[0].get('id')
    #             if _id in self._flaps:
    #                 updated_at = parse(val.get('devices')[0]['updated_at'])
    #                 updated_at_current = parse(self._flaps[_id]['data']['updated_at'])
    #                 if updated_at < updated_at_current:
    #                     continue
    #             self._flaps[_id] = {'state': LockState(json.loads(val.get('data', {})).get('mode')),
    #                                 'data': val.get('devices')[0]}
    #     self._prev_timeline_request = datetime.datetime.utcnow()
    #     print("pets")
    #     print(self._pets)
    #     print("flaps")
    #     print(self._flaps)
    #     print("here")

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
