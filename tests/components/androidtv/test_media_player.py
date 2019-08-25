"""The tests for the androidtv platform."""
import logging
from socket import error as socket_error
import unittest
from unittest.mock import patch

from homeassistant.components.androidtv.media_player import (
    AndroidTVDevice,
    FireTVDevice,
    setup,
)


def connect_device_success(self, *args, **kwargs):
    """TODO."""
    return self


def connect_device_fail(self, *args, **kwargs):
    """TODO."""
    raise socket_error


def adb_shell_python_adb_error(self, cmd):
    """Raise an error that is among those caught for the Python ADB implementation."""
    raise AttributeError


def adb_shell_adb_server_error(self, cmd):
    """Raise an error that is among those caught for the ADB server implementation."""
    raise ConnectionResetError


class AdbAvailable:
    """A class with ADB shell methods that can be patched with return values."""

    def shell(self, cmd):
        """Send an ADB shell command (ADB server implementation)."""
        pass


class AdbUnavailable:
    """A class with ADB shell methods that raise errors."""

    def __bool__(self):
        """Return `False` to indicate that the ADB connection is unavailable."""
        return False

    def shell(self, cmd):
        """Raise an error that pertains to the Python ADB implementation."""
        raise ConnectionResetError


class TestAndroidTVPythonImplementation(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up an `AndroidTVDevice` media player."""
        with patch(
            "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_success
        ), patch("adb.adb_commands.AdbCommands.Shell", return_value=""):
            aftv = setup("127.0.0.1:5555", device_class="androidtv")
            self.aftv = AndroidTVDevice(aftv, "Fake Android TV", {}, None, None)

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
                    self.aftv.update()
                    self.assertFalse(self.aftv.available)
                    self.assertIsNone(self.aftv.state)

        assert len(logs.output) == 2
        assert logs.output[0].startswith("ERROR")
        assert logs.output[1].startswith("WARNING")

        with self.assertLogs(level=logging.DEBUG) as logs:
            with patch(
                "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_success
            ), patch("adb.adb_commands.AdbCommands.Shell", return_value=""):
                for _ in range(1):
                    self.aftv.update()

        assert (
            "ADB connection to {} successfully established".format(self.aftv.aftv.host)
            in logs.output[0]
        )


class TestAndroidTVServerImplementation(unittest.TestCase):
    """Test the androidtv media player for an Android TV device."""

    def setUp(self):
        """Set up an `AndroidTVDevice` media player."""
        with patch(
            "adb_messenger.client.Client.device", return_value=AdbAvailable()
        ), patch("{}.AdbAvailable.shell".format(__name__), return_value=""), patch(
            "androidtv.basetv.BaseTV.available", return_value=True
        ):
            aftv = setup(
                "127.0.0.1:5555", adb_server_ip="127.0.0.1", device_class="androidtv"
            )
            self.aftv = AndroidTVDevice(aftv, "Fake Android TV", {}, None, None)

    def test_reconnect(self):
        """Test that the error and reconnection attempts are logged correctly.

        "Handles device/service unavailable. Log a warning once when
        unavailable, log once when reconnected."

        https://developers.home-assistant.io/docs/en/integration_quality_scale_index.html
        """
        with self.assertLogs(level=logging.WARNING) as logs:
            with patch(
                "adb_messenger.client.Client.device", return_value=AdbUnavailable()
            ), patch(
                "{}.AdbAvailable.shell".format(__name__), adb_shell_adb_server_error
            ):
                for _ in range(5):
                    self.aftv.update()
                    self.assertFalse(self.aftv.available)
                    self.assertIsNone(self.aftv.state)

        assert len(logs.output) == 2
        assert logs.output[0].startswith("ERROR")
        assert logs.output[1].startswith("WARNING")

        with self.assertLogs(level=logging.DEBUG) as logs:
            with patch(
                "adb_messenger.client.Client.device", return_value=AdbAvailable()
            ):
                self.aftv.update()

        assert (
            "ADB connection to {} via ADB server {}:{} successfully established".format(
                self.aftv.aftv.host,
                self.aftv.aftv.adb_server_ip,
                self.aftv.aftv.adb_server_port,
            )
            in logs.output[0]
        )


class TestFireTVPythonImplementation(TestAndroidTVPythonImplementation):
    """Test the androidtv media player for a Fire TV device."""

    def setUp(self):
        """Set up a `FireTVDevice` media player."""
        with patch(
            "adb.adb_commands.AdbCommands.ConnectDevice", connect_device_success
        ), patch("adb.adb_commands.AdbCommands.Shell", return_value=""):
            aftv = setup("127.0.0.1:5555", device_class="firetv")
            self.aftv = FireTVDevice(aftv, "Fake Fire TV", {}, True, None, None)


class TestFireTVServerImplementation(TestAndroidTVServerImplementation):
    """Test the androidtv media player for a Fire TV device."""

    def setUp(self):
        """Set up a `FireTVDevice` media player."""
        with patch(
            "adb_messenger.client.Client.device", return_value=AdbAvailable()
        ), patch("{}.AdbAvailable.shell".format(__name__), return_value=""), patch(
            "androidtv.basetv.BaseTV.available", return_value=True
        ):
            aftv = setup(
                "127.0.0.1:5555", adb_server_ip="127.0.0.1", device_class="firetv"
            )
            self.aftv = FireTVDevice(aftv, "Fake Fire TV", {}, True, None, None)
