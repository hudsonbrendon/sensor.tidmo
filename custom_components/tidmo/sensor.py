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

CONF_TOKEN = "token"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_TOKEN): cv.string,
    }
)

LOGIN_URL = "https://tidmo.com.br/api/login/"
BASE_URL = "https://api.tidmo.com.br/api/v1/users/self/requests/"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the currency sensor"""

    token = config["token"]

    add_entities(
        [TidmoSensor(hass, token, SCAN_INTERVAL)],
        True,
    )


class TidmoSensor(Entity):
    def __init__(self, hass, token, interval):
        """Inizialize sensor"""
        self._state = STATE_UNKNOWN
        self._hass = hass
        self._interval = interval
        self._name = "Tidmo"
        self._token = token
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

    def update(self):
        """Get the latest update fron the api"""
        response = requests.get(BASE_URL, headers={"Authorization": "Bearer {}".format(self._token)})
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
                    )
                )
        else:
            _LOGGER.error("Cannot perform the request")

