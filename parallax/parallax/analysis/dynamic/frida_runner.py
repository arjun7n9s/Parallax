import asyncio
import logging
import os
import time
from typing import Any, Callable, Optional

import frida

from parallax.core.config import settings
from parallax.sandbox.launcher import launch_for_instrumentation

logger = logging.getLogger(__name__)


class FridaRunnerError(Exception):
    pass


class FridaRunner:
    """
    Executes a generated JS hook script inside an Android package using Frida.
    Listens for send() payloads and forwards them via a callback.
    """

    def __init__(
        self,
        package_name: str,
        script_content: str,
        on_message_callback: Callable[[dict, Any], None],
        device_id: Optional[str] = None,
        shell: Optional[Callable[[str], str]] = None,
    ):
        self.package_name = package_name
        self.script_content = script_content
        self.on_message_callback = on_message_callback
        # Frida device id. Defaults to the configured adb serial; frida tunnels
        # to frida-server through adb for adb-connected emulators/devices.
        self.device_id = device_id or os.getenv("FRIDA_DEVICE_ID") or settings.FRIDA_DEVICE_ID
        # adb shell callable used by the launch fallback chain (icon-hiding
        # malware). Without it, only frida spawn (launcher apps) is possible.
        self.shell = shell

        self.device: Optional[frida.core.Device] = None
        self.session: Optional[frida.core.Session] = None
        self.script: Optional[frida.core.Script] = None
        # Which launch strategy actually started the app (audit signal).
        self.launch_strategy: Optional[str] = None

    def _on_message(self, message: dict, data: Any) -> None:
        """
        Internal handler for Frida messages.
        """
        if message["type"] == "send":
            try:
                payload = message.get("payload")
                if payload:
                    self.on_message_callback(payload, data)
            except Exception as e:
                logger.error(f"Error handling Frida payload: {e}", exc_info=True)
        elif message["type"] == "error":
            logger.error(f"Frida script error in {self.package_name}: {message.get('description')}")

    def run_sync(self, timeout_seconds: int = 60) -> None:
        """
        Runs the hook script synchronously for a given duration.
        """
        try:
            # Connect to the device frida exposes for the adb serial; frida
            # tunnels to frida-server over adb. (A plain get_device() on a
            # "host:27042" string raises InvalidArgumentError — it does not open
            # a TCP connection; add_remote_device would, but the adb tunnel is
            # the reliable path for an emulator.)
            try:
                self.device = frida.get_device(self.device_id, timeout=10)
            except (frida.InvalidArgumentError, frida.TimedOutError):
                # Fall back to whatever USB/adb device is present.
                self.device = frida.get_usb_device(timeout=10)

            logger.info(f"Connected to Frida device: {self.device.id}")

            # Get the app running by whatever means works (spawn for launcher
            # apps; am-start / accessibility-wake / notification-wake for
            # icon-hiding malware) and obtain its pid.
            result = launch_for_instrumentation(
                self.package_name,
                # bandit B604 false positive: this is an adb-shell callable, not
                # a subprocess shell=True invocation.
                shell=self.shell,  # type: ignore[arg-type]  # nosec B604
                frida_device=self.device,
                timeout=settings.DYNAMIC_TIMEOUT_SECONDS,
            )
            self.launch_strategy = result.strategy.value
            logger.info(
                "Instrumenting %s via %s (pid %s)",
                self.package_name,
                result.strategy.value,
                result.pid,
            )

            # Attach works regardless of how the process started.
            self.session = self.device.attach(result.pid)
            self.script = self.session.create_script(self.script_content)
            self.script.on("message", self._on_message)  # type: ignore[call-overload]
            self.script.load()

            # Only a spawned (suspended) process needs resuming. Attach paths are
            # already running, so resuming would be wrong (and there's nothing to
            # resume). We then miss the very earliest init for attach paths but
            # capture all ongoing behavior — the right trade-off for malware that
            # only runs once its service is enabled.
            if result.spawned:
                self.device.resume(result.pid)
            logger.info(f"Listening on {self.package_name} for {timeout_seconds} seconds...")

            # Wait for the specified duration to capture events
            time.sleep(timeout_seconds)

        except frida.ServerNotRunningError:
            raise FridaRunnerError("Frida server is not running on the target device.")
        except frida.ExecutableNotFoundError:
            raise FridaRunnerError(f"Package {self.package_name} not found on the device.")
        except Exception as e:
            raise FridaRunnerError(f"Failed to run Frida script: {e}")
        finally:
            self._cleanup()

    async def run_async(self, timeout_seconds: int = 60) -> None:
        """
        Runs the hook script asynchronously.
        """
        # Run the blocking Frida operations in a thread pool
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.run_sync, timeout_seconds)

    def _cleanup(self) -> None:
        """
        Clean up Frida resources.
        """
        try:
            if self.script:
                self.script.unload()
        except Exception as e:
            logger.debug(f"Error unloading Frida script: {e}")

        try:
            if self.session:
                self.session.detach()
        except Exception as e:
            logger.debug(f"Error detaching Frida session: {e}")

        logger.info(f"Cleaned up Frida resources for {self.package_name}")
