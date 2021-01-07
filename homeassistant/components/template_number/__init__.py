"""Support to set a numeric value from a slider or text box."""
import logging
import typing

import voluptuous as vol

from homeassistant.components.input_number import InputNumber, NumberStorageCollection
from homeassistant.const import (
    ATTR_EDITABLE,
    ATTR_MODE,
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
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.script import Script
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import (
    ATTR_INITIAL,
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    CONF_INITIAL,
    CONF_MAX,
    CONF_MIN,
    CONF_SET_VALUE_SCRIPT,
    CONF_STEP,
    CONF_VALUE_CHANGED_SCRIPT,
    DOMAIN,
    MODE_BOX,
    MODE_SLIDER,
    SERVICE_DECREMENT,
    SERVICE_INCREMENT,
    SERVICE_SET_VALUE,
    SERVICE_SET_VALUE_NO_SCRIPT,
)

_LOGGER = logging.getLogger(__name__)


def cv_template_number(cfg):
    """Configure validation helper for template number (voluptuous)."""

    # From input_number
    minimum = cfg.get(CONF_MIN)
    maximum = cfg.get(CONF_MAX)
    if minimum >= maximum:
        raise vol.Invalid(
            f"Maximum ({minimum}) is not greater than minimum ({maximum})"
        )
    state = cfg.get(CONF_INITIAL)
    if state is not None and (state < minimum or state > maximum):
        raise vol.Invalid(f"Initial value {state} not in range {minimum}-{maximum}")

    # template_number
    if CONF_VALUE_TEMPLATE in cfg and CONF_SET_VALUE_SCRIPT not in cfg:
        raise vol.Invalid(
            "{} cannot be provided without {}".format(
                CONF_VALUE_TEMPLATE, CONF_SET_VALUE_SCRIPT
            )
        )

    return cfg


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.All(
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
                    vol.Optional(CONF_MODE, default=MODE_SLIDER): vol.In(
                        [MODE_BOX, MODE_SLIDER]
                    ),
                    # (Start) TemplateNumber
                    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
                    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
                    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
                    vol.Optional(CONF_SET_VALUE_SCRIPT): cv.SCRIPT_SCHEMA,
                    vol.Optional(CONF_VALUE_CHANGED_SCRIPT): cv.SCRIPT_SCHEMA,
                    # (End) TemplateNumber
                },
                cv_template_number,
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up a template number."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    id_manager = collection.IDManager()

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection"), id_manager
    )
    collection.attach_entity_component_collection(
        component, yaml_collection, lambda cfg: TemplateNumber.from_yaml(cfg, hass)
    )

    storage_collection = NumberStorageCollection(
        Store(hass, STORAGE_VERSION, STORAGE_KEY),
        logging.getLogger(f"{__name__}.storage_collection"),
        id_manager,
    )
    collection.attach_entity_component_collection(
        component, storage_collection, TemplateNumber
    )

    await yaml_collection.async_load(
        [{CONF_ID: id_, **(conf or {})} for id_, conf in config.get(DOMAIN, {}).items()]
    )
    await storage_collection.async_load()

    component.async_register_entity_service(
        SERVICE_SET_VALUE,
        {vol.Required(ATTR_VALUE): vol.Coerce(float)},
        "async_set_value",
    )

    component.async_register_entity_service(SERVICE_INCREMENT, {}, "async_increment")

    component.async_register_entity_service(SERVICE_DECREMENT, {}, "async_decrement")

    # (Start) Template Number
    component.async_register_entity_service(
        SERVICE_SET_VALUE_NO_SCRIPT,
        {vol.Required(ATTR_VALUE): vol.Coerce(float)},
        "async_set_value_no_script",
    )
    # (End) Template Number

    return True


class TemplateNumber(InputNumber):
    """Representation of a template number."""

    def __init__(
        self, config: typing.Dict, hass: typing.Optional[HomeAssistantType] = None
    ):
        """Initialize an input number."""
        super().__init__(config)
        self._config = config  # Delete
        self.editable = True  # Delete
        self._current_value = config.get(CONF_INITIAL)

        self._initial = config.get(CONF_INITIAL)
        self.__maximum = config[CONF_MAX]
        self.__minimum = config[CONF_MIN]
        self._mode = config[CONF_MODE]
        self._name = config.get(CONF_NAME)
        self.__step = config[CONF_STEP]
        self._unique_id = config[CONF_ID]
        self._unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT)

        self._entities = config.get(CONF_ENTITY_ID, set())
        self.hass = hass if config.get(CONF_SET_VALUE_SCRIPT) is not None else None

        # template
        self._value_template = config.get(CONF_VALUE_TEMPLATE)
        if self._value_template is not None:
            self._value_template.hass = self.hass

        # icon template
        self._icon = None
        self._icon_template = config.get(CONF_ICON_TEMPLATE)
        if self._icon_template is not None:
            self._icon_template.hass = self.hass

        # set_value_script
        if config.get(CONF_SET_VALUE_SCRIPT) is not None:
            self._set_value_script = Script(
                hass,
                config[CONF_SET_VALUE_SCRIPT],
                config.get(CONF_NAME, "Template Number script"),
                DOMAIN,
            )
        else:
            self._set_value_script = None

        # value_changed_script
        if config.get(CONF_VALUE_CHANGED_SCRIPT) is not None:
            self._value_changed_script = Script(
                hass,
                config[CONF_VALUE_CHANGED_SCRIPT],
                config.get(CONF_NAME, "Template Number script"),
                DOMAIN,
            )
        else:
            self._value_changed_script = None

    @property
    def _minimum(self) -> float:
        """Return minimum allowed value."""
        return self.__minimum

    @property
    def _maximum(self) -> float:
        """Return maximum allowed value."""
        return self.__maximum

    @property
    def _step(self) -> int:
        """Return entity's increment/decrement step."""
        return self.__step

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
    def state(self):
        """Return the state of the component."""
        return self._current_value

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def unique_id(self) -> typing.Optional[str]:
        """Return unique id of the entity."""
        return self._unique_id

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_INITIAL: self._initial,
            ATTR_EDITABLE: self.editable,
            ATTR_MIN: self._minimum,
            ATTR_MAX: self._maximum,
            ATTR_STEP: self._step,
            ATTR_MODE: self._mode,
        }

    @classmethod
    def from_yaml(  # pylint: disable=arguments-differ
        cls, config: typing.Dict, hass: HomeAssistantType
    ) -> "TemplateNumber":  # pylint: disable=arguments-differ
        """Return entity instance initialized from yaml storage."""
        template_num = cls(config, hass)
        template_num.entity_id = f"{DOMAIN}.{config[CONF_ID]}"
        template_num.editable = False
        return template_num

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

        # Call `InputNumber.async_added_to_hass`
        # await super().async_added_to_hass()

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
            raise vol.Invalid(
                f"Invalid value for {self.entity_id}: {value} (range {self._minimum} - {self._maximum})"
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
        await self.async_set_value(min(self._current_value + self._step, self._maximum))

    async def async_decrement(self):
        """Decrement value."""
        await self.async_set_value(max(self._current_value - self._step, self._minimum))

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
