"""Support to track cast volume."""
import logging

import voluptuous as vol

from homeassistant.components.media_player.const import (
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.script import Script

_LOGGER = logging.getLogger(__name__)

# Domains
DOMAIN = "cast_volume_tracker"
ENTITY_ID_FORMAT = DOMAIN + ".{}"

# Attributes
ATTR_CAST_IS_ON = "cast_is_on"
ATTR_EXPECTED_VOLUME_LEVEL = "expected_volume_level"
ATTR_IS_VOLUME_MANAGEMENT_ENABLED = "is_volume_management_enabled"
ATTR_VALUE = "value"

# Configuration parameters
CONF_DEFAULT_VOLUME_TEMPLATE = "default_volume_template"
CONF_MEMBERS = "members"
CONF_MEMBERS_EXCLUDED_WHEN_OFF = "members_excluded_when_off"
CONF_MEMBERS_START_MUTED = "members_start_muted"
CONF_MUTE_WHEN_OFF = "mute_when_off"
CONF_OFF_SCRIPT = "off_script"
CONF_ON_SCRIPT = "on_script"
CONF_PARENTS = "parents"

# Other constants
CAST_ON_STATES = (STATE_IDLE, STATE_PAUSED, STATE_PLAYING)
MUTE_THRESHOLD = 1e-3

VALUE_MIN = 0.0
VALUE_MAX = 100.0
VALUE_STEP = 5.0


# Schemas
SERVICE_ENABLE_VOLUME_MANAGEMENT = "enable_volume_management"

SERVICE_ENABLE_VOLUME_MANAGEMENT_SCHEMA = vol.Schema(
    {vol.Required(ATTR_IS_VOLUME_MANAGEMENT_ENABLED): cv.boolean}
)

SERVICE_DEFAULT_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})

SERVICE_VOLUME_MUTE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_MEDIA_VOLUME_MUTED): cv.boolean,
    }
)

SERVICE_VOLUME_SET_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_MEDIA_VOLUME_LEVEL): vol.Coerce(float),
    }
)

SERVICE_VOLUME_DOWN_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})

SERVICE_VOLUME_UP_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})


# =========================================================================== #
#                                                                             #
#                         Cast Volume Tracker setup                           #
#                                                                             #
# =========================================================================== #
def _cv_cast_volume_tracker(cfg):
    """Configure validation helper for Cast volume tracker."""
    return cfg


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.All(
                {
                    vol.Required(CONF_NAME): cv.string,
                    vol.Optional(CONF_PARENTS, default=list()): cv.ensure_list,
                    vol.Optional(CONF_MEMBERS): cv.ensure_list,
                    vol.Optional(
                        CONF_MEMBERS_EXCLUDED_WHEN_OFF, default=list()
                    ): cv.ensure_list,
                    vol.Optional(
                        CONF_MEMBERS_START_MUTED, default=list()
                    ): cv.ensure_list,
                    vol.Optional(CONF_MUTE_WHEN_OFF, default=True): cv.boolean,
                    vol.Optional(CONF_DEFAULT_VOLUME_TEMPLATE): cv.template,
                    vol.Optional(CONF_OFF_SCRIPT): cv.SCRIPT_SCHEMA,
                    vol.Optional(CONF_ON_SCRIPT): cv.SCRIPT_SCHEMA,
                },
                _cv_cast_volume_tracker,
            )
        )
    },
    required=True,
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up a cast volume tracker."""
    hass.data.setdefault(DOMAIN, {})
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []

    # setup individual speakers first
    for object_id, cfg in sorted(
        config[DOMAIN].items(), key=lambda x: CONF_MEMBERS in x[1]
    ):
        name = cfg.get(CONF_NAME)
        off_script = cfg.get(CONF_OFF_SCRIPT)
        on_script = cfg.get(CONF_ON_SCRIPT)

        # Get the `cast_is_on`, `value`, and `is_volume_muted` attributes from the media player
        cast_state_obj = hass.states.get(f"{MEDIA_PLAYER_DOMAIN}.{object_id}")
        if cast_state_obj:
            cast_is_on = cast_state_obj.state in CAST_ON_STATES
            mp_volume_level = cast_state_obj.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)

            if mp_volume_level is not None:
                is_volume_muted = mp_volume_level < MUTE_THRESHOLD
                value = 100.0 * mp_volume_level
            else:
                is_volume_muted = cfg[CONF_MUTE_WHEN_OFF]
                value = 0.0

        # The media player is off --> the `value` and `is_volume_muted` attributes will be restored from the last state
        else:
            cast_is_on = False
            is_volume_muted = cfg[CONF_MUTE_WHEN_OFF]
            value = 0.0

        if CONF_MEMBERS not in cfg:
            cvt = CastVolumeTrackerIndividual(
                hass,
                object_id,
                name,
                cast_is_on,
                value,
                is_volume_muted,
                off_script,
                on_script,
                cfg.get(CONF_DEFAULT_VOLUME_TEMPLATE),
                cfg[CONF_PARENTS],
                cfg[CONF_MUTE_WHEN_OFF],
            )
            hass.data[DOMAIN][object_id] = cvt
            entities.append(cvt)
        else:
            cvt = CastVolumeTrackerGroup(
                hass,
                object_id,
                name,
                cast_is_on,
                value,
                is_volume_muted,
                off_script,
                on_script,
                None,
                cfg[CONF_MEMBERS],
                cfg[CONF_MEMBERS_EXCLUDED_WHEN_OFF],
                cfg[CONF_MEMBERS_START_MUTED],
            )
            hass.data[DOMAIN][object_id] = cvt
            entities.append(cvt)

    if not entities:
        return False

    for cvt in entities:
        cvt.get_members_and_parents()

    component.async_register_entity_service(
        SERVICE_VOLUME_MUTE, SERVICE_VOLUME_MUTE_SCHEMA, "async_volume_mute"
    )

    component.async_register_entity_service(
        SERVICE_VOLUME_SET, SERVICE_VOLUME_SET_SCHEMA, "async_volume_set"
    )

    component.async_register_entity_service(
        SERVICE_VOLUME_DOWN, SERVICE_VOLUME_DOWN_SCHEMA, "async_volume_down"
    )

    component.async_register_entity_service(
        SERVICE_VOLUME_UP, SERVICE_VOLUME_UP_SCHEMA, "async_volume_up"
    )

    async def async_enable_volume_management(service):
        """Enable or disable volume management."""
        is_volume_management_enabled = service.data[ATTR_IS_VOLUME_MANAGEMENT_ENABLED]
        for cvt in hass.data[DOMAIN].values():
            cvt.volume_management_enabled = is_volume_management_enabled

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_VOLUME_MANAGEMENT,
        async_enable_volume_management,
        schema=SERVICE_ENABLE_VOLUME_MANAGEMENT_SCHEMA,
    )

    await component.async_add_entities(entities)
    return True


# =========================================================================== #
#                                                                             #
#                       Cast Volume Tracker (base class)                      #
#                                                                             #
# =========================================================================== #
class CastVolumeTracker(RestoreEntity):
    """Representation of a Cast volume tracker.

    Parameters
    ----------
    hass : HomeassistantType
        `hass` instance
    object_id : str
        The associated object ID
    name : str
        The friendly name for the cast volume tracker
    cast_is_on : bool
        Whether the associated media player is on when the tracker is initialized
    value : float
        The initial value for the `CastVolumeTracker`
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted when initialized
    off_script : Script, None
        A script that is run when the associated media player turns off
    on_script : Script, None
        A script that is run when the associated media player turns on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off

    Attributes
    ----------
    _entities : list[str]
        A list with one entry: the entity ID of the associated media player
    _name : str
        The friendly name for the cast volume tracker
    _off_script : Script, None
        A script that is run when the associated media player turns off
    _on_script : Script, None
        A script that is run when the associated media player turns on
    cast_is_on : bool
        Whether the associated media player is on
    cast_is_on_prev : bool
        Whether the associated media player was on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off
    entity_id : str
        The entity ID
    hass : HomeassistantType
        `hass` instance
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted
    media_player : str
        The associated media player's entity ID
    mp_volume_level : float, None
        The volume level of the associated media player
    mp_volume_level_prev : float, None
        The previous volume level of the associated media player
    object_id : str
        The associated object ID
    value : float
        The value of the `CastVolumeTracker`
    value_prev : float
        The previous value of the `CastVolumeTracker` (not needed)
    volume_management_enabled : bool
        Whether volume management is enabled

    """

    def __init__(
        self,
        hass,
        object_id,
        name,
        cast_is_on,
        value,
        is_volume_muted,
        off_script,
        on_script,
        default_volume_template,
    ):
        """Initialize a Cast Volume Tracker."""
        self.hass = hass

        # strings
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self.object_id = object_id
        self.media_player = f"{MEDIA_PLAYER_DOMAIN}.{object_id}"
        self._entities = [f"{MEDIA_PLAYER_DOMAIN}.{object_id}"]
        self._name = name

        # state attributes - floats
        self.value = value
        self.value_prev = value
        self.mp_volume_level = None
        self.mp_volume_level_prev = None

        # state attributes - booleans
        self.cast_is_on = cast_is_on
        self.cast_is_on_prev = cast_is_on
        self.is_volume_muted = is_volume_muted

        # flags
        self.volume_management_enabled = True

        # scripts
        if off_script:
            self._off_script = Script(hass, off_script, name, DOMAIN)
        else:
            self._off_script = None

        if on_script:
            self._on_script = Script(hass, on_script, name, DOMAIN)
        else:
            self._on_script = None

        # template
        self.default_volume_template = default_volume_template
        if default_volume_template:
            self.default_volume_template.hass = hass

    # ======================================================================= #
    #                                                                         #
    #                               Properties                                #
    #                                                                         #
    # ======================================================================= #
    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the cast volume tracker."""
        return self._name

    @property
    def state(self):
        """Return the state of the component."""
        return round(self.value, 2)

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_CAST_IS_ON: self.cast_is_on,
            ATTR_VALUE: self.value,
            ATTR_MEDIA_VOLUME_LEVEL: self.mp_volume_level,
            ATTR_EXPECTED_VOLUME_LEVEL: self.expected_volume_level,
            ATTR_MEDIA_VOLUME_MUTED: self.is_volume_muted,
        }

    @property
    def equilibrium(self):
        """Whether or not the cast volume is at the expected level."""
        return self.mp_volume_level is None or round(self.mp_volume_level, 3) == round(
            self.expected_volume_level, 3
        )

    @property
    def expected_value(self):
        """Get the expected value, based on ``self.mp_volume_level`` and stuff..."""
        if self.is_volume_muted or self.mp_volume_level is None:
            return self.value
        return 100.0 * self.mp_volume_level

    @property
    def expected_volume_level(self):
        """Get the expected cast volume level, based on ``self.value`` and ``self.is_volume_muted``."""
        raise NotImplementedError

    # ======================================================================= #
    #                                                                         #
    #                               HA methods                                #
    #                                                                         #
    # ======================================================================= #
    async def async_added_to_hass(self):
        """Run when entity about to be added to hass and register callbacks."""

        @callback
        def cast_volume_tracker_state_listener(entity):
            """Handle target device state changes."""
            self.async_schedule_update_ha_state(True)

        @callback
        def cast_volume_tracker_startup(event):
            """Listen for state changes."""
            if self._entities:
                async_track_state_change_event(
                    self.hass, self._entities, cast_volume_tracker_state_listener
                )

            self.async_schedule_update_ha_state(True)

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, cast_volume_tracker_startup
        )

        await super().async_added_to_hass()

        # If the cast is off, restore the last `value` and `is_volume_muted`
        # attributes
        if self.cast_is_on:
            return

        state = await self.async_get_last_state()
        if state is None:
            return

        value = state and float(state.state)
        is_volume_muted = state.attributes.get(ATTR_MEDIA_VOLUME_MUTED)

        # Check against None because value can be 0
        if value is not None:
            self.value_prev = self.value
            self.value = value

        if is_volume_muted is not None:
            self.is_volume_muted = is_volume_muted

    async def async_volume_set(self, volume_level=None):
        """Set new volume level."""
        if volume_level is None:
            if self.default_volume_template is None:
                return

            volume_level = self.default_volume_template.async_render()
            if volume_level in ["None", "unknown"]:
                return

            volume_level = float(volume_level)

        service_args = self._volume_set(volume_level)

        for args in service_args:
            await self.hass.services.async_call(*args)

        # await self.async_update_ha_state()
        self._update()
        self.async_write_ha_state()

    async def async_volume_mute(self, is_volume_muted):
        """Mute the volume."""
        service_args = self._volume_mute(is_volume_muted)

        for args in service_args:
            await self.hass.services.async_call(*args)

        # await self.async_update_ha_state()
        self._update()
        self.async_write_ha_state()

    async def async_volume_down(self):
        """Decrease the volume."""
        service_args = self._volume_down()

        for args in service_args:
            await self.hass.services.async_call(*args)

        # await self.async_update_ha_state()
        self._update()
        self.async_write_ha_state()

    async def async_volume_up(self):
        """Increase the volume."""
        service_args = self._volume_up()

        for args in service_args:
            await self.hass.services.async_call(*args)

        # await self.async_update_ha_state()
        self._update()
        self.async_write_ha_state()

    async def async_update(self):
        """Update the state and perform any necessary service calls."""
        # Update and get arguments for service calls
        service_args = self._update()

        if not self.volume_management_enabled:
            return

        for args in service_args:
            await self.hass.services.async_call(*args)

        if self.cast_is_on_prev and not self.cast_is_on:
            if self._off_script:
                await self._off_script.async_run(context=self._context)
        elif not self.cast_is_on_prev and self.cast_is_on:
            if self._on_script:
                await self._on_script.async_run(context=self._context)

    # ======================================================================= #
    #                                                                         #
    #                             Helper methods                              #
    #                                                                         #
    # ======================================================================= #
    @staticmethod
    def cvt_volume_mute(entity_id, is_volume_muted):
        """Return arguments to be passed to the `cast_volume_tracker.volume_mute` service."""
        return [
            [
                DOMAIN,
                SERVICE_VOLUME_MUTE,
                {
                    ATTR_ENTITY_ID: [
                        ENTITY_ID_FORMAT.format(cvt.object_id) for cvt in entity_id
                    ],
                    ATTR_MEDIA_VOLUME_MUTED: is_volume_muted,
                },
            ]
        ]

    @staticmethod
    def cvt_volume_set(entity_id, volume_level=None):
        """Return arguments to be passed to the `cast_volume_tracker.volume_set` service."""
        if isinstance(entity_id, str):
            if volume_level is None:
                return [[DOMAIN, SERVICE_VOLUME_SET, {ATTR_ENTITY_ID: entity_id}]]
            return [
                [
                    DOMAIN,
                    SERVICE_VOLUME_SET,
                    {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: volume_level},
                ]
            ]

        if volume_level is None:
            return [
                [
                    DOMAIN,
                    SERVICE_VOLUME_SET,
                    {
                        ATTR_ENTITY_ID: [
                            ENTITY_ID_FORMAT.format(cvt.object_id) for cvt in entity_id
                        ],
                    },
                ]
            ]
        return [
            [
                DOMAIN,
                SERVICE_VOLUME_SET,
                {
                    ATTR_ENTITY_ID: [
                        ENTITY_ID_FORMAT.format(cvt.object_id) for cvt in entity_id
                    ],
                    ATTR_MEDIA_VOLUME_LEVEL: volume_level,
                },
            ]
        ]

    @staticmethod
    def mp_volume_set(entity_id, volume_level):
        """Return arguments to be passed to the `media_player.volume_set` service."""
        return [
            [
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: volume_level},
            ]
        ]

    def get_members_and_parents(self):
        """Fill in the `members*` attribute for groups and the `parents` attribute for individuals."""
        raise NotImplementedError

    def set_attributes(self, cast_is_on=None, value=None, is_volume_muted=None):
        """Set the attributes for the cast volume tracker."""
        if cast_is_on is not None:
            self.cast_is_on_prev = self.cast_is_on
            self.cast_is_on = cast_is_on

        if value is not None:
            self.value_prev = self.value
            self.value = value

        if is_volume_muted is not None:
            self.is_volume_muted = is_volume_muted

    def _update(self):
        """Update the cast volume tracker."""
        cast_state_obj = self.hass.states.get(self.media_player)

        # The state object could not be found or the state is unknown / unavailable
        if not cast_state_obj or cast_state_obj.state is None:
            return

        # Update the current and previous state attributes
        self.cast_is_on_prev = self.cast_is_on
        self.cast_is_on = cast_state_obj.state in CAST_ON_STATES
        self.mp_volume_level_prev = self.mp_volume_level
        self.mp_volume_level = cast_state_obj.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)

        # Track only, don't manage the volume
        if not self.volume_management_enabled:
            if self.mp_volume_level is not None:
                self.is_volume_muted = self.mp_volume_level < MUTE_THRESHOLD
            self.value_prev = self.value
            self.value = self.expected_value
            return []

        # Off -> Off
        if not self.cast_is_on_prev and not self.cast_is_on:
            return []

        # Off -> On
        if not self.cast_is_on_prev and self.cast_is_on:
            return self._update_off_to_on()

        # On -> Off
        if self.cast_is_on_prev and not self.cast_is_on:
            return self._update_on_to_off()

        # On -> On and volume changed
        if (
            self.mp_volume_level is not None
            and self.mp_volume_level is not None
            and (
                self.mp_volume_level_prev is None
                or round(self.mp_volume_level, 3) != round(self.mp_volume_level_prev, 3)
            )
        ):
            return self._update_on_to_on()

        return []

    def _update_on_to_off(self):
        raise NotImplementedError

    def _update_off_to_on(self):
        raise NotImplementedError

    def _update_on_to_on(self):
        raise NotImplementedError

    def _volume_mute(self, is_volume_muted):
        """Mute/Un-mute the volume."""
        raise NotImplementedError

    def _volume_set(self, volume_level):
        """Set the volume."""
        raise NotImplementedError

    def _volume_down(self):
        """Decrease the volume."""
        volume_level = max(self.value - VALUE_STEP, VALUE_MIN) / VALUE_MAX
        return self._volume_set(volume_level)

    def _volume_up(self):
        """Increase the volume."""
        volume_level = min(self.value + VALUE_STEP, VALUE_MAX) / VALUE_MAX
        return self._volume_set(volume_level)


# =========================================================================== #
#                                                                             #
#                         Cast Volume Tracker (group)                         #
#                                                                             #
# =========================================================================== #
class CastVolumeTrackerGroup(CastVolumeTracker):
    """A class for storing information about a Chromecast group.

    Parameters
    ----------
    hass : HomeassistantType
        `hass` instance
    object_id : str
        The associated object ID
    name : str
        The friendly name for the cast volume tracker
    cast_is_on : bool
        Whether the associated media player is on when the tracker is initialized
    value : float
        The initial value for the `CastVolumeTracker`
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted when initialized
    off_script : Script, None
        A script that is run when the associated media player turns off
    on_script : Script, None
        A script that is run when the associated media player turns on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off
    members : list[str]
        A list of the members' object IDs
    members_excluded_when_off : list[str], None
        A list of the object IDs of members whose volumes should not be used to compute the group's volume when the group is off
    members_start_muted : list[str], None
        A list of the object IDs of members that should be muted when the group is turned on

    Attributes
    ----------
    _entities : list[str]
        A list with one entry: the entity ID of the associated media player
    _name : str
        The friendly name for the cast volume tracker
    _off_script : Script, None
        A script that is run when the associated media player turns off
    _on_script : Script, None
        A script that is run when the associated media player turns on
    cast_is_on : bool
        Whether the associated media player is on
    cast_is_on_prev : bool
        Whether the associated media player was on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off
    entity_id : str
        The entity ID
    hass : HomeassistantType
        `hass` instance
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted
    media_player : str
        The associated media player's entity ID
    members : list[CastVolumeTrackerIndividual]
        A list of the members' `CastVolumeTrackerIndividual` objects
    members_when_off : list[CastVolumeTrackerIndividual]
        A list of the `CastVolumeTrackerIndividual` objects whose for members whose volumes should not be used to compute the group's volume when the group is off
    members_start_muted : list[CastVolumeTrackerIndividual]
        A list of the cast volume tracker objects for members that should be muted when the group is turned on
    members_start_unmuted : list[CastVolumeTrackerIndividual]
        A list of the cast volume tracker objects for members that should not be muted when the group is turned on
    members_with_default : list[CastVolumeTrackerIndividual]
        A list of the cast volume tracker objects for members that have default volume levels
    members_without_default : list[CastVolumeTrackerIndividual]
        A list of the cast volume tracker objects for members that do not have default volume levels
    mp_volume_level : float, None
        The volume level of the associated media player
    mp_volume_level_prev : float, None
        The previous volume level of the associated media player
    object_id : str
        The associated object ID
    value : float
        The value of the `CastVolumeTracker`
    value_prev : float
        The previous value of the `CastVolumeTracker` (not needed)
    volume_management_enabled : bool
        Whether volume management is enabled

    """

    def __init__(
        self,
        hass,
        object_id,
        name,
        cast_is_on,
        value,
        is_volume_muted,
        off_script,
        on_script,
        default_volume_template,
        members,
        members_excluded_when_off,
        members_start_muted,
    ):
        """Initialize a Cast Volume Tracker for a Chromecast group."""
        super().__init__(
            hass,
            object_id,
            name,
            cast_is_on,
            value,
            is_volume_muted,
            off_script,
            on_script,
            default_volume_template,
        )

        # group members (filled in with object IDs here; updated with the instances by `get_members_and_parents()`)
        self.members = members
        if not members_excluded_when_off:
            self.members_when_off = members
        else:
            self.members_when_off = [
                member for member in members if member not in members_excluded_when_off
            ]

        if not members_start_muted:
            self.members_start_muted = []
            self.members_start_unmuted = members
        else:
            self.members_start_muted = [
                member for member in members if member in members_start_muted
            ]
            self.members_start_unmuted = [
                member for member in members if member not in members_start_muted
            ]

        # cast volume trackers (placeholders; updated with the instances by `get_members_and_parents()`)
        self.members_with_default = []
        self.members_without_default = []

    @property
    def expected_volume_level(self):
        """Get the expected cast volume level, based on ``self.value`` and ``self.is_volume_muted``."""
        return (
            0.0
            if self.is_volume_muted
            else 0.01
            * self.value
            * sum(not member.is_volume_muted for member in self.members)
            / len(self.members)
        )

    def get_members_and_parents(self):
        """Fill in the `members*` attributes."""
        self.members = [self.hass.data[DOMAIN][member] for member in self.members]
        self.members_when_off = [
            self.hass.data[DOMAIN][member] for member in self.members_when_off
        ]
        self.members_start_muted = [
            self.hass.data[DOMAIN][member] for member in self.members_start_muted
        ]
        self.members_start_unmuted = [
            self.hass.data[DOMAIN][member] for member in self.members_start_unmuted
        ]
        self.members_with_default = [
            member for member in self.members if member.has_default_volume
        ]
        self.members_without_default = [
            member for member in self.members if not member.has_default_volume
        ]

    def _update_off_to_on(self):
        self.is_volume_muted = False
        self.value_prev = self.value
        self.value = sum([member.value for member in self.members_when_off]) / len(
            self.members_when_off
        )

        # set the `cast_is_on` and `is_volume_muted` attributes for the speakers in the group
        for member in self.members_start_unmuted:
            member.set_attributes(cast_is_on=True, is_volume_muted=False)
        for member in self.members_start_muted:
            member.set_attributes(cast_is_on=True, is_volume_muted=True)

        # 1) Set the cast volume tracker volumes
        return self.cvt_volume_set(self.members, 0.01 * self.value)

    def _update_on_to_off(self):
        self.is_volume_muted = True

        # set the `cast_is_on` and `is_volume_muted` attributes for the speakers in the group
        for member in self.members:
            member.set_attributes(
                cast_is_on=False, is_volume_muted=member.mute_when_off
            )

        # 1) Set the cast volume tracker volumes for members without default values
        # 2) Set the cast volume tracker volumes for members with default values
        return self.cvt_volume_set(
            self.members_without_default, 0.01 * self.value
        ) + self.cvt_volume_set(self.members_with_default, None)

    def _update_on_to_on(self):
        self.is_volume_muted = all([member.is_volume_muted for member in self.members])

        old_equilibrium = self.mp_volume_level_prev is None or round(
            self.mp_volume_level_prev, 3
        ) == round(self.expected_volume_level, 3)
        if not self.equilibrium:
            # if self.mp_volume_level_prev is not None and round(self.mp_volume_level_prev, 3) != round(self.expected_volume_level, 3):
            if not old_equilibrium:
                return []

        if not self.is_volume_muted:
            # CASE 1
            #   The volume is at equilibrium -> update the value.
            #
            #   EXAMPLE: the `cast_volume_tracker.volume_set` service was used
            #   to change the volume for the group
            if self.equilibrium:
                self.value_prev = self.value
                self.value = (
                    100.0
                    * self.mp_volume_level
                    * len(self.members)
                    / sum([not member.is_volume_muted for member in self.members])
                )

            # CASE 2
            #   The volume is not at equilibrium because the volume was changed
            #   for a member `CastVolumeTrackerIndividual` -> update the value.
            #
            #   EXAMPLE: the `cast_volume_tracker.volume_set` service was used
            #   to change the volume for a member
            elif any(
                round(member.value, 3) != round(self.value, 3)
                for member in self.members
            ):
                self.value_prev = self.value
                self.value = (
                    100.0
                    * self.mp_volume_level
                    * len(self.members)
                    / sum([not member.is_volume_muted for member in self.members])
                )

            # CASE 3
            #   The volume was at equilibrium but now it is not because the
            #   volume for one or more speakers changed -> update the value.
            #
            #   EXAMPLE: the `media_player.volume_set` service was used to
            #   change the volume for a member
            elif old_equilibrium:
                self.value_prev = self.value
                self.value = (
                    100.0
                    * self.mp_volume_level
                    * len(self.members)
                    / sum([not member.is_volume_muted for member in self.members])
                )

            # Prevent an infinite loop
            if (
                old_equilibrium
                and sum(not member.is_volume_muted for member in self.members) > 1
            ):
                self.mp_volume_level = self.mp_volume_level_prev

        # 1) Set the cast volume trackers
        return self.cvt_volume_set(self.members, 0.01 * self.value) * 2

    def _volume_mute(self, is_volume_muted):
        """Mute/Un-mute the volume for the group members."""
        if not self.cast_is_on:
            return []

        if is_volume_muted ^ self.is_volume_muted:
            self.set_attributes(is_volume_muted=is_volume_muted)

            # 1) Mute the cast volume trackers
            return self.cvt_volume_mute(self.members, is_volume_muted)

        return []

    def _volume_set(self, volume_level):
        """Set the volume level for the group members."""
        if not self.cast_is_on:
            off_cast_volume_trackers = [
                member for member in self.members_when_off if not member.cast_is_on
            ]

            if not off_cast_volume_trackers:
                return []

            new_value = (
                100.0 * volume_level * len(off_cast_volume_trackers)
                + sum(
                    [
                        member.value
                        for member in self.members_when_off
                        if member.cast_is_on
                    ]
                )
            ) / len(self.members_when_off)
            self.set_attributes(value=new_value)

            return self.cvt_volume_set(off_cast_volume_trackers, volume_level)

        self.set_attributes(value=100.0 * volume_level)

        # 1) Set the cast volume tracker volumes
        return self.cvt_volume_set(self.members, volume_level)


# =========================================================================== #
#                                                                             #
#                       Cast Volume Tracker (individual)                      #
#                                                                             #
# =========================================================================== #
class CastVolumeTrackerIndividual(CastVolumeTracker):
    """A class for storing information about an individual Chromecast speaker.

    Parameters
    ----------
    hass : HomeassistantType
        `hass` instance
    object_id : str
        The associated object ID
    name : str
        The friendly name for the cast volume tracker
    cast_is_on : bool
        Whether the associated media player is on when the tracker is initialized
    cast_is_on_prev : bool
        Whether the associated media player was on
    value : float
        The initial value for the `CastVolumeTracker`
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted when initialized
    off_script : Script, None
        A script that is run when the associated media player turns off
    on_script : Script, None
        A script that is run when the associated media player turns on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off
    parents : list[str]
        A list of the parents' object IDs
    mute_when_off : bool
        Whether this speaker should be muted when it is turned off

    Attributes
    ----------
    _entities : list[str]
        A list with one entry: the entity ID of the associated media player
    _name : str
        The friendly name for the cast volume tracker
    _off_script : Script, None
        A script that is run when the associated media player turns off
    _on_script : Script, None
        A script that is run when the associated media player turns on
    cast_is_on : bool
        Whether the associated media player is on
    default_volume_template : Template, None
        The volume for the media player will be set to this level when it is turned off
    entity_id : str
        The entity ID
    has_default_volume : bool
        Whether the associated `CastVolumeTrackerEntity` has a default volume template
    hass : HomeassistantType
        `hass` instance
    is_volume_muted : bool
        Whether the `CastVolumeTracker` is muted
    media_player : str
        The associated media player's entity ID
    mp_volume_level : float, None
        The volume level of the associated media player
    mp_volume_level_prev : float, None
        The previous volume level of the associated media player
    mute_when_off : bool
        Whether this speaker should be muted when it is turned off
    object_id : str
        The associated object ID
    parents : list[CastVolumeTrackerGroup]
        A list of the parents' `CastVolumeTrackerGroup` objects
    value : float
        The value of the `CastVolumeTracker`
    value_prev : float
        The previous value of the `CastVolumeTracker` (not needed)
    volume_management_enabled : bool
        Whether volume management is enabled

    """

    def __init__(
        self,
        hass,
        object_id,
        name,
        cast_is_on,
        value,
        is_volume_muted,
        off_script,
        on_script,
        default_volume_template,
        parents,
        mute_when_off,
    ):
        """Initialize a Cast Volume Tracker for an individual speaker."""
        super().__init__(
            hass,
            object_id,
            name,
            cast_is_on,
            value,
            is_volume_muted,
            off_script,
            on_script,
            default_volume_template,
        )

        # groups to which this speaker belongs (object IDs here; updated with the instances by `get_members_and_parents()`))
        if parents is None:
            self.parents = []
        else:
            self.parents = parents

        # mute the volume when this speaker turns off
        self.mute_when_off = mute_when_off

        # does this speaker have a default volume template?
        self.has_default_volume = bool(default_volume_template)

    @property
    def expected_volume_level(self):
        """Get the expected cast volume level, based on ``self.value`` and ``self.is_volume_muted``."""
        return 0.0 if self.is_volume_muted else 0.01 * self.value

    def get_members_and_parents(self):
        """Fill in the `parents`."""
        self.parents = [self.hass.data[DOMAIN][parent] for parent in self.parents]

    @property
    def parent_is_on(self):
        """Whether or not a parent group is playing."""
        return any([parent.cast_is_on for parent in self.parents])

    def _update_off_to_on(self):
        if self.parent_is_on:
            return []

        self.is_volume_muted = False

        # 1) Set the media player volume
        return self.mp_volume_set(self.media_player, self.expected_volume_level)

    def _update_on_to_off(self):
        if self.parent_is_on:
            return []

        self.is_volume_muted = self.mute_when_off

        if self.has_default_volume:
            # 1) Set the cast volume tracker volume
            return self.cvt_volume_set(self.entity_id, None)

        # 1) Set the media player volume
        return self.mp_volume_set(self.media_player, self.expected_volume_level)

    def _update_on_to_on(self):
        if self.parent_is_on:
            return []

        if not self.is_volume_muted:
            self.value_prev = self.value
            self.value = 100.0 * self.mp_volume_level

        # 1) Set the media player volume
        return self.mp_volume_set(self.media_player, self.expected_volume_level)

    def _volume_mute(self, is_volume_muted):
        """Mute/Un-mute the volume."""
        if is_volume_muted ^ self.is_volume_muted:
            self.set_attributes(is_volume_muted=is_volume_muted)

            # 1) Set the media player volume
            return self.mp_volume_set(self.media_player, self.expected_volume_level)

        return []

    def _volume_set(self, volume_level):
        """Set the volume."""
        self.set_attributes(value=100.0 * volume_level)

        # 1) Set the media player volume
        return self.mp_volume_set(self.media_player, self.expected_volume_level)
