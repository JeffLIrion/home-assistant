"""Tests for the cast_volume_tracker component."""

import os

from homeassistant.components.cast_volume_tracker import DOMAIN as CVT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN
from homeassistant.const import STATE_IDLE, STATE_OFF
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml.loader import load_yaml

PWD = os.path.dirname(__file__)

CAST_VOLUME_TRACKER_CONFIG = {CVT_DOMAIN: load_yaml(PWD + "/cast_volume_trackers.yaml")}
CAST_MOCK_CONFIG = {DOMAIN: load_yaml(PWD + "/media_players.yaml")}


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
