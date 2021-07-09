"""wyzesense integration.

v0.0.7

"""

# pylint: skip-file

import logging
from os import path
import subprocess

from retry import retry
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_MOTION,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_STATE,
    CONF_DEVICE,
    DEVICE_CLASS_TIMESTAMP,
    EVENT_HOMEASSISTANT_STOP,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

from .wyzesense_custom import *  # noqa: F403

DOMAIN = "wyzesense"

ATTR_MAC = "mac"
ATTR_RSSI = "rssi"
ATTR_AVAILABLE = "available"
CONF_INITIAL_STATE = "initial_state"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICE, default="auto"): cv.string,
        vol.Optional(CONF_INITIAL_STATE, default={}): vol.Schema(
            {cv.string: vol.In(["on", "off"])}
        ),
    }
)

SERVICE_SCAN = "scan"
SERVICE_REMOVE = "remove"

SERVICE_SCAN_SCHEMA = vol.Schema({})

SERVICE_REMOVE_SCHEMA = vol.Schema({vol.Required(ATTR_MAC): cv.string})

_LOGGER = logging.getLogger(__name__)


def findDongle():  # noqa: D103
    df = (
        subprocess.check_output(["ls", "-la", "/sys/class/hidraw"])
        .decode("utf-8")
        .lower()
    )
    for line in df.split("\n"):
        if "e024" in line and "1a86" in line:
            for w in line.split(" "):
                if "hidraw" in w:
                    return "/dev/%s" % w


def setup_platform(hass, config, add_entites, discovery_info=None):  # noqa: D103
    if config[CONF_DEVICE].lower() == "auto":
        config[CONF_DEVICE] = findDongle()
    _LOGGER.debug("WYZESENSE v0.0.7")
    _LOGGER.debug("Attempting to open connection to hub at " + config[CONF_DEVICE])

    forced_initial_states = config[CONF_INITIAL_STATE]
    entities = {}

    def on_event(ws, event):
        if event.Type == "state":
            (sensor_type, sensor_state, sensor_battery, sensor_signal) = event.Data
            data = {
                ATTR_AVAILABLE: True,
                ATTR_MAC: event.MAC,
                ATTR_STATE: 1
                if sensor_state == "open" or sensor_state == "active"
                else 0,
                ATTR_DEVICE_CLASS: DEVICE_CLASS_MOTION
                if sensor_type == "motion"
                else DEVICE_CLASS_DOOR,
                DEVICE_CLASS_TIMESTAMP: event.Timestamp.isoformat(),
                ATTR_RSSI: sensor_signal * -1,
                ATTR_BATTERY_LEVEL: sensor_battery,
            }

            _LOGGER.debug(data)

            if event.MAC not in entities:
                new_entity = WyzeSensor(data)
                entities[event.MAC] = new_entity
                add_entites([new_entity])
                f = open(".storage/wyze_sensors.txt", "a")
                f.write(event.MAC + "\r\n")
            else:
                entities[event.MAC]._data = data
                entities[event.MAC].schedule_update_ha_state()

    @retry(TimeoutError, tries=10, delay=1, logger=_LOGGER)
    def beginConn():
        return Open(config[CONF_DEVICE], on_event)  # noqa: F405

    ws = beginConn()

    result = []

    if path.exists(".storage/wyze_sensors.txt"):
        sensor_file = open(".storage/wyze_sensors.txt")
        result = sensor_file.readlines()
        sensor_file.close()

    _LOGGER.debug("%d Sensors Loaded from config" % len(result))

    for mac in result:
        _LOGGER.debug("Registering Sensor Entity: %s" % mac)

        mac = mac.strip()

        if not len(mac) == 8:
            _LOGGER.debug("Ignoring %s, Invalid length for MAC" % mac)
            continue

        initial_state = forced_initial_states.get(mac)

        data = {ATTR_AVAILABLE: False, ATTR_MAC: mac, ATTR_STATE: 0}

        if mac not in entities:
            new_entity = WyzeSensor(
                data, should_restore=True, override_restore_state=initial_state
            )
            entities[mac] = new_entity
            add_entites([new_entity])

    # Configure Destructor
    def on_shutdown(event):
        _LOGGER.debug("Closing connection to hub")
        ws.Stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, on_shutdown)

    # Configure Service
    def on_scan(call):
        result = ws.Scan()
        if result:
            notification = (
                "Sensor found and added as: binary_sensor.wyzesense_%s (unless you have customized the entity id prior).<br/>To add more sensors, call wyzesense.scan again.<br/><br/>More Info: type=%d, version=%d"
                % result
            )
            hass.components.persistent_notification.create(notification, DOMAIN)
            _LOGGER.debug(notification)
        else:
            notification = "Scan completed with no sensor found."
            hass.components.persistent_notification.create(notification, DOMAIN)
            _LOGGER.debug(notification)

    def on_remove(call):
        mac = call.data.get(ATTR_MAC).upper()
        if entities.get(mac):
            ws.Delete(mac)
            toDelete = entities[mac]
            hass.add_job(toDelete.async_remove)
            del entities[mac]
            notification = "Successfully Removed Sensor: %s" % mac
            hass.components.persistent_notification.create(notification, DOMAIN)
            _LOGGER.debug(notification)
        else:
            notification = "No sensor with mac %s found to remove" % mac
            hass.components.persistent_notification.create(notification, DOMAIN)
            _LOGGER.debug(notification)

    hass.services.register(DOMAIN, SERVICE_SCAN, on_scan, SERVICE_SCAN_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_REMOVE, on_remove, SERVICE_REMOVE_SCHEMA)


class WyzeSensor(BinarySensorEntity, RestoreEntity):
    """Class to hold Hue Sensor basic info."""

    def __init__(self, data, should_restore=False, override_restore_state=None):
        """Initialize the sensor object."""
        _LOGGER.debug(data)
        self._data = data
        self._should_restore = should_restore
        self._override_restore_state = override_restore_state

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        if self._should_restore:

            last_state = await self.async_get_last_state()

            if last_state is not None:
                actual_state = last_state.state

                if self._override_restore_state is not None:
                    actual_state = self._override_restore_state

                self._data = {
                    ATTR_STATE: 1 if actual_state == "on" else 0,
                    ATTR_AVAILABLE: False,
                    **last_state.attributes,
                }

    @property
    def assumed_state(self):  # noqa: D102
        return not self._data[ATTR_AVAILABLE]

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def unique_id(self):  # noqa: D102
        return self._data[ATTR_MAC]

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._data[ATTR_STATE]

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._data[ATTR_DEVICE_CLASS] if self._data[ATTR_AVAILABLE] else None

    @property
    def device_state_attributes(self):
        """Attributes."""
        attributes = self._data.copy()
        del attributes[ATTR_STATE]
        del attributes[ATTR_AVAILABLE]

        return attributes
