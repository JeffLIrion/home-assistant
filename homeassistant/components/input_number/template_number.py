"""Template number functionality."""
import logging
from typing import Optional  # noqa pylint: disable=unused-import

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

_LOGGER = logging.getLogger(__name__)

CONF_SET_VALUE_SCRIPT = "set_value_script"
CONF_VALUE_CHANGED_SCRIPT = "value_changed_script"

SERVICE_SET_VALUE_NO_SCRIPT = "set_value_no_script"


TEMPLATE_NUMBER_CREATE_FIELDS = {
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    vol.Optional(CONF_SET_VALUE_SCRIPT): cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_VALUE_CHANGED_SCRIPT): cv.SCRIPT_SCHEMA,
}

TEMPLATE_NUMBER_UPDATE_FIELDS = {
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    vol.Optional(CONF_SET_VALUE_SCRIPT): cv.SCRIPT_SCHEMA,
    vol.Optional(CONF_VALUE_CHANGED_SCRIPT): cv.SCRIPT_SCHEMA,
}


def get_entity_ids(config):
    """Get the entity IDs for the templates."""
    # setup the entity ID's for the template
    template_entity_ids = set()
    value_template = config.get(CONF_VALUE_TEMPLATE)
    icon_template = config.get(CONF_ICON_TEMPLATE)

    if value_template is not None:
        temp_ids = value_template.extract_entities()
        if str(temp_ids) != MATCH_ALL:
            template_entity_ids |= set(temp_ids)

    if icon_template is not None:
        icon_ids = icon_template.extract_entities()
        if str(icon_ids) != MATCH_ALL:
            template_entity_ids |= set(icon_ids)

    return config.get(CONF_ENTITY_ID, template_entity_ids)


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
