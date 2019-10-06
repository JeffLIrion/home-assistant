"""Support for functionality to interact with Android TV/Fire TV devices."""

import logging
import voluptuous as vol

from homeassistant.components.androidtv.const import DOMAIN
from homeassistant.const import ATTR_COMMAND, ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SERVICE_ADB_COMMAND = "adb_command"

SERVICE_ADB_COMMAND_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids, vol.Required(ATTR_COMMAND): cv.string}
)


def setup(hass, config):
    """Set up the Android TV integration."""

    def service_adb_command(service):
        """Dispatch service calls to target entities."""
        cmd = service.data.get(ATTR_COMMAND)
        entity_id = service.data.get(ATTR_ENTITY_ID)
        target_devices = [
            dev for dev in hass.data[DOMAIN].values() if dev.entity_id in entity_id
        ]

        for target_device in target_devices:
            output = target_device.adb_command(cmd)

            # log the output, if there is any
            if output:
                _LOGGER.info(
                    "Output of command '%s' from '%s': %s",
                    cmd,
                    target_device.entity_id,
                    output,
                )

    hass.services.register(
        DOMAIN,
        SERVICE_ADB_COMMAND,
        service_adb_command,
        schema=SERVICE_ADB_COMMAND_SCHEMA,
    )

    # Return boolean to indicate that initialization was successful.
    return True
