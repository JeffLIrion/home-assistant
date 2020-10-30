"""
Simple platform to control **SOME** Tuya switch devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tuya/
"""
from threading import Lock
from time import time

import pytuya
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_SWITCHES,
)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ["pytuya==7.0"]

CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"

DEFAULT_ID = "1"

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
        vol.Optional(CONF_SWITCHES, default={}): vol.Schema({cv.slug: SWITCH_SCHEMA}),
    }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    devices = config.get(CONF_SWITCHES)
    switches = []

    outlet_device = TuyaCache(
        pytuya.OutletDevice(
            config.get(CONF_DEVICE_ID),
            config.get(CONF_HOST),
            config.get(CONF_LOCAL_KEY),
        )
    )

    for object_id, device_config in devices.items():
        switches.append(
            TuyaDevice(
                outlet_device,
                device_config.get(CONF_FRIENDLY_NAME, object_id),
                device_config.get(CONF_ID),
            )
        )

    name = config.get(CONF_NAME)
    if name:
        switches.append(TuyaDevice(outlet_device, name, config.get(CONF_ID)))

    add_devices(switches)


class TuyaCache:
    """Cache wrapper for `pytuya.OutletDevice`."""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    def __get_status(self):
        for i in range(3):
            try:
                return self._device.status()
            except Exception as exc:  # pylint: disable=broad-except
                if i + 1 == 3:
                    raise exc

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for i in range(3):
            try:
                return self._device.set_status(state, switchid)
            except Exception as exc:  # pylint: disable=broad-except
                if i + 1 == 3:
                    raise exc

    def status(self):
        """Get state of Tuya switch and cache the results."""
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 20:
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()


class TuyaDevice(SwitchEntity):
    """Representation of a Tuya switch."""

    def __init__(self, device, name, switchid):
        """Initialize the Tuya switch."""
        self._device = device
        self._name = name
        self._state = False
        self._switchid = switchid

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        self._device.set_status(True, self._switchid)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_status(False, self._switchid)

    def update(self):
        """Get state of Tuya switch."""
        status = self._device.status()
        self._state = status["dps"][self._switchid]
