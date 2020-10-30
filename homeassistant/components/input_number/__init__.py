"""Support to set a numeric value from a slider or text box."""
import logging
import typing

import voluptuous as vol

from homeassistant.const import (
    ATTR_EDITABLE,
    ATTR_MODE,
    CONF_ICON,
    CONF_ID,
    CONF_MODE,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    SERVICE_RELOAD,
)
from homeassistant.core import callback
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.helpers.service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType

from .template_number import (
    CONF_ENTITY_ID,
    CONF_ICON_TEMPLATE,
    CONF_SET_VALUE_SCRIPT,
    CONF_VALUE_CHANGED_SCRIPT,
    CONF_VALUE_TEMPLATE,
    EVENT_HOMEASSISTANT_START,
    SERVICE_SET_VALUE_NO_SCRIPT,
    TEMPLATE_NUMBER_CREATE_FIELDS,
    TEMPLATE_NUMBER_UPDATE_FIELDS,
    Optional,
    Script,
    TemplateError,
    async_track_state_change_event,
    cv_template_number,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "input_number"

CONF_INITIAL = "initial"
CONF_MIN = "min"
CONF_MAX = "max"
CONF_STEP = "step"

MODE_SLIDER = "slider"
MODE_BOX = "box"

ATTR_INITIAL = "initial"
ATTR_VALUE = "value"
ATTR_MIN = "min"
ATTR_MAX = "max"
ATTR_STEP = "step"

SERVICE_SET_VALUE = "set_value"
SERVICE_INCREMENT = "increment"
SERVICE_DECREMENT = "decrement"


def _cv_input_number0(cfg):
    """Configure validation helper for input number (voluptuous)."""
    minimum = cfg.get(CONF_MIN)
    maximum = cfg.get(CONF_MAX)
    if minimum >= maximum:
        raise vol.Invalid(
            f"Maximum ({minimum}) is not greater than minimum ({maximum})"
        )
    state = cfg.get(CONF_INITIAL)
    if state is not None and (state < minimum or state > maximum):
        raise vol.Invalid(f"Initial value {state} not in range {minimum}-{maximum}")
    return cfg


# (Start) TemplateNumber
def _cv_input_number(cfg):
    """Configure validation helper for template number (voluptuous)."""
    return cv_template_number(_cv_input_number0)(cfg)


# (End) TemplateNumber


CREATE_FIELDS = {
    vol.Required(CONF_NAME): vol.All(str, vol.Length(min=1)),
    vol.Required(CONF_MIN): vol.Coerce(float),
    vol.Required(CONF_MAX): vol.Coerce(float),
    vol.Optional(CONF_INITIAL): vol.Coerce(float),
    vol.Optional(CONF_STEP, default=1): vol.All(vol.Coerce(float), vol.Range(min=1e-3)),
    vol.Optional(CONF_ICON): cv.icon,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_MODE, default=MODE_SLIDER): vol.In([MODE_BOX, MODE_SLIDER]),
}
CREATE_FIELDS.update(TEMPLATE_NUMBER_CREATE_FIELDS)  # TemplateNumber

UPDATE_FIELDS = {
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_MIN): vol.Coerce(float),
    vol.Optional(CONF_MAX): vol.Coerce(float),
    vol.Optional(CONF_INITIAL): vol.Coerce(float),
    vol.Optional(CONF_STEP): vol.All(vol.Coerce(float), vol.Range(min=1e-3)),
    vol.Optional(CONF_ICON): cv.icon,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_MODE): vol.In([MODE_BOX, MODE_SLIDER]),
}
UPDATE_FIELDS.update(TEMPLATE_NUMBER_UPDATE_FIELDS)  # TemplateNumber

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
                _cv_input_number,
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)
RELOAD_SERVICE_SCHEMA = vol.Schema({})
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up an input slider."""
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

    collection.StorageCollectionWebsocket(
        storage_collection, DOMAIN, DOMAIN, CREATE_FIELDS, UPDATE_FIELDS
    ).async_setup(hass)

    collection.attach_entity_registry_cleaner(hass, DOMAIN, DOMAIN, yaml_collection)
    collection.attach_entity_registry_cleaner(hass, DOMAIN, DOMAIN, storage_collection)

    async def reload_service_handler(service_call: ServiceCallType) -> None:
        """Reload yaml entities."""
        conf = await component.async_prepare_reload(skip_reset=True)
        if conf is None:
            conf = {DOMAIN: {}}
        await yaml_collection.async_load(
            [{CONF_ID: id_, **conf} for id_, conf in conf.get(DOMAIN, {}).items()]
        )

    homeassistant.helpers.service.async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_service_handler,
        schema=RELOAD_SERVICE_SCHEMA,
    )

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


class NumberStorageCollection(collection.StorageCollection):
    """Input storage based collection."""

    CREATE_SCHEMA = vol.Schema(vol.All(CREATE_FIELDS, _cv_input_number))
    UPDATE_SCHEMA = vol.Schema(UPDATE_FIELDS)

    async def _process_create_data(self, data: typing.Dict) -> typing.Dict:
        """Validate the config is valid."""
        return self.CREATE_SCHEMA(data)

    @callback
    def _get_suggested_id(self, info: typing.Dict) -> str:
        """Suggest an ID based on the config."""
        return info[CONF_NAME]

    async def _update_data(self, data: dict, update_data: typing.Dict) -> typing.Dict:
        """Return a new updated data object."""
        update_data = self.UPDATE_SCHEMA(update_data)
        return _cv_input_number({**data, **update_data})


class InputNumber(RestoreEntity):
    """Representation of a slider."""

    def __init__(self, config: typing.Dict, hass: Optional[HomeAssistantType] = None):
        """Initialize an input number."""
        self._config = config
        self.editable = True
        self._current_value = config.get(CONF_INITIAL)

    @classmethod
    def from_yaml(cls, config: typing.Dict) -> "InputNumber":
        """Return entity instance initialized from yaml storage."""
        input_num = cls(config)
        input_num.entity_id = f"{DOMAIN}.{config[CONF_ID]}"
        input_num.editable = False
        return input_num

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def _minimum(self) -> float:
        """Return minimum allowed value."""
        return self._config[CONF_MIN]

    @property
    def _maximum(self) -> float:
        """Return maximum allowed value."""
        return self._config[CONF_MAX]

    @property
    def name(self):
        """Return the name of the input slider."""
        return self._config.get(CONF_NAME)

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._config.get(CONF_ICON)

    @property
    def state(self):
        """Return the state of the component."""
        return self._current_value

    @property
    def _step(self) -> int:
        """Return entity's increment/decrement step."""
        return self._config[CONF_STEP]

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    @property
    def unique_id(self) -> typing.Optional[str]:
        """Return unique id of the entity."""
        return self._config[CONF_ID]

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_INITIAL: self._config.get(CONF_INITIAL),
            ATTR_EDITABLE: self.editable,
            ATTR_MIN: self._minimum,
            ATTR_MAX: self._maximum,
            ATTR_STEP: self._step,
            ATTR_MODE: self._config[CONF_MODE],
        }

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
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
        self.async_write_ha_state()

    async def async_increment(self):
        """Increment value."""
        await self.async_set_value(min(self._current_value + self._step, self._maximum))

    async def async_decrement(self):
        """Decrement value."""
        await self.async_set_value(max(self._current_value - self._step, self._minimum))

    async def async_update_config(self, config: typing.Dict) -> None:
        """Handle when the config is updated."""
        self._config = config
        # just in case min/max values changed
        self._current_value = min(self._current_value, self._maximum)
        self._current_value = max(self._current_value, self._minimum)
        self.async_write_ha_state()

    # TemplateNumber
    async def async_set_value_no_script(self, value):
        """Set new value."""
        await InputNumber.async_set_value(self, value)


class TemplateNumber(InputNumber):
    """Representation of a slider."""

    def __init__(self, config: typing.Dict, hass: Optional[HomeAssistantType] = None):
        """Initialize an input number."""
        super().__init__(config)
        self._entities = config.get(CONF_ENTITY_ID, set())
        self.hass = hass if config.get(CONF_SET_VALUE_SCRIPT) is not None else None

        # template
        self._value_template = config.get(CONF_VALUE_TEMPLATE)
        if self._value_template is not None:
            self._value_template.hass = self.hass

        # icon template
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
        await super().async_added_to_hass()

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
                self._config[CONF_ICON] = self._icon_template.async_render()
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
