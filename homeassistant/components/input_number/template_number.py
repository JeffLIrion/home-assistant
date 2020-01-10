"""Template number functionality."""
import logging

import voluptuous as vol

from homeassistant.const import (  # noqa pylint: disable=unused-import
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_ID,
    CONF_ICON,
    CONF_ICON_TEMPLATE,
    CONF_MODE,
    CONF_NAME,
    CONF_VALUE_TEMPLATE,
    EVENT_HOMEASSISTANT_START,
    MATCH_ALL,
)
from homeassistant.core import callback  # noqa pylint: disable=unused-import
from homeassistant.exceptions import TemplateError  # noqa pylint: disable=unused-import
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (  # noqa pylint: disable=unused-import
    async_track_state_change,
)
from homeassistant.helpers.script import Script  # noqa pylint: disable=unused-import

# from homeassistant.components.input_number import (
#    #InputNumber,
#    #_cv_input_number,
#    CONF_MIN,
#    CONF_MAX,
#    CONF_INITIAL,
#    CONF_STEP)

_LOGGER = logging.getLogger(__name__)

CONF_SET_VALUE_SCRIPT = "set_value_script"
CONF_VALUE_CHANGED_SCRIPT = "value_changed_script"

SERVICE_SET_VALUE_NO_SCRIPT = "set_value_no_script"


TEMPLATE_NUMBER_SCHEMA_DICT = {
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_SET_VALUE_SCRIPT): cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    vol.Optional(CONF_VALUE_CHANGED_SCRIPT): cv.SCRIPT_SCHEMA,
}


'''def _cv_template_number(cfg):
    """Configure validation helper for template number (voluptuous)."""
    # _cv_input_number(cfg)

    if CONF_VALUE_TEMPLATE in cfg and CONF_SET_VALUE_SCRIPT not in cfg:
        raise vol.Invalid(
            "{} cannot be provided without {}".format(
                CONF_VALUE_TEMPLATE, CONF_SET_VALUE_SCRIPT
            )
        )

    return cfg'''


'''def setup_template_number_entity(hass, cfg, object_id):
    """Create a `TemplateNumber` entity."""
    name = cfg.get(CONF_NAME)
    minimum = cfg.get(CONF_MIN)
    maximum = cfg.get(CONF_MAX)
    initial = cfg.get(CONF_INITIAL)
    step = cfg.get(CONF_STEP)
    icon = cfg.get(CONF_ICON)
    unit = cfg.get(ATTR_UNIT_OF_MEASUREMENT)
    mode = cfg.get(CONF_MODE)
    icon_template = cfg.get(CONF_ICON_TEMPLATE)
    set_value_script = cfg.get(CONF_SET_VALUE_SCRIPT)
    value_template = cfg.get(CONF_VALUE_TEMPLATE)
    value_changed_script = cfg.get(CONF_VALUE_CHANGED_SCRIPT)

    # setup the entity ID's for the template
    template_entity_ids = set()
    if value_template is not None:
        temp_ids = value_template.extract_entities()
        if str(temp_ids) != MATCH_ALL:
            template_entity_ids |= set(temp_ids)

    if icon_template is not None:
        icon_ids = icon_template.extract_entities()
        if str(icon_ids) != MATCH_ALL:
            template_entity_ids |= set(icon_ids)

    entity_ids = cfg.get(CONF_ENTITY_ID, template_entity_ids)

    return TemplateNumber(
        object_id,
        name,
        initial,
        minimum,
        maximum,
        step,
        icon,
        icon_template,
        unit,
        mode,
        hass,
        value_template,
        set_value_script,
        entity_ids,
        value_changed_script,
    )'''


def setup_template_number_entity(
    constructor, hass, cfg, object_id, minimum, maximum, initial, step
):
    """Create a `TemplateNumber` entity."""
    name = cfg.get(CONF_NAME)
    icon = cfg.get(CONF_ICON)
    unit = cfg.get(ATTR_UNIT_OF_MEASUREMENT)
    mode = cfg.get(CONF_MODE)
    icon_template = cfg.get(CONF_ICON_TEMPLATE)
    set_value_script = cfg.get(CONF_SET_VALUE_SCRIPT)
    value_template = cfg.get(CONF_VALUE_TEMPLATE)
    value_changed_script = cfg.get(CONF_VALUE_CHANGED_SCRIPT)

    # setup the entity ID's for the template
    template_entity_ids = set()
    if value_template is not None:
        temp_ids = value_template.extract_entities()
        if str(temp_ids) != MATCH_ALL:
            template_entity_ids |= set(temp_ids)

    if icon_template is not None:
        icon_ids = icon_template.extract_entities()
        if str(icon_ids) != MATCH_ALL:
            template_entity_ids |= set(icon_ids)

    entity_ids = cfg.get(CONF_ENTITY_ID, template_entity_ids)

    return constructor(
        object_id,
        name,
        initial,
        minimum,
        maximum,
        step,
        icon,
        icon_template,
        unit,
        mode,
        hass,
        value_template,
        set_value_script,
        entity_ids,
        value_changed_script,
    )


def cv_template_number(cv_input_number):
    """Configure validation helper for template number (voluptuous)."""

    def _cv_template_number(cfg):
        cv_input_number(cfg)

        if CONF_VALUE_TEMPLATE in cfg and CONF_SET_VALUE_SCRIPT not in cfg:
            raise vol.Invalid(
                "{} cannot be provided without {}".format(
                    CONF_VALUE_TEMPLATE, CONF_SET_VALUE_SCRIPT
                )
            )

        return cfg

    return _cv_template_number


'''class TemplateNumber(InputNumber):
    """Representation of a slider with template functionality."""

    def __init__(
        self,
        object_id,
        name,
        initial,
        minimum,
        maximum,
        step,
        icon,
        icon_template,
        unit,
        mode,
        hass,
        value_template,
        set_value_script,
        entity_ids,
        value_changed_script,
    ):
        """Initialize a template number."""
        super().__init__(
            object_id, name, initial, minimum, maximum, step, icon, unit, mode
        )
        self.hass = hass
        self._entities = entity_ids

        # template
        self._value_template = value_template
        if self._value_template is not None:
            self._value_template.hass = self.hass

        # icon template
        self._icon_template = icon_template
        if self._icon_template is not None:
            self._icon_template.hass = self.hass

        # set_value_script
        if set_value_script:
            self._set_value_script = Script(hass, set_value_script)
        else:
            self._set_value_script = None

        # value_changed_script
        if value_changed_script:
            self._value_changed_script = Script(hass, value_changed_script)
        else:
            self._value_changed_script = None

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass and register callbacks."""

        @callback
        def template_number_state_listener(entity, old_state, new_state):
            """Handle target device state changes."""
            self.async_schedule_update_ha_state(True)

        @callback
        def template_number_startup(event):
            """Listen for state changes."""
            if self._entities:
                async_track_state_change(
                    self.hass, self._entities, template_number_state_listener
                )

            self.async_schedule_update_ha_state(True)

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, template_number_startup
        )

        await super().async_added_to_hass()
        if self._current_value is not None:
            return

        state = await self.async_get_last_state()
        value = state and float(state.state)

        # Check against None because value can be 0
        if value is not None and self._minimum <= value <= self._maximum:
            self._current_value = value
        else:
            self._current_value = self._minimum

    async def async_set_value(self, value):
        """Set new value."""
        num_value = float(value)
        if num_value < self._minimum or num_value > self._maximum:
            _LOGGER.warning(
                "Invalid value: %s (range %s - %s)",
                num_value,
                self._minimum,
                self._maximum,
            )
            return
        self._current_value = num_value

        if self._set_value_script:
            await self._set_value_script.async_run(
                {"value": self._current_value}, context=self._context
            )
        await self.async_update_ha_state()

    async def async_increment(self):
        """Increment value."""
        new_value = self._current_value + self._step
        if new_value > self._maximum:
            _LOGGER.warning(
                "Invalid value: %s (range %s - %s)",
                new_value,
                self._minimum,
                self._maximum,
            )
            return
        self._current_value = new_value

        if self._set_value_script:
            await self._set_value_script.async_run(
                {"value": self._current_value}, context=self._context
            )

        await self.async_update_ha_state()

    async def async_decrement(self):
        """Decrement value."""
        new_value = self._current_value - self._step
        if new_value < self._minimum:
            _LOGGER.warning(
                "Invalid value: %s (range %s - %s)",
                new_value,
                self._minimum,
                self._maximum,
            )
            return
        self._current_value = new_value

        if self._set_value_script:
            await self._set_value_script.async_run(
                {"value": self._current_value}, context=self._context
            )

        await self.async_update_ha_state()

    async def async_update(self):
        """Update the state from the template."""
        if self._value_template:
            try:
                value = self._value_template.async_render()
                if value not in ["None", "unknown"] and self._current_value != float(
                    value
                ):
                    self._current_value = float(value)

                    if self._value_changed_script:
                        await self._value_changed_script.async_run(
                            {"value": self._current_value}, context=self._context
                        )

            except TemplateError as ex:
                _LOGGER.error(ex)

        if self._icon_template:
            try:
                setattr(self, "_icon", self._icon_template.async_render())
            except TemplateError as ex:
                if ex.args and ex.args[0].startswith(
                    "UndefinedError: 'None' has no attribute"
                ):
                    # Common during HA startup - so just a warning
                    _LOGGER.warning(
                        "Could not render icon template for %s, "
                        "the state is unknown.",
                        self._name,
                    )'''
