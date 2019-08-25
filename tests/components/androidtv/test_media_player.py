"""The tests for the androidtv platform."""
import logging
import unittest
from unittest.mock import Mock, patch

# from homeassistant.setup import setup_component
from homeassistant.components.androidtv.media_player import (
    setup_platform,
    AndroidTVDevice,
    setup,
)

# import homeassistant.components.media_player as mp
# from homeassistant.components.yamaha import media_player as yamaha
from tests.common import get_test_home_assistant


_LOGGER = logging.getLogger(__name__)


def connect(self, always_log_errors=False):
    """Mimic the `AndroidTV` / `FireTV` connect method."""
    self._adb = True
    self._available = True
    return self._available


def connect_fail(self, always_log_errors=False):
    """Mimic the `AndroidTV` / `FireTV` connect method."""
    self._adb = False
    self._available = False
    return self._available


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


class TestAndroidTV(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up an `AndroidTVDevice` media player."""
        with patch("androidtv.basetv.BaseTV.connect", connect), patch(
            "androidtv.basetv.BaseTV._adb_shell_python_adb", return_value=None
        ):
            atv = setup("127.0.0.1:5555", device_class="androidtv")
            self.atv = AndroidTVDevice(atv, "Fake Android TV", {}, None, None)

    '''def test_reconnect(self):
        """Test the update method."""
        with self.assertLogs(level=logging.ERROR) as logs:
            with patch("androidtv.basetv.BaseTV.connect", connect_fail), patch("androidtv.basetv.BaseTV._adb_shell_python_adb", adb_shell_python_adb_error):
                self.atv.update()
                for _ in range(5):
                    _LOGGER.critical(self.atv.available)
                    self.atv.update()
                    self.atv.aftv.connect()
                    self.assertTrue(not self.atv.aftv.available)
                    self.assertTrue(not self.atv.available)
            with patch.object(self.atv.aftv, "connect", connect_fail),
                patch.object(self.atv.aftv, "adb_shell", adb_shell_python_adb_error):
                #with patch("androidtv.basetv.BaseTV.connect", connect_fail), patch(
                #    "androidtv.basetv.BaseTV._adb_shell_python_adb", adb_shell_python_adb_error
                #):
                for _ in range(5):
                    _LOGGER.critical(self.atv.available)
                    self.atv.update()
                    self.assertTrue(not self.atv.available)

        #self.assertEqual(logs, [])
        #self.assertTrue(False)'''


class TestAndroidTV2(unittest.TestCase):
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

    '''def enable_output(self, port, enabled):
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
