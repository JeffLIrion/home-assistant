"""The tests for the androidtv platform."""
import unittest
from unittest.mock import Mock, patch

# from homeassistant.setup import setup_component
from homeassistant.components.androidtv.media_player import setup_platform

# import homeassistant.components.media_player as mp
# from homeassistant.components.yamaha import media_player as yamaha
from tests.common import get_test_home_assistant


def connect(self):
    """Mimic the `AndroidTV` / `FireTV` connect method."""
    self._adb = True
    self._available = True
    return self._available


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
    "name": "Android TV",
    "device_class": "androidtv",
    "host": "127.0.0.1",
    "port": 5555,
    "state_detection_rules": {},
    "apps": {},
}


class TestAndroidTV(unittest.TestCase):
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
