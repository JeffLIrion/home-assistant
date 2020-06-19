"""Define patches used for androidtv tests."""

from tests.async_mock import mock_open, patch

KEY_PYTHON = "python"
KEY_SERVER = "server"

ADB_DEVICE_TCP_ASYNC_FAKE = "AdbDeviceTcpAsyncFake"
CLIENT_FAKE_SUCCESS = "ClientFakeSuccess"
CLIENT_FAKE_FAIL = "ClientFakeFail"
DEVICE_FAKE = "DeviceFake"


class AdbDeviceTcpAsyncFake:
    """A fake of the `adb_shell.adb_device_async.AdbDeviceTcpAsync` class."""

    def __init__(self, *args, **kwargs):
        """Initialize a fake `adb_shell.adb_device_async.AdbDeviceTcpAsync` instance."""
        self.available = False

    async def close(self):
        """Close the socket connection."""
        self.available = False

    async def connect(self, *args, **kwargs):
        """Try to connect to a device."""
        raise NotImplementedError

    async def push(self, *args, **kwargs):
        """Push a file to the device."""

    async def pull(self, *args, **kwargs):
        """Pull a file from the device."""

    async def shell(self, cmd, *args, **kwargs):
        """Send an ADB shell command."""
        return None


class ClientFakeSuccess:
    """A fake of the `ppadb.client.Client` class when the connection and shell commands succeed."""

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
    """A fake of the `ppadb.client.Client` class when the connection and shell commands fail."""

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
    """A fake of the `ppadb.device.Device` class."""

    def __init__(self, host):
        """Initialize a `DeviceFake` instance."""
        self.host = host

    def get_serial_no(self):
        """Get the serial number for the device (IP:PORT)."""
        return self.host

    def push(self, *args, **kwargs):
        """Push a file to the device."""

    def pull(self, *args, **kwargs):
        """Pull a file from the device."""

    def shell(self, cmd):
        """Send an ADB shell command."""
        raise NotImplementedError

    def screencap(self):
        """Take a screencap."""
        raise NotImplementedError


def patch_connect(success):
    """Mock the `adb_shell.adb_device_async.AdbDeviceTcpAsync` and `ppadb.client.Client` classes."""

    async def connect_success_python(self, *args, **kwargs):
        """Mock the `AdbDeviceTcpAsyncFake.connect` method when it succeeds."""
        self.available = True

    async def connect_fail_python(self, *args, **kwargs):
        """Mock the `AdbDeviceTcpAsyncFake.connect` method when it fails."""
        raise OSError

    if success:
        return {
            KEY_PYTHON: patch(
                f"{__name__}.{ADB_DEVICE_TCP_ASYNC_FAKE}.connect",
                connect_success_python,
            ),
            KEY_SERVER: patch(
                "androidtv.adb_manager.adb_manager_async.Client", ClientFakeSuccess
            ),
        }
    return {
        KEY_PYTHON: patch(
            f"{__name__}.{ADB_DEVICE_TCP_ASYNC_FAKE}.connect", connect_fail_python
        ),
        KEY_SERVER: patch(
            "androidtv.adb_manager.adb_manager_async.Client", ClientFakeFail
        ),
    }


def patch_shell(response=None, error=False):
    """Mock the `AdbDeviceTcpAsyncFake.shell` and `DeviceFake.shell` methods."""

    async def shell_success(self, cmd, *args, **kwargs):
        """Mock the `AdbDeviceTcpAsyncFake.shell` and `DeviceFake.shell` methods when they are successful."""
        self.shell_cmd = cmd
        return response

    def delete_shell_success(self, cmd, *args, **kwargs):
        """Mock the `AdbDeviceTcpAsyncFake.shell` and `DeviceFake.shell` methods when they are successful."""
        self.shell_cmd = cmd
        return response

    async def shell_fail_python(self, cmd, *args, **kwargs):
        """Mock the `AdbDeviceTcpAsyncFake.shell` method when it fails."""
        self.shell_cmd = cmd
        raise AttributeError

    def shell_fail_server(self, cmd):
        """Mock the `DeviceFake.shell` method when it fails."""
        self.shell_cmd = cmd
        raise ConnectionResetError

    if not error:
        return {
            KEY_PYTHON: patch(
                f"{__name__}.{ADB_DEVICE_TCP_ASYNC_FAKE}.shell", shell_success
            ),
            KEY_SERVER: patch(f"{__name__}.{DEVICE_FAKE}.shell", delete_shell_success),
        }
    return {
        KEY_PYTHON: patch(
            f"{__name__}.{ADB_DEVICE_TCP_ASYNC_FAKE}.shell", shell_fail_python
        ),
        KEY_SERVER: patch(f"{__name__}.{DEVICE_FAKE}.shell", shell_fail_server),
    }


PATCH_ADB_DEVICE_TCP = patch(
    "androidtv.adb_manager.adb_manager_async.AdbDeviceTcpAsync", AdbDeviceTcpAsyncFake
)
PATCH_ANDROIDTV_OPEN = patch(
    "androidtv.adb_manager.adb_manager_async.open", mock_open()
)
PATCH_KEYGEN = patch("homeassistant.components.androidtv.media_player.keygen")
PATCH_SIGNER = patch("androidtv.adb_manager.adb_manager_async.PythonRSASigner")


def isfile(filepath):
    """Mock `os.path.isfile`."""
    return filepath.endswith("adbkey")


PATCH_ISFILE = patch("os.path.isfile", isfile)
PATCH_ACCESS = patch("os.access", return_value=True)


def patch_firetv_update(state, current_app, running_apps):
    """Patch the `FireTV.update()` method."""
    return patch(
        "androidtv.firetv.firetv_async.FireTVAsync.update",
        return_value=(state, current_app, running_apps),
    )


def patch_androidtv_update(
    state, current_app, running_apps, device, is_volume_muted, volume_level
):
    """Patch the `AndroidTV.update()` method."""
    return patch(
        "androidtv.androidtv.androidtv_async.AndroidTVAsync.update",
        return_value=(
            state,
            current_app,
            running_apps,
            device,
            is_volume_muted,
            volume_level,
        ),
    )


PATCH_LAUNCH_APP = patch("androidtv.basetv.basetv_async.BaseTVAsync.launch_app")
PATCH_STOP_APP = patch("androidtv.basetv.basetv_async.BaseTVAsync.stop_app")
