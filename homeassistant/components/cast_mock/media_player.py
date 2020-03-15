"""A mock media player for testing `cast_volume_tracker`."""
import asyncio  # noqa
import logging

import voluptuous as vol

from homeassistant.components.cast_volume_tracker import CONF_MEMBERS, CONF_PARENTS
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerDevice
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import CONF_NAME, STATE_IDLE, STATE_OFF
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CAST_MOCK_DOMAIN = "cast_mock"

SUPPORT_CAST_MOCK = (
    SUPPORT_TURN_OFF | SUPPORT_TURN_ON | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET
)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_PARENTS, default=list()): cv.ensure_list,
        vol.Optional(CONF_MEMBERS, default=list()): cv.ensure_list,
    },
    extra=vol.ALLOW_EXTRA,
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Cast Mock platform."""
    hass.data.setdefault(CAST_MOCK_DOMAIN, {})
    cast_mock = CastMock(config[CONF_NAME], config[CONF_PARENTS], config[CONF_MEMBERS])
    add_entities([cast_mock])
    hass.data[CAST_MOCK_DOMAIN][config[CONF_NAME]] = cast_mock


class CastMock(MediaPlayerDevice):
    """A mock cast media player."""

    def __init__(self, name, parents, members):
        """Initialize the mock cast media player."""
        self._name = name
        self._parents = parents
        self._members = members
        self._state = STATE_OFF
        self._volume_level = 0.0
        self._is_volume_muted = False

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._is_volume_muted

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def should_poll(self):
        """Device should be polled."""
        return False

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_CAST_MOCK

    @property
    def volume_level(self):
        """Return the volume level."""
        return self._volume_level

    async def async_turn_on(self):
        """Turn on the device."""
        self._state = STATE_IDLE

    async def async_turn_off(self):
        """Turn off the device."""
        self._state = STATE_OFF
