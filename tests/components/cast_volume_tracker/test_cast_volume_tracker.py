"""Tests for the cast_volume_tracker component."""

import os

from homeassistant.components.cast_volume_tracker import DOMAIN as CVT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MP_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_IDLE,
    STATE_OFF,
)
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml.loader import load_yaml

PWD = os.path.dirname(__file__)

MEDIA_PLAYERS = [
    "all_my_speakers",
    "bedroom_mini",
    "bedroom_speakers",
    "computer_speakers",
    "kitchen_home",
    "kitchen_speakers",
    "living_room_display",
    "living_room_speakers",
    "main_speakers",
]

CAST_MOCK_CONFIG = {MP_DOMAIN: load_yaml(PWD + "/media_players.yaml")}
CAST_VOLUME_TRACKER_CONFIG = {CVT_DOMAIN: load_yaml(PWD + "/cast_volume_trackers.yaml")}


async def test_setup(hass):
    """Test that a `cast_mock` media player can be created."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    for media_player in MEDIA_PLAYERS:
        mp_entity_id = "media_player.{}".format(media_player)
        state = hass.states.get(mp_entity_id)
        assert state is not None
        assert state.state == STATE_OFF
        assert state.state != STATE_IDLE

        cvt_entity_id = "cast_volume_tracker.{}".format(media_player)
        state = hass.states.get(cvt_entity_id)
        assert state is not None


async def test_cast_mock_turn_on_off_individual(hass):
    """Test that a `cast_mock` individual (i.e., not a group) media player can be turned on and off."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    # assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    entity_id = "media_player.bedroom_mini"

    # Make sure the media player is off
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )

    # Make sure the media player is idle
    state = hass.states.get(entity_id)
    assert state is not None
    # assert state.state == STATE_IDLE

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )

    # Make sure the media player is off
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF
