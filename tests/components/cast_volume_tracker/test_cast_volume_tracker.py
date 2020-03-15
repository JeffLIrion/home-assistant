"""Tests for the cast_volume_tracker component."""

from homeassistant.components.cast_mock.media_player import (
    CAST_MOCK_DOMAIN,
    CONF_PARENTS,
)
from homeassistant.components.cast_volume_tracker import CONF_MUTE_WHEN_OFF
from homeassistant.components.media_player.const import DOMAIN
from homeassistant.const import CONF_NAME, CONF_PLATFORM, STATE_IDLE, STATE_OFF
from homeassistant.setup import async_setup_component

BEDROOM_SPEAKERS_CONFIG = {
    DOMAIN: {
        CONF_PLATFORM: CAST_MOCK_DOMAIN,
        CONF_NAME: "Bedroom Speakers",
        CONF_PARENTS: ["media_player.all_my_speakers"],
        CONF_MUTE_WHEN_OFF: True,
    }
}

COMPUTER_SPEAKERS_CONFIG = {
    DOMAIN: {
        CONF_PLATFORM: CAST_MOCK_DOMAIN,
        CONF_NAME: "Computer Speakers",
        CONF_PARENTS: [
            "media_player.all_my_speakers",
            "media_player.kitchen_speakers",
            "media_player.main_speakers",
        ],
    }
}


async def _setup_one(hass, config):
    """Set up one media player."""
    assert await async_setup_component(hass, DOMAIN, config)
    name = "media_player." + config[CONF_NAME].lower().replace(" ", "_")
    state = hass.states.get(name)
    assert state is not None
    assert state.state == STATE_OFF
    assert state.state != STATE_IDLE


async def _setup_all(hass):
    """Set up all the media players for the tests."""
    await _setup_one(hass, BEDROOM_SPEAKERS_CONFIG)
    await _setup_one(hass, COMPUTER_SPEAKERS_CONFIG)


async def test_setup(hass):
    """Test that a `cast_mock` media player can be created."""
    assert await async_setup_component(hass, DOMAIN, BEDROOM_SPEAKERS_CONFIG)

    state = hass.states.get("media_player.bedroom_speakers")
    assert state is not None
    assert state.state == STATE_OFF
