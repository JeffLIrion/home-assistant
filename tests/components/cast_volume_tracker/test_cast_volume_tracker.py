"""Tests for the cast_volume_tracker component."""

import os

from homeassistant.components.cast_volume_tracker import DOMAIN as CVT_DOMAIN
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MP_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
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


def check_volume_levels(hass, volume_dict):
    """Check that all volume levels are as expected."""
    return all(
        (
            hass.states.get(entity_id).attributes("volume_level") == volume_level
            for entity_id, volume_level in volume_dict.items()
        )
    )


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
    assert state.state == STATE_IDLE

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )

    # Make sure the media player is off
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF


async def test_cast_mock_turn_on_off_group(hass):
    """Test that a `cast_mock` group can be turned on and off."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)

    entity_id = "media_player.kitchen_speakers"
    members = ["media_player.computer_speakers", "media_player.kitchen_home"]

    # Make sure the media player and its members are off
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF
    for member in members:
        member_state = hass.states.get(member)
        assert member_state is not None
        assert member_state.state == STATE_OFF

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )
    await hass.async_block_till_done()

    # Make sure the media player and its members are idle
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_IDLE
    for member in members:
        member_state = hass.states.get(member)
        assert member_state is not None
        assert member_state.state == STATE_IDLE

    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )
    await hass.async_block_till_done()

    # Make sure the media player and its members are off
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF
    for member in members:
        member_state = hass.states.get(member)
        assert member_state is not None
        assert member_state.state == STATE_OFF


async def test_cast_mock_volume_set_individual(hass):
    """Test that the `media_player.volume_set` service works for an individual player."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)

    entity_id = "media_player.bedroom_mini"

    # Turn on the media player and set the volume
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.123},
        blocking=True,
    )

    # Make sure the media player's volume is as expected
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_IDLE
    assert state.attributes["volume_level"] == 0.123


async def test_cast_mock_volume_set_group(hass):
    """Test that the `media_player.volume_set` service works for a group."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)

    entity_id = "media_player.kitchen_speakers"
    members = ["media_player.computer_speakers", "media_player.kitchen_home"]

    # Turn on the media player and set the volume
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True,
    )
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.123},
        blocking=True,
    )

    # Make sure the media player's volume is as expected
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_IDLE
    assert state.attributes["volume_level"] == 0.123
    for member in members:
        member_state = hass.states.get(member)
        assert member_state is not None
        assert member_state.state == STATE_IDLE
        assert member_state.attributes["volume_level"] == 0.123


async def test_cast_mock_volume_set_individual_in_group(hass):
    """Test that the `media_player.volume_set` service works for an individual player that is part of a group."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)

    entity_id = "media_player.computer_speakers"
    group_entity_id = "media_player.kitchen_speakers"
    member_entity_ids = [entity_id, "media_player.kitchen_home"]

    # Set the volumes for the members
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: member_entity_ids, ATTR_MEDIA_VOLUME_LEVEL: 0.1},
        blocking=True,
    )

    # Turn on the group media player
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: group_entity_id}, blocking=True,
    )

    # Make sure the group media player's volume is as expected
    state = hass.states.get(group_entity_id)
    assert state is not None
    assert state.state == STATE_IDLE
    assert state.attributes["volume_level"] == 0.1

    # Set the individual media player's volume
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.3},
        blocking=True,
    )

    # Make sure the group media player's volume is as expected
    state = hass.states.get(group_entity_id)
    assert state is not None
    assert state.state == STATE_IDLE
    assert state.attributes["volume_level"] == 0.2


async def test_cvt_kitchen_speakers(hass):
    """Test a group with two members."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {
            ATTR_ENTITY_ID: "cast_volume_tracker.kitchen_speakers",
            ATTR_MEDIA_VOLUME_MUTED: True,
        },
        blocking=True,
    )

    # Set the Kitchen Home and Computer Speakers cast volume trackers to 7
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: [
                "cast_volume_tracker.computer_speakers",
                "cast_volume_tracker.kitchen_home",
            ],
            ATTR_MEDIA_VOLUME_LEVEL: 0.07,
        },
        blocking=True,
    )

    # While the speakers are off, set the cast volume tracker to 10
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: "cast_volume_tracker.kitchen_speakers",
            ATTR_MEDIA_VOLUME_LEVEL: 0.10,
        },
        blocking=True,
    )
    expected_volume_level = hass.states.get(
        "cast_volume_tracker.kitchen_speakers"
    ).attributes["expected_volume_level"]
    assert expected_volume_level == 0.0
    assert float(hass.states.get("cast_volume_tracker.kitchen_speakers").state) == 10.0

    expected_volume_level = hass.states.get(
        "cast_volume_tracker.computer_speakers"
    ).attributes["expected_volume_level"]
    assert expected_volume_level == 0.0
    assert float(hass.states.get("cast_volume_tracker.computer_speakers").state) == 10.0

    # Turn the speakers on
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "media_player.kitchen_speakers"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("media_player.kitchen_speakers").state == STATE_IDLE

    attrs = dict(hass.states.get("media_player.kitchen_speakers").attributes)
    attrs["volume_level"] = 0.10
    hass.states.async_set("media_player.kitchen_speakers", STATE_IDLE, attributes=attrs)
    await hass.async_block_till_done()
    # assert hass.states.get("cast_volume_tracker.kitchen_speakers").attributes["cast_is_on"]
    # assert hass.states.get("media_player.kitchen_speakers").attributes["volume_level"] == 0.10
    # assert hass.states.get("media_player.kitchen_home").attributes["volume_level"] == 0.10
    # assert float(hass.states.get("cast_volume_tracker.computer_speakers").attributes["expected_volume_level"]) == 10.
    # assert float(hass.states.get("cast_volume_tracker.kitchen_home").attributes["expected_volume_level"]) == 10.
