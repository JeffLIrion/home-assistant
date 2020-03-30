"""Tests for the cast_volume_tracker component."""

import logging
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

_LOGGER = logging.getLogger(__name__)
PWD = os.path.dirname(__file__)

ATTR_CAST_IS_ON = "cast_is_on"
ATTR_EXPECTED_VOLUME_LEVEL = "expected_volume_level"
ATTR_VALUE = "value"

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
            hass.states.get(entity_id).attributes[ATTR_MEDIA_VOLUME_LEVEL]
            == volume_level
            for entity_id, volume_level in volume_dict.items()
        )
    )


def check_attr(hass, entity_id, expected_value, attr=ATTR_MEDIA_VOLUME_LEVEL):
    """Check the value of an attribute."""
    if isinstance(expected_value, float):
        return float(hass.states.get(entity_id).attributes[attr]) == expected_value
    if isinstance(expected_value, int):
        return int(hass.states.get(entity_id).attributes[attr]) == expected_value
    if isinstance(expected_value, bool):
        return hass.states.get(entity_id).attributes[attr] is expected_value
    return hass.states.get(entity_id).attributes[attr] == expected_value


def check_cvt(hass, entity_id, attributes):
    """Check the state attributes of a cast volume tracker."""
    state_attrs = hass.states.get(entity_id).attributes
    if (
        attributes[ATTR_CAST_IS_ON] is not None
        and state_attrs[ATTR_CAST_IS_ON] is not attributes[ATTR_CAST_IS_ON]
    ):
        _LOGGER.critical(
            "%s = %s",
            ATTR_CAST_IS_ON,
            "True" if state_attrs[ATTR_CAST_IS_ON] else "False",
        )
        return False
    if (
        attributes[ATTR_VALUE] is not None
        and abs(state_attrs[ATTR_VALUE] - attributes[ATTR_VALUE]) > 1e-5
    ):
        _LOGGER.critical("%s = %d", ATTR_VALUE, state_attrs[ATTR_VALUE])
        return False
    if (
        attributes[ATTR_MEDIA_VOLUME_LEVEL] is not None
        and state_attrs[ATTR_MEDIA_VOLUME_LEVEL] != attributes[ATTR_MEDIA_VOLUME_LEVEL]
    ):
        _LOGGER.critical(
            "%s = %f", ATTR_MEDIA_VOLUME_LEVEL, state_attrs[ATTR_MEDIA_VOLUME_LEVEL]
        )
        return False
    if (
        attributes[ATTR_EXPECTED_VOLUME_LEVEL] is not None
        and state_attrs[ATTR_EXPECTED_VOLUME_LEVEL]
        != attributes[ATTR_EXPECTED_VOLUME_LEVEL]
    ):
        _LOGGER.critical(
            "%s = %f",
            ATTR_EXPECTED_VOLUME_LEVEL,
            state_attrs[ATTR_EXPECTED_VOLUME_LEVEL],
        )
        return False
    if (
        attributes[ATTR_MEDIA_VOLUME_MUTED] is not None
        and state_attrs[ATTR_MEDIA_VOLUME_MUTED]
        is not attributes[ATTR_MEDIA_VOLUME_MUTED]
    ):
        _LOGGER.critical(
            "%s = %s",
            ATTR_MEDIA_VOLUME_MUTED,
            "True" if state_attrs[ATTR_MEDIA_VOLUME_LEVEL] else "False",
        )
        return False
    return True


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


# =========================================================================== #
#                                                                             #
#                                  Cast Mock                                  #
#                                                                             #
# =========================================================================== #
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
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.123


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
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.123
    for member in members:
        member_state = hass.states.get(member)
        assert member_state is not None
        assert member_state.state == STATE_IDLE
        assert member_state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.123


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
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.1

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
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.2


# =========================================================================== #
#                                                                             #
#                        Cast Volume Tracker (control)                        #
#                                                                             #
# =========================================================================== #
async def test_cvt_computer_speakers_control(hass):
    """Test an individual cast volume tracker."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.async_start()
    await hass.async_block_till_done()

    mp_entity_id = "media_player.computer_speakers"
    cvt_entity_id = "cast_volume_tracker.computer_speakers"

    cvt_attrs = {
        ATTR_CAST_IS_ON: False,
        ATTR_VALUE: 0.0,
        ATTR_MEDIA_VOLUME_LEVEL: None,
        ATTR_EXPECTED_VOLUME_LEVEL: 0.0,
        ATTR_MEDIA_VOLUME_MUTED: True,
    }

    # Turn the speaker off
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )
    assert check_attr(hass, cvt_entity_id, False, ATTR_CAST_IS_ON)

    # While the speaker is off, set the volume to 10
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.10},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 10.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Turn the speaker on
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )
    cvt_attrs[ATTR_CAST_IS_ON] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.1
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.1
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Set the volume to 11
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.11},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 11.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)
    assert check_attr(hass, mp_entity_id, 0.0)
    assert check_attr(hass, cvt_entity_id, True, ATTR_MEDIA_VOLUME_MUTED)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.11
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.11
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Set the volume to 22
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.22},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 22.0
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.22
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.22
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Set the volume to 33
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.33},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 33.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.33
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.33
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)


async def test_cvt_kitchen_speakers_control(hass):
    """Test a group with two members."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.async_start()
    await hass.async_block_till_done()


# =========================================================================== #
#                                                                             #
#                         Cast Volume Tracker (track)                         #
#                                                                             #
# =========================================================================== #
async def test_cvt_computer_speakers_track(hass):
    """Test an individual cast volume tracker."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.async_start()
    await hass.async_block_till_done()

    mp_entity_id = "media_player.computer_speakers"
    cvt_entity_id = "cast_volume_tracker.computer_speakers"

    # Turn the speaker on
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )

    computer_speakers = hass.data["cast_mock"]["computer_speakers"]
    _LOGGER.critical(computer_speakers.state_)
    _LOGGER.critical(computer_speakers.volume_level_)
    hass.states.async_set(
        mp_entity_id,
        computer_speakers.state_,
        attributes={"volume_level": computer_speakers.volume_level_},
    )
    await hass.async_block_till_done()

    cast_is_on = hass.states.get(cvt_entity_id).attributes["cast_is_on"]
    assert cast_is_on

    if 1:
        return

    assert hass.data["cast_mock"]["computer_speakers"].state_ == STATE_IDLE
    assert hass.states.get(mp_entity_id).attributes["volume_level"] == 0.321
    # assert hass.data[MP_DOMAIN]["computer_speakers"].volume_level_ == 0.321
    # assert hass.states.get("media_player.computer_speakers").attributes["volume_level"] == 0.321

    # While the speakers are off, set the volume to 10
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.123},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("media_player.computer_speakers").state == STATE_IDLE
    assert (
        hass.states.get("media_player.computer_speakers").attributes["volume_level"]
        == 0.123
    )
    assert hass.states.get("")

    attrs = dict(hass.states.get("media_player.computer_speakers").attributes)
    attrs["volume_level"] = 0.10
    hass.states.async_set(
        "media_player.computer_speakers", STATE_IDLE, attributes=attrs
    )
    await hass.async_block_till_done()
    # assert hass.states.get("cast_volume_tracker.computer_speakers").attributes["cast_is_on"]


async def test_cvt_kitchen_speakers_track(hass):
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


# =========================================================================== #
#                                                                             #
#                    Cast Volume Tracker (real world tests)                   #
#                                                                             #
# =========================================================================== #
async def test_kitchen_home(hass):
    """Test the Kitchen Home cast volume tracker."""
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.async_start()
    await hass.async_block_till_done()

    mp_entity_id = "media_player.kitchen_home"
    cvt_entity_id = "cast_volume_tracker.kitchen_home"

    cvt_attrs = {
        ATTR_CAST_IS_ON: False,
        ATTR_VALUE: 0.0,
        ATTR_MEDIA_VOLUME_LEVEL: None,
        ATTR_EXPECTED_VOLUME_LEVEL: 0.0,
        ATTR_MEDIA_VOLUME_MUTED: True,
    }

    # Turn off the media player
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )
    assert check_attr(hass, cvt_entity_id, False, ATTR_CAST_IS_ON)

    # While the media player is off, set the volume to 10
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.10},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 10.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Turn the media player on
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )
    cvt_attrs[ATTR_CAST_IS_ON] = True

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.10
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # While the speakers are on and not muted, set the volume to 15
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.15},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 15.0
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.15
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.15
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # While the speakers are on and muted, set the volume to 7
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.07},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 7.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.07
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.07
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    # Set the media player volume to 0.05
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.05},
        blocking=True,
    )
    cvt_attrs[ATTR_VALUE] = 5.0
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.05
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.05
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)


async def test_kitchen_speakers(hass):
    """Test the Kitchen Speakers cast volume tracker."""
    # pytest --log-cli-level=CRITICAL  tests/components/cast_volume_tracker/test_cast_volume_tracker.py::test_kitchen_speakers
    assert await async_setup_component(hass, MP_DOMAIN, CAST_MOCK_CONFIG)
    assert await async_setup_component(hass, CVT_DOMAIN, CAST_VOLUME_TRACKER_CONFIG)

    await hass.async_start()
    await hass.async_block_till_done()

    mp_entity_id = "media_player.kitchen_speakers"
    cvt_entity_id = "cast_volume_tracker.kitchen_speakers"

    mp_computer_speakers = "media_player.computer_speakers"
    cvt_computer_speakers = "cast_volume_tracker.computer_speakers"

    mp_kitchen_home = "media_player.kitchen_home"
    cvt_kitchen_home = "cast_volume_tracker.kitchen_home"

    cvt_attrs = {
        ATTR_CAST_IS_ON: False,
        ATTR_VALUE: None,
        ATTR_MEDIA_VOLUME_LEVEL: None,
        ATTR_EXPECTED_VOLUME_LEVEL: None,
        ATTR_MEDIA_VOLUME_MUTED: None,
    }

    cvt_cs_attrs = {
        ATTR_CAST_IS_ON: False,
        ATTR_VALUE: 0.0,
        ATTR_MEDIA_VOLUME_LEVEL: None,
        ATTR_EXPECTED_VOLUME_LEVEL: 0.0,
        ATTR_MEDIA_VOLUME_MUTED: True,
    }

    cvt_kh_attrs = {
        ATTR_CAST_IS_ON: False,
        ATTR_VALUE: 0.0,
        ATTR_MEDIA_VOLUME_LEVEL: None,
        ATTR_EXPECTED_VOLUME_LEVEL: 0.0,
        ATTR_MEDIA_VOLUME_MUTED: None,
    }

    # Turn off the media players
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [mp_entity_id, mp_computer_speakers, mp_kitchen_home]},
        blocking=True,
    )
    assert check_attr(hass, cvt_entity_id, False, ATTR_CAST_IS_ON)
    assert check_attr(hass, cvt_computer_speakers, False, ATTR_CAST_IS_ON)
    assert check_attr(hass, cvt_kitchen_home, False, ATTR_CAST_IS_ON)

    # Set the Kitchen Home and Computer Speakers cast volume trackers to 7
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: [cvt_computer_speakers, cvt_kitchen_home],
            ATTR_MEDIA_VOLUME_LEVEL: 0.07,
        },
        blocking=True,
    )

    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 7.0
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_VALUE] = 7.0
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.07
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.07
    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # While the media players are off, set the cast volume tracker to 10
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.1},
        blocking=True,
    )

    cvt_attrs[ATTR_VALUE] = 10.0
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 10.0
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Turn the media player on
    await hass.services.async_call(
        MP_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: mp_entity_id}, blocking=True,
    )

    cvt_attrs[ATTR_VALUE] = 10.0
    cvt_attrs[ATTR_CAST_IS_ON] = True
    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 10.0
    cvt_cs_attrs[ATTR_CAST_IS_ON] = True
    cvt_cs_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_VALUE] = 10.0
    cvt_kh_attrs[ATTR_CAST_IS_ON] = True
    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )

    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )

    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.10
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # While the speakers are on and not muted, set the volume to 15
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.15},
        blocking=True,
    )

    cvt_attrs[ATTR_VALUE] = 15.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.15
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 15.0
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.15
    cvt_cs_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_VALUE] = 15.0
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.15
    cvt_kh_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: True},
        blocking=True,
    )

    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = True
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # While the speakers are on and muted, set the volume to 5
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.05},
        blocking=True,
    )

    cvt_attrs[ATTR_VALUE] = 5.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 5.0
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    cvt_cs_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_VALUE] = 5.0
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.0
    cvt_kh_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Un-mute the volume
    await hass.services.async_call(
        CVT_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: cvt_entity_id, ATTR_MEDIA_VOLUME_MUTED: False},
        blocking=True,
    )

    cvt_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.05
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.05
    assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_MEDIA_VOLUME_MUTED] = False
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.05
    assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # Set one media player volume to 0.11
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: mp_kitchen_home, ATTR_MEDIA_VOLUME_LEVEL: 0.11},
        blocking=True,
    )

    cvt_attrs[ATTR_VALUE] = 8.0
    cvt_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.08
    cvt_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    assert check_cvt(hass, cvt_entity_id, cvt_attrs)

    cvt_cs_attrs[ATTR_VALUE] = 8.0
    cvt_cs_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.08
    cvt_cs_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    # assert check_cvt(hass, cvt_computer_speakers, cvt_cs_attrs)

    cvt_kh_attrs[ATTR_VALUE] = 8.0
    cvt_kh_attrs[ATTR_EXPECTED_VOLUME_LEVEL] = 0.08
    cvt_kh_attrs[ATTR_MEDIA_VOLUME_LEVEL] = None
    # assert check_cvt(hass, cvt_kitchen_home, cvt_kh_attrs)

    # assert False
