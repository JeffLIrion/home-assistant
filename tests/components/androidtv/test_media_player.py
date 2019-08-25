"""The tests for the androidtv platform."""
import logging
import unittest
from unittest.mock import patch

# from homeassistant.setup import setup_component
from homeassistant.components.androidtv.media_player import AndroidTVDevice, setup

#    setup_platform,

# import homeassistant.components.media_player as mp
# from homeassistant.components.yamaha import media_player as yamaha
# from tests.common import get_test_home_assistant

from socket import error as socket_error


_LOGGER = logging.getLogger(__name__)


RECONNECT_LOGS = [
    "ERROR:homeassistant.components.androidtv.media_player:Failed to execute an ADB command. ADB connection re-establishing attempt in the next update. Error: ",
    "WARNING:androidtv.basetv:Couldn't connect to host 127.0.0.1:5555, error: Timed out trying to connect to ADB device.",
]


def connect_device_success(self, *args, **kwargs):
    """TODO."""
    return self


def connect_device_fail(self, *args, **kwargs):
    """TODO."""
    raise socket_error


def connect_server_fail(self, *args, **kwargs):
    """TODO."""
    raise Exception


def connect_success(self, always_log_errors=False):
    """Mimic the `AndroidTV` / `FireTV` connect method."""
    self._adb = True
    self._adb_device = True
    self._available = True
    return self._available


def connect_fail(self, always_log_errors=False):
    """Mimic the `AndroidTV` / `FireTV` connect method."""
    self._adb = False
    self._adb_device = False
    self._available = False
    return self._available


"""def adb_shell(self, cmd):
    pass"""


def adb_shell_python_adb_error(self, cmd):
    """Raise an error that is among those caught for the Python ADB implementation."""
    raise AttributeError


def adb_shell_adb_server_error(self, cmd):
    """Raise an error that is among those caught for the ADB server implementation."""
    raise ConnectionResetError


'''def _create_zone_mock(name, url):
    zone = MagicMock()
    zone.ctrl_url = url
    zone.zone = name
    return zone


class FakeYamahaDevice:
    """A fake Yamaha device."""

    def __init__(self, ctrl_url, name, zones=None):
        """Initialize the fake Yamaha device."""
        self.ctrl_url = ctrl_url
        self.name = name
        self.zones = zones or []

    def zone_controllers(self):
        """Return controllers for all available zones."""
        return self.zones'''

CONFIG_PYTHON_ADB = {
    "name": "androidtv",
    "device_class": "androidtv",
    "host": "127.0.0.1",
    "port": 5555,
    "state_detection_rules": {},
    "apps": {},
}


class AdbAvailable:
    """A class with ADB shell methods that can be patched with return values."""

    def shell(self, cmd):
        """Send an ADB shell command (ADB server implementation)."""
        pass

    def Shell(self, cmd):
        """Send an ADB shell command (Python ADB implementation)."""
        pass


class AdbUnavailable:
    """A class with ADB shell methods that raise errors."""

    def shell(self, cmd):
        """Raise an error that pertains to the Python ADB implementation."""
        raise ConnectionResetError

    def Shell(self, cmd):
        """Raise an error that pertains to the ADB server implementation."""
        raise AttributeError


class TestAndroidTV(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up an `AndroidTVDevice` media player."""
        with patch(
            "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_success
        ), patch("adb.adb_commands.AdbCommands.Shell", return_value=""):
            atv = setup("127.0.0.1:5555", device_class="androidtv")
            self.atv = AndroidTVDevice(atv, "Fake Android TV", {}, None, None)

    def test_dummy(self):
        """Pass."""
        self.assertTrue(True)

    def test_reconnect(self):
        """Test that the error and reconnection attempts are logged correctly.

        "Handles device/service unavailable. Log a warning once when
        unavailable, log once when reconnected."

        https://developers.home-assistant.io/docs/en/integration_quality_scale_index.html
        """
        with self.assertLogs(level=logging.WARNING) as logs:
            with patch(
                "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_fail
            ), patch("adb.adb_commands.AdbCommands.Shell", adb_shell_python_adb_error):
                for _ in range(5):
                    self.atv.update()

        assert len(logs.output) == 2
        assert logs.output[0].startswith("ERROR")
        assert logs.output[1].startswith("WARNING")

        with self.assertLogs(level=logging.DEBUG) as logs:
            with patch(
                "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_success
            ), patch("adb.adb_commands.AdbCommands.Shell", return_value=""):
                for _ in range(1):
                    self.atv.update()

        assert (
            "ADB connection to {} successfully established".format(self.atv.aftv.host)
            in logs.output[0]
        )


class TestAndroidTVServer(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up an `AndroidTVDevice` media player."""
        with patch(
            "adb_messenger.client.Client.device", return_value=AdbAvailable()
        ), patch("{}.AdbAvailable.shell".format(__name__), return_value=""), patch(
            "androidtv.basetv.BaseTV.available", return_value=True
        ):
            atv = setup(
                "127.0.0.1:5555", adb_server_ip="127.0.0.1", device_class="androidtv"
            )
            self.atv = AndroidTVDevice(atv, "Fake Android TV", {}, None, None)
            assert self.atv.available
            assert self.atv.aftv.available

    def test_dummy(self):
        """Pass."""
        self.assertTrue(True)

    '''def test_reconnect(self):
        """Test that the error and reconnection attempts are logged correctly.

        "Handles device/service unavailable. Log a warning once when
        unavailable, log once when reconnected."

        https://developers.home-assistant.io/docs/en/integration_quality_scale_index.html
        """
        with self.assertLogs(level=logging.WARNING) as logs:
            with patch("adb_messenger.client.Client.device", return_value=AdbUnavailable()), patch("{}.AdbAvailable.shell".format(__name__), adb_shell_adb_server_error):
                for _ in range(3):
                    self.atv.update()
                    assert not self.atv.available
                    assert not self.atv.aftv.available

        _LOGGER.critical(logs.output)
        assert len(logs.output) == 2
        assert logs.output[0].startswith("ERROR")
        assert logs.output[1].startswith("WARNING")

        with self.assertLogs(level=logging.DEBUG) as logs:
            with patch("adb_messenger.client.Client.device", return_value=AdbAvailable()):#, patch("{}.shell".format(__name__), return_value=""):
                self.atv.update()

        assert "ADB connection to {} successfully established".format(self.atv.aftv.host) in logs.output[0]'''


'''class TestAndroidTV2(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        # self.main_zone = _create_zone_mock("Main zone", "http://main")
        # self.device = FakeYamahaDevice(
        #    "http://receiver", "Receiver", zones=[self.main_zone]
        # )

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    def test_dummy(self):
        """Pass."""
        self.assertTrue(True)

    def test_setup_platform(self):
        """Setup."""
        with patch("androidtv.basetv.BaseTV.connect", connect), patch(
            "androidtv.basetv.BaseTV._adb_shell_python_adb", return_value=None
        ):
            add_entities = Mock()
            setup_platform(self.hass, CONFIG_PYTHON_ADB, add_entities)

    def test_reconnect(self):
        """Setup."""
        with patch("androidtv.basetv.BaseTV.connect", connect), patch(
            "androidtv.basetv.BaseTV._adb_shell_python_adb", return_value=None
        ):
            add_entities = Mock()
            setup_platform(self.hass, CONFIG_PYTHON_ADB, add_entities)

        with patch("androidtv.basetv.BaseTV.connect", connect_fail), patch(
            "androidtv.basetv.BaseTV._adb_shell_python_adb", adb_shell_python_adb_error
        ):
            for _ in range(3):
                pass
                # self.hass.services.call("homeassistant", "update_entity", {"entity_id": "media_player.androidtv"})

    def enable_output(self, port, enabled):
        """Enable output on a specific port."""
        data = {
            "entity_id": "media_player.yamaha_receiver_main_zone",
            "port": port,
            "enabled": enabled,
        }

        self.hass.services.call(yamaha.DOMAIN, yamaha.SERVICE_ENABLE_OUTPUT, data, True)

    def create_receiver(self, mock_rxv):
        """Create a mocked receiver."""
        mock_rxv.return_value = self.device

        config = {"media_player": {"platform": "yamaha", "host": "127.0.0.1"}}

        assert setup_component(self.hass, mp.DOMAIN, config)

    @patch("rxv.RXV")
    def test_enable_output(self, mock_rxv):
        """Test enabling and disabling outputs."""
        self.create_receiver(mock_rxv)

        self.enable_output("hdmi1", True)
        self.main_zone.enable_output.assert_called_with("hdmi1", True)

        self.enable_output("hdmi2", False)
        self.main_zone.enable_output.assert_called_with("hdmi2", False)'''
