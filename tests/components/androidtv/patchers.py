"""Define patches used for androidtv tests."""

from contextlib import contextmanager
from socket import error as socket_error
from unittest.mock import patch


class AdbDeviceFake:
    """A fake of the `adb_shell.adb_device.AdbDevice` class."""

    def __init__(self, *args, **kwargs):
        """Initialize a fake `adb_shell.adb_device.AdbDevice` instance."""
        self.available = False

    def close(self):
        """Close the socket connection."""
        self.available = False

    def connect(self, *args, **kwargs):
        """Try to connect to a device."""
        raise NotImplementedError

    def shell(self, cmd):
        """Send an ADB shell command."""
        return None


class ClientFakeSuccess:
    """A fake of the `adb_messenger.client.Client` class when the connection and shell commands succeed."""

    def __init__(self, host="127.0.0.1", port=5037):
        """Initialize a `ClientFakeSuccess` instance."""
        self._devices = []

    def devices(self):
        """Get a list of the connected devices."""
        return self._devices

    def device(self, serial):
        """Mock the `Client.device` method when the device is connected via ADB."""
        device = DeviceFake(serial)
        self._devices.append(device)
        return device


class ClientFakeFail:
    """A fake of the `adb_messenger.client.Client` class when the connection and shell commands fail."""

    def __init__(self, host="127.0.0.1", port=5037):
        """Initialize a `ClientFakeFail` instance."""
        self._devices = []

    def devices(self):
        """Get a list of the connected devices."""
        return self._devices

    def device(self, serial):
        """Mock the `Client.device` method when the device is not connected via ADB."""
        self._devices = []


class DeviceFake:
    """A fake of the `adb_messenger.device.Device` class."""

    def __init__(self, host):
        """Initialize a `DeviceFake` instance."""
        self.host = host

    def get_serial_no(self):
        """Get the serial number for the device (IP:PORT)."""
        return self.host

    def shell(self, cmd):
        """Send an ADB shell command."""
        raise NotImplementedError


def patch_connect(success):
    """Mock the `adb_shell.adb_device.AdbDevice` and `adb_messenger.client.Client` classes."""

    def connect_success_python(self, *args, **kwargs):
        """Mock the `AdbDeviceFake.connect` method when it succeeds."""
        self.available = True

    def connect_fail_python(self, *args, **kwargs):
        """Mock the `AdbDeviceFake.connect` method when it fails."""
        raise socket_error

    if success:
        return {
            "python": patch(
                f"{__name__}.AdbDeviceFake.connect", connect_success_python
            ),
            "server": patch("androidtv.adb_manager.Client", ClientFakeSuccess),
        }
    return {
        "python": patch(f"{__name__}.AdbDeviceFake.connect", connect_fail_python),
        "server": patch("androidtv.adb_manager.Client", ClientFakeFail),
    }


def patch_shell(response=None, error=False):
    """Mock the `AdbDeviceFake.shell` and `DeviceFake.shell` methods."""

    def shell_success(self, cmd):
        """Mock the `AdbDeviceFake.shell` and `DeviceFake.shell` methods when they are successful."""
        self.shell_cmd = cmd
        return response

    def shell_fail_python(self, cmd):
        """Mock the `AdbDeviceFake.shell` method when it fails."""
        self.shell_cmd = cmd
        raise AttributeError

    def shell_fail_server(self, cmd):
        """Mock the `DeviceFake.shell` method when it fails."""
        self.shell_cmd = cmd
        raise ConnectionResetError

    if not error:
        return {
            "python": patch(f"{__name__}.AdbDeviceFake.shell", shell_success),
            "server": patch(f"{__name__}.DeviceFake.shell", shell_success),
        }
    return {
        "python": patch(f"{__name__}.AdbDeviceFake.shell", shell_fail_python),
        "server": patch(f"{__name__}.DeviceFake.shell", shell_fail_server),
    }


PATCH_ADB_DEVICE = patch("androidtv.adb_manager.AdbDevice", AdbDeviceFake)


class FileReadWrite:
    """Mock an opened file that can be read and written to."""

    def __init__(self):
        """Initialize a `FileReadWrite` instance."""
        self._content = b""
        self.mode = "r"

    def read(self):
        """Read `self._content`."""
        if self.mode == "r":
            if not isinstance(self._content, str):
                return self._content.decode()
            return self._content

        if isinstance(self._content, str):
            return self._content.encode("utf-8")
        return self._content

    def write(self, content):
        """Write `self._content`."""
        self._content = content


PRIVATE_KEY = FileReadWrite()
PUBLIC_KEY = FileReadWrite()


@contextmanager
def open_priv_pub(infile, mode="r"):
    """Open a `FileReadWrite` object."""
    try:
        if infile.endswith(".pub"):
            PUBLIC_KEY.mode = mode
            yield PUBLIC_KEY
        else:
            PRIVATE_KEY.mode = mode
            yield PRIVATE_KEY
    finally:
        pass


PATCH_ANDROIDTV_OPEN = patch("androidtv.adb_manager.open", open_priv_pub)
PATCH_KEYGEN_OPEN = patch("adb_shell.auth.keygen.open", open_priv_pub)


def isfile(filepath):
    """Mock `os.path.isfile`."""
    return filepath.endswith("adbkey")


PATCH_ISFILE = patch("os.path.isfile", isfile)
PATCH_ACCESS = patch("os.access", return_value=True)
