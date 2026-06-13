"""Regression tests for the dynamic-capture plumbing bugs.

These guard the three stacked failures that made a real malware run produce
0 frida observations while looking like "the app was dormant":

  1. Frida connected via get_device("localhost:27042"), which raises
     InvalidArgumentError (it cannot open a TCP connection) instead of
     tunnelling through adb.
  2. SandboxRunner used asyncio.gather(return_exceptions=True) and never
     inspected the result, silently swallowing any frida failure.
  3. (covered by the frida 16.x pin) frida 17 dropped the bundled Java
     bridge, so every Java.perform hook failed with "Java is not defined".
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parallax.analysis.dynamic.frida_runner import FridaRunner
from parallax.core.config import settings
from parallax.sandbox.runner import SandboxRunner


# ---------------------------------------------------------- frida device wiring
class TestFridaDeviceConnection:
    def test_default_device_is_adb_serial_not_tcp(self):
        """Default must be the adb serial frida tunnels through, never the
        host:27042 TCP form that get_device() cannot open."""
        runner = FridaRunner("com.x", "//js", lambda p, d: None)
        assert runner.device_id == settings.FRIDA_DEVICE_ID
        assert runner.device_id != "localhost:27042"
        assert ":27042" not in runner.device_id

    def test_explicit_device_id_wins(self):
        runner = FridaRunner("com.x", "//js", lambda p, d: None, device_id="emulator-5554")
        assert runner.device_id == "emulator-5554"

    @patch("parallax.analysis.dynamic.frida_runner.time.sleep", return_value=None)
    @patch("parallax.analysis.dynamic.frida_runner.frida")
    def test_connects_via_get_device_with_serial(self, mock_frida, _sleep):
        """run_sync must call frida.get_device with the configured serial."""
        device = MagicMock()
        device.spawn.return_value = 1234
        device.attach.return_value = MagicMock()
        mock_frida.get_device.return_value = device

        FridaRunner("com.x", "//js", lambda p, d: None, device_id="localhost:5555").run_sync(
            timeout_seconds=0
        )

        mock_frida.get_device.assert_called_once()
        assert mock_frida.get_device.call_args[0][0] == "localhost:5555"
        device.spawn.assert_called_once_with(["com.x"])


# ----------------------------------------------------- sandbox error surfacing
class TestSandboxSurfacesFridaError:
    @pytest.mark.asyncio
    @patch("parallax.sandbox.runner.FridaRunner")
    @patch("parallax.sandbox.runner.MitmproxyRunner")
    async def test_frida_failure_is_recorded_not_swallowed(self, mock_mitm_cls, mock_frida_cls):
        """A frida failure must surface on sandbox.frida_error rather than being
        swallowed by gather(return_exceptions=True) and read as 0 observations."""
        mitm = MagicMock()
        mitm.start = AsyncMock()
        mitm.stop = AsyncMock()
        mock_mitm_cls.return_value = mitm

        frida_runner = MagicMock()
        frida_runner.run_async = AsyncMock(side_effect=RuntimeError("Java is not defined"))
        mock_frida_cls.return_value = frida_runner

        sandbox = SandboxRunner(submission_id="s1", package_name="com.x", apk_path="/x.apk")
        obs = await sandbox.run_analysis(frida_script="//js", timeout_seconds=0)

        assert sandbox.frida_error is not None
        assert "Java is not defined" in sandbox.frida_error
        assert "RuntimeError" in sandbox.frida_error
        assert obs == []  # no observations, but the failure is now visible

    @pytest.mark.asyncio
    @patch("parallax.sandbox.runner.FridaRunner")
    @patch("parallax.sandbox.runner.MitmproxyRunner")
    async def test_no_error_recorded_on_clean_run(self, mock_mitm_cls, mock_frida_cls):
        mitm = MagicMock()
        mitm.start = AsyncMock()
        mitm.stop = AsyncMock()
        mock_mitm_cls.return_value = mitm

        frida_runner = MagicMock()
        frida_runner.run_async = AsyncMock(return_value=None)
        mock_frida_cls.return_value = frida_runner

        sandbox = SandboxRunner(submission_id="s1", package_name="com.x", apk_path="/x.apk")
        # Simulate one frida observation arriving via the callback.
        sandbox._on_frida_message({"hook": "SmsManager.sendTextMessage"}, None)
        await sandbox.run_analysis(frida_script="//js", timeout_seconds=0)

        assert sandbox.frida_error is None

    @pytest.mark.asyncio
    @patch("parallax.sandbox.runner.FridaRunner")
    @patch("parallax.sandbox.runner.MitmproxyRunner")
    async def test_frida_device_id_passed_from_avd_manager(self, mock_mitm_cls, mock_frida_cls):
        mitm = MagicMock()
        mitm.start = AsyncMock()
        mitm.stop = AsyncMock()
        mock_mitm_cls.return_value = mitm
        mock_frida_cls.return_value = MagicMock(run_async=AsyncMock(return_value=None))

        avd = SimpleNamespace(device_id="localhost:5555")
        sandbox = SandboxRunner(
            submission_id="s1", package_name="com.x", apk_path="/x.apk", avd_manager=avd
        )
        await sandbox.run_analysis(frida_script="//js", timeout_seconds=0)

        # FridaRunner must be constructed with the AVD's device_id.
        assert mock_frida_cls.call_args.kwargs["device_id"] == "localhost:5555"
