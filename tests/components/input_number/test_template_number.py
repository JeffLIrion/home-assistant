"""The tests for the Input (Template) number component."""

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
