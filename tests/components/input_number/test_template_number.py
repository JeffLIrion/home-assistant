"""The tests for the Input (Template) number component."""

import voluptuous as vol

from homeassistant.components.input_number import DOMAIN
from homeassistant.setup import async_setup_component


async def test_setup(hass):
    """Test that a `TemplateNumber` can be created."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                "test_1": {
                    "initial": 50,
                    "min": 0,
                    "max": 100,
                    "set_value_script": {"service": "homeassistant.restart"},
                }
            }
        },
    )
    entity_id = "input_number.test_1"

    state = hass.states.get(entity_id)
    assert state is not None


async def test_setup_fail(hass):
    """Test that a value template is not allowed without a script."""
    try:
        await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: {
                    "test_1": {
                        "initial": 50,
                        "min": 0,
                        "max": 100,
                        "value_template": "{{ 5 }}",
                    }
                }
            },
        )
    except vol.Invalid:
        pass


def check_states(
    hass, tracked_value, set_value_script, value_changed_script, template_number
):
    """Check that the states are as expected."""
    if tracked_value is not None:
        state = hass.states.get("input_number.tracked_value")
        assert state is not None
        assert float(state.state) == tracked_value

    if set_value_script is not None:
        state = hass.states.get("input_number.set_value_script")
        assert state is not None
        assert float(state.state) == set_value_script

    if value_changed_script is not None:
        state = hass.states.get("input_number.value_changed_script")
        assert state is not None
        assert float(state.state) == value_changed_script

    if template_number is not None:
        state = hass.states.get("input_number.template_number")
        assert state is not None
        assert float(state.state) == template_number


async def test_template_number(hass):
    """Test that the appropriate actions are performed when a `TemplateNumber` is changed."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                "tracked_value": {"initial": 50, "min": 0, "max": 100},
                "set_value_script": {"initial": 100, "min": 0, "max": 200},
                "value_changed_script": {"initial": 150, "min": 0, "max": 300},
                "template_number": {
                    "initial": 50,
                    "min": 0,
                    "max": 100,
                    "entity_id": "input_number.tracked_value",
                    "value_template": "{{ states('input_number.tracked_value') | round(0) }}",
                    "set_value_script": {
                        "service": "input_number.set_value",
                        "data_template": {
                            "entity_id": "input_number.set_value_script",
                            "value": "{{ value | multiply(2) }}",
                        },
                    },
                    "value_changed_script": {
                        "service": "input_number.set_value",
                        "data_template": {
                            "entity_id": "input_number.value_changed_script",
                            "value": "{{ value | multiply(3) }}",
                        },
                    },
                },
            }
        },
    )
    await hass.async_start()
    await hass.async_block_till_done()

    # TEST 1: the initial values are as expected
    check_states(hass, 50, 100, 150, 50)

    # TEST 2: when the template number's value gets set via `input_number.set_value`
    # - The template number's value should change
    # - The `set_value_script` sequence should be called
    await hass.services.async_call(
        "input_number",
        "set_value",
        {"entity_id": "input_number.template_number", "value": 10},
        blocking=True,
    )
    check_states(hass, 50, 20, 150, 10)

    # TEST 3: when the template number's value gets set via `input_number.set_value_no_script`
    # - The template number's value should change
    # - The `set_value_script` sequence should NOT be called
    await hass.services.async_call(
        "input_number",
        "set_value_no_script",
        {"entity_id": "input_number.template_number", "value": 15},
        blocking=True,
    )
    check_states(hass, 50, 20, 150, 15)

    # TEST 4: when the tracked value changes
    # - The template number's value should change
    # - The `value_changed_script` sequence should be called
    hass.states.async_set("input_number.tracked_value", 25)
    await hass.async_block_till_done()
    check_states(hass, 25, 20, 75, 25)
