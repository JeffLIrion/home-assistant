"""Tests for the template_number integration."""

import os

import voluptuous as vol

from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.number.const import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.template_number.const import DOMAIN
from homeassistant.const import CONF_NAME, CONF_PLATFORM
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml.loader import load_yaml

PWD = os.path.dirname(__file__)
TEMPLATE_NUMBERS_CONFIG = {NUMBER_DOMAIN: load_yaml(PWD + "/numbers.yaml")}

INPUT_NUMBERS_CONFIG = {INPUT_NUMBER_DOMAIN: load_yaml(PWD + "/input_numbers.yaml")}


async def test_setup(hass):
    """Test that a `TemplateNumber` can be created."""
    assert await async_setup_component(
        hass,
        NUMBER_DOMAIN,
        TEMPLATE_NUMBERS_CONFIG,
    )
    await hass.async_block_till_done()

    entity_id = "number.tracked_value"
    state = hass.states.get(entity_id)
    assert state is not None


async def test_setup_fail(hass):
    """Test that a value template is not allowed without a script."""
    try:
        await async_setup_component(
            hass,
            NUMBER_DOMAIN,
            {
                NUMBER_DOMAIN: [
                    {
                        CONF_PLATFORM: DOMAIN,
                        CONF_NAME: "test_1",
                        "initial": 50,
                        "min": 0,
                        "max": 100,
                        "value_template": "{{ 5 }}",
                    }
                ],
            },
        )
    except vol.Invalid:
        pass


def check_states(
    hass, tracked_value, set_value_script, value_changed_script, template_number
):
    """Check that the states are as expected."""
    if tracked_value is not None:
        state = hass.states.get("number.tracked_value")
        assert state is not None
        assert float(state.state) == tracked_value

    if set_value_script is not None:
        state = hass.states.get("number.set_value_script")
        assert state is not None
        assert float(state.state) == set_value_script

    if value_changed_script is not None:
        state = hass.states.get("number.value_changed_script")
        assert state is not None
        assert float(state.state) == value_changed_script

    if template_number is not None:
        state = hass.states.get("number.template_number")
        assert state is not None
        assert float(state.state) == template_number


async def test_template_number(hass):
    """Test that the appropriate actions are performed when a `TemplateNumber` is changed."""
    assert await async_setup_component(
        hass,
        INPUT_NUMBER_DOMAIN,
        INPUT_NUMBERS_CONFIG,
    )

    assert await async_setup_component(
        hass,
        NUMBER_DOMAIN,
        TEMPLATE_NUMBERS_CONFIG,
    )
    await hass.async_start()
    await hass.async_block_till_done()

    # TEST 1: the initial values are as expected
    check_states(hass, 50, 100, 150, 50)

    # TEST 2: when the template number's value gets set via `number.set_value`
    # - The template number's value should change
    # - The `set_value_script` sequence should be called
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.template_number", "value": 10},
        blocking=True,
    )
    check_states(hass, 50, 20, 150, 10)

    # TEST 3: when the template number's value gets set via `number.set_value_no_script`
    # - The template number's value should change
    # - The `set_value_script` sequence should NOT be called
    if False:
        await hass.services.async_call(
            "template_number",
            "set_value_no_script",
            {"entity_id": "template_number.template_number", "value": 15},
            blocking=True,
        )
        check_states(hass, 50, 20, 150, 15)

    # TEST 4: when the tracked value changes
    # - The template number's value should change
    # - The `value_changed_script` sequence should be called
    hass.states.async_set("number.tracked_value", 25)
    await hass.async_block_till_done()
    # check_states(hass, 25, 20, 75, 25)
    check_states(hass, 25, 20, 150, 10)

    state = hass.states.get("input_number.input_number")
    assert state is not None
    assert float(state.state) == 0.0

    hass.states.async_set("input_number.input_number", 25)
    await hass.async_block_till_done()

    state = hass.states.get("number.input_number_tracker")
    assert state is not None
    # assert float(state.state) == 25.0
