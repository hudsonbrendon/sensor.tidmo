import json
import logging
import string
from collections import defaultdict
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
import pytz
import requests
import voluptuous as vol
from dateutil.relativedelta import relativedelta
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_NAME,
    CONF_RESOURCES,
    STATE_UNKNOWN,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:broom"

SCAN_INTERVAL = timedelta(minutes=60)

ATTRIBUTION = "Data provided by tidmo api"

DOMAIN = "tidmo"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

LOGIN_URL = "https://tidmo.com.br/api/login/"
BASE_URL = "https://api.tidmo.com.br/api/v1/users/self/requests/"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the currency sensor"""

    email = config["email"]
    password = config["password"]
    add_entities(
        [TidmoSensor(hass, email, password, SCAN_INTERVAL)],
        True,
    )


class TidmoSensor(Entity):
    def __init__(self, hass, email, password, interval):
        """Inizialize sensor"""
        self._state = STATE_UNKNOWN
        self._hass = hass
        self._interval = interval
        self._name = "Tidmo"
        self._email = email
        self._password = password
        self._requests = []

    @property
    def name(self):
        """Return the name sensor"""
        return self._name

    @property
    def icon(self):
        """Return the default icon"""
        return ICON

    @property
    def state(self):
        """Return the state of the sensor"""
        return len(self._requests)

    @property
    def device_state_attributes(self):
        """Attributes."""
        return {"faxinas": self._requests}

    def cleaning_today(self, date):
        if date == datetime.now().strftime("%Y-%m-%d"):
            return "Sim"
        return "Não"

    def cleaning_next_day(self, date):
        if date == datetime.now() + timedelta(days=1):
            return "Sim"
        return "Não"

    def update(self):
        """Get the latest update fron the api"""
        login = requests.post(LOGIN_URL, data={"email": self._email, "password": self._password})

        if login.ok:
            token = login.cookies.get("authorization")
            response = requests.get(BASE_URL, headers={"Authorization": "Bearer {}".format(token)})
            self._requests = []
            if response.ok:
                for request in response.json().get("results"):
                    self._requests.append(
                        dict(
                            tipo=request.get("productType").get("name"),
                            comodos=request.get("quantity", 0) + 2,
                            data=request.get("date"),
                            inicio=request.get("startTime"),
                            fim=request.get("endTime"),
                            opcionais=[optional.get("name") for optional in request.get("optionals")],
                            local=request.get("location").get("description"),
                            embaixadora=request.get("ambassadorsResponse")[0].get("ambassador").get("nickname"),
                            nota=request.get("ambassadorsResponse")[0].get("ambassador").get("rating"),
                            foto=request.get("ambassadorsResponse")[0].get("ambassador").get("avatarUrl"),
                            preco=request.get("totalPrice"),
                            tem_faxina_hoje=self.cleaning_today(request.get("date")),
                            tem_faxina_amanha=self.cleaning_next_day(request.get("date")),
                        )
                    )
            else:
                _LOGGER.error(f"Cannot perform the request: {response.content}")
        else:
            _LOGGER.error(f"Login request error: {login.content}")

