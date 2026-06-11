import asyncio
import logging
import os
import time
from typing import Any, Callable, Optional

import frida

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
    ):
        self.package_name = package_name
        self.script_content = script_content
        self.on_message_callback = on_message_callback

        self.device: Optional[frida.core.Device] = None
        self.session: Optional[frida.core.Session] = None
        self.script: Optional[frida.core.Script] = None

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
            # Either hardcode a device ID passed via env var
            device_id = os.getenv("FRIDA_DEVICE_ID", "localhost:27042")

            # Try to get the device by ID first (Docker/TCP)
            try:
                self.device = frida.get_device(device_id, timeout=5)
            except frida.TimedOutError:
                # Fall back to USB if no device_id or TCP connection fails
                self.device = frida.get_usb_device(timeout=5)

            logger.info(f"Connected to Frida device: {self.device.id}")

            # Spawn the application to hook it early
            pid = self.device.spawn([self.package_name])
            logger.info(f"Spawned {self.package_name} with PID {pid}")

            # Attach and load script
            self.session = self.device.attach(pid)
            self.script = self.session.create_script(self.script_content)
            self.script.on("message", self._on_message)  # type: ignore[call-overload]
            self.script.load()

            # Resume execution
            self.device.resume(pid)
            logger.info(f"Resumed {self.package_name}. Listening for {timeout_seconds} seconds...")

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
