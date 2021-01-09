"""Number platform for the template_number integration."""

import logging
import typing

import voluptuous as vol

from homeassistant.components.number import PLATFORM_SCHEMA, NumberEntity
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_ICON,
    CONF_ICON_TEMPLATE,
    CONF_ID,
    CONF_MODE,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.script import Script
from homeassistant.helpers.typing import HomeAssistantType

from .const import (
    CONF_INITIAL,
    CONF_MAX,
    CONF_MIN,
    CONF_SET_VALUE_SCRIPT,
    CONF_STEP,
    CONF_VALUE_CHANGED_SCRIPT,
    DOMAIN,
    MODE_BOX,
    MODE_SLIDER,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_MIN): vol.Coerce(float),
        vol.Required(CONF_MAX): vol.Coerce(float),
        vol.Optional(CONF_INITIAL): vol.Coerce(float),
        vol.Optional(CONF_STEP, default=1): vol.All(
            vol.Coerce(float), vol.Range(min=1e-3)
        ),
        vol.Optional(CONF_ICON): cv.icon,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_MODE, default=MODE_SLIDER): vol.In([MODE_BOX, MODE_SLIDER]),
        # (Start) TemplateNumber
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_SET_VALUE_SCRIPT): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_VALUE_CHANGED_SCRIPT): cv.SCRIPT_SCHEMA,
        # (End) TemplateNumber
    },
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the number platform for the template_number integration."""
    template_number = TemplateNumberEntity(config, hass)
    async_add_entities([template_number])


class TemplateNumberEntity(NumberEntity):
    """Template number... number."""

    def __init__(
        self, config: typing.Dict, hass: typing.Optional[HomeAssistantType] = None
    ):
        """Initialize a template number."""
        # super().__init__(config)

        self._current_value = config.get(CONF_INITIAL)
        self._max_value = config[CONF_MAX]
        self._min_value = config[CONF_MIN]
        self._mode = config[CONF_MODE]
        self._name = config.get(CONF_NAME)
        self._step = config[CONF_STEP]
        self._unique_id = config.get(CONF_ID)
        self._unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT)

        self._entities = config.get(CONF_ENTITY_ID, set())
        self.hass = hass if config.get(CONF_SET_VALUE_SCRIPT) else None

        # template
        self._value_template = config.get(CONF_VALUE_TEMPLATE)
        if self._value_template:
            self._value_template.hass = self.hass

        # icon template
        self._icon = None
        self._icon_template = config.get(CONF_ICON_TEMPLATE)
        if self._icon_template:
            self._icon_template.hass = self.hass

        # set_value_script
        if config.get(CONF_SET_VALUE_SCRIPT):
            self._set_value_script = Script(
                hass,
                config[CONF_SET_VALUE_SCRIPT],
                config.get(CONF_NAME, "Template Number set_value_script"),
                DOMAIN,
            )
        else:
            self._set_value_script = None

        # value_changed_script
        if config.get(CONF_VALUE_CHANGED_SCRIPT):
            self._value_changed_script = Script(
                hass,
                config[CONF_VALUE_CHANGED_SCRIPT],
                config.get(CONF_NAME, "Template Number value_changed_script"),
                DOMAIN,
            )
        else:
            self._value_changed_script = None

    @property
    def value(self) -> float:
        """Return the entity value to represent the entity state."""
        return self._current_value

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the input slider."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def unique_id(self) -> typing.Optional[str]:
        """Return unique id of the entity."""
        return self._unique_id

    @property
    def min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def step(self) -> float:
        """Return the increment/decrement step."""
        return self._step

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        # If this is a true `TemplateNumber`, then listen for state changes
        if self._set_value_script:

            @callback
            def template_number_state_listener(entity):
                """Handle target device state changes."""
                self.async_schedule_update_ha_state(True)

            @callback
            def template_number_startup(event):
                """Listen for state changes."""
                if self._entities:
                    async_track_state_change_event(
                        self.hass, self._entities, template_number_state_listener
                    )

                self.async_schedule_update_ha_state(True)

            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, template_number_startup
            )

    async def async_set_value(self, value):
        """Set new value."""
        num_value = float(value)

        if num_value < self._min_value or num_value > self._max_value:
            raise vol.Invalid(
                f"Invalid value for {self.entity_id}: {value} (range {self._min_value} - {self._max_value})"
            )

        self._current_value = num_value

        # This is the only part of the function that differs from `InputNumber.async_set_value()`
        if not self._set_value_script:
            self.async_write_ha_state()
            return

        await self._set_value_script.async_run(
            {"value": self._current_value}, context=self._context
        )
        await self.async_update_ha_state()

    async def async_increment(self):
        """Increment value."""
        await self.async_set_value(
            min(self._current_value + self._step, self._max_value)
        )

    async def async_decrement(self):
        """Decrement value."""
        await self.async_set_value(
            max(self._current_value - self._step, self._min_value)
        )

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
                self._icon = self._icon_template.async_render()
            except TemplateError as ex:
                if ex.args and ex.args[0].startswith(
                    "UndefinedError: 'None' has no attribute"
                ):
                    # Common during HA startup - so just a warning
                    _LOGGER.warning(
                        "Could not render icon template for %s, "
                        "the state is unknown.",
                        self.name,
                    )
