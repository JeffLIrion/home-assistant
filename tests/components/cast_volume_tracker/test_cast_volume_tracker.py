"""Tests for the cast_volume_tracker component."""

from homeassistant.components.cast_mock.media_player import (
    CAST_MOCK_DOMAIN,
    CONF_PARENTS,
)
from homeassistant.components.cast_volume_tracker import DOMAIN as CVT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN
from homeassistant.const import CONF_NAME, CONF_PLATFORM, STATE_IDLE, STATE_OFF
from homeassistant.setup import async_setup_component

CAST_MOCK_CONFIG = {
    DOMAIN: [
        {
            CONF_PLATFORM: CAST_MOCK_DOMAIN,
            CONF_NAME: "Bedroom Speakers",
            CONF_PARENTS: ["media_player.all_my_speakers"],
        },
        {
            CONF_PLATFORM: CAST_MOCK_DOMAIN,
            CONF_NAME: "Computer Speakers",
            CONF_PARENTS: [
                "media_player.all_my_speakers",
                "media_player.kitchen_speakers",
                "media_player.main_speakers",
            ],
        },
    ]
}

CAST_VOLUME_TRACKER_CONFIG = {
    CVT_DOMAIN: {
        "bedroom_speakers": {
            CONF_NAME: "Bedroom Speakers",
            CONF_PARENTS: ["media_player.all_my_speakers"],
        },
        "computer_speakers": {
            CONF_NAME: "Computer Speakers",
            CONF_PARENTS: [
                "media_player.all_my_speakers",
                "media_player.kitchen_speakers",
                "media_player.main_speakers",
            ],
        },
    }
}


async def test_setup(hass):
    """Test that a `cast_mock` media player can be created."""
    assert await async_setup_component(hass, DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    for entity_id in [
        "media_player.bedroom_speakers",
        "media_player.computer_speakers",
    ]:
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_OFF
        assert state.state != STATE_IDLE

        cvt_entity_id = entity_id.replace("media_player", "cast_volume_tracker")
        state = hass.states.get(cvt_entity_id)
        assert state is not None
