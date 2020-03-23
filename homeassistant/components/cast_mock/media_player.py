"""A mock media player for testing `cast_volume_tracker`."""
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
    cast_mock = CastMock(
        config[CONF_NAME], config[CONF_PARENTS], config[CONF_MEMBERS], hass
    )
    add_entities([cast_mock])
    object_id = config[CONF_NAME].lower().replace(" ", "_")
    hass.data[CAST_MOCK_DOMAIN][object_id] = cast_mock


class CastMock(MediaPlayerDevice):
    """A mock cast media player."""

    def __init__(self, name, parents, members, hass):
        """Initialize the mock cast media player."""
        self._hass = hass
        self._name = name
        self._parents = parents
        self._members = members
        self.state_ = STATE_OFF
        self.volume_level_ = 0.0
        self.is_volume_muted_ = False
        self.entity_id_ = "media_player.{}".format(name.lower().replace(" ", "_"))

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self.is_volume_muted_

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
        return self.state_

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_CAST_MOCK

    @property
    def volume_level(self):
        """Return the volume level."""
        return self.volume_level_

    async def async_turn_on(self):
        """Turn on the device."""
        self.state_ = STATE_IDLE
        self.async_write_ha_state()

        # If this is a group, then turn on its members and compute its volume level
        members = [
            self._hass.data[CAST_MOCK_DOMAIN][member] for member in self._members
        ]
        if members:
            self.volume_level_ = sum(
                (member.volume_level_ for member in members)
            ) / len(members)
            off_entity_ids = [
                member.entity_id_ for member in members if member.state_ == STATE_OFF
            ]
            for entity_id in off_entity_ids:
                self._hass.states.async_set(entity_id, STATE_IDLE)
                # await self._hass.async_block_till_done()

    async def async_turn_off(self):
        """Turn off the device."""
        self.state_ = STATE_OFF
        self.async_write_ha_state()

        # If this is a group, then turn off its members
        members = [
            self._hass.data[CAST_MOCK_DOMAIN][member] for member in self._members
        ]
        if members:
            on_entity_ids = [
                member.entity_id_ for member in members if member.state_ != STATE_OFF
            ]
            for entity_id in on_entity_ids:
                self._hass.states.async_set(entity_id, STATE_IDLE)
                # await self._hass.async_block_till_done()

    async def async_set_volume_level(self, volume):
        """Set the volume level."""
        # old_volume_level = self.volume_level_
        self.volume_level_ = volume

        # If this is a group, then adjust the volume of its members
        members = [
            self._hass.data[CAST_MOCK_DOMAIN][member] for member in self._members
        ]
        for member in members:
            # TODO: calculate the volume correctly and set it
            self._hass.states.async_set(member.entity_id_, STATE_IDLE)

        parents = [
            self._hass.data[CAST_MOCK_DOMAIN][parent] for parent in self._parents
        ]
        for parent in parents:
            if parent.state_ != STATE_OFF:
                # TODO: calculate the volume correctly and set it
                self._hass.states.async_set(parent.entity_id_, STATE_IDLE)
