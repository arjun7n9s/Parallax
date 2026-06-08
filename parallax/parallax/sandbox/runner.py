import asyncio
import logging
from typing import List, Optional

from parallax.analysis.dynamic.frida_runner import FridaRunner, FridaRunnerError
from parallax.analysis.dynamic.mitmproxy_runner import MitmproxyRunner, MitmproxyRunnerError

logger = logging.getLogger(__name__)


class SandboxRunnerError(Exception):
    pass


class SandboxRunner:
    """
    Orchestrates the dynamic analysis lifecycle.
    This includes coordinating the emulator, Mitmproxy, and Frida for a single submission.
    """

    def __init__(
        self, submission_id: str, package_name: str, apk_path: str, proxy_port: int = 8080
    ):
        self.submission_id = submission_id
        self.package_name = package_name
        self.apk_path = apk_path
        self.proxy_port = proxy_port

        self.mitm_runner: Optional[MitmproxyRunner] = None
        self.frida_runner: Optional[FridaRunner] = None

        self.observations: List[dict] = []

    def _on_frida_message(self, payload: dict, data: bytes):
        """Callback for Frida observations"""
        self.observations.append(payload)
        logger.debug(f"Captured Frida observation for {self.package_name}: {payload.get('hook')}")

    def _on_mitm_flow(self, payload: dict):
        """Callback for Mitmproxy flows"""
        self.observations.append(payload)
        logger.debug(
            f"Captured Mitmproxy flow for {self.package_name}: {payload['args'].get('url')}"
        )

    async def run_analysis(self, frida_script: str, timeout_seconds: int = 60) -> List[dict]:
        """
        Executes the dynamic analysis lifecycle:
        1. Start mitmproxy
        2. Spawn frida and run script
        3. Wait for timeout
        4. Shutdown and return all collected observations
        """
        logger.info(
            f"Starting Sandbox run for {self.package_name} (Submission {self.submission_id})"
        )

        self.mitm_runner = MitmproxyRunner(
            submission_id=self.submission_id,
            listen_port=self.proxy_port,
            on_flow_callback=self._on_mitm_flow,
        )
        self.frida_runner = FridaRunner(
            package_name=self.package_name,
            script_content=frida_script,
            on_message_callback=self._on_frida_message,
        )

        try:
            # Start proxy in background
            await self.mitm_runner.start()

            # Make sure emulator has the proxy configured (in a real prod environment,
            # the emulator would already be routed through the mitmproxy container's port)

            # Start Frida and wait for the execution timeout
            try:
                await asyncio.wait_for(
                    self.frida_runner.run_async(timeout_seconds=timeout_seconds),
                    timeout=timeout_seconds + 30,  # 30s buffer
                )
            except asyncio.TimeoutError:
                raise SandboxRunnerError("Frida execution exceeded timeout")

        except FridaRunnerError as e:
            logger.error(f"Frida error during sandbox run: {e}")
            raise SandboxRunnerError(f"Sandbox frida execution failed: {e}")
        except MitmproxyRunnerError as e:
            logger.error(f"Mitmproxy error during sandbox run: {e}")
            raise SandboxRunnerError(f"Sandbox proxy execution failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in sandbox run: {e}")
            raise SandboxRunnerError(f"Sandbox run failed: {e}")
        finally:
            # Clean up proxy
            if self.mitm_runner:
                await self.mitm_runner.stop()

        logger.info(
            f"Completed Sandbox run for {self.package_name}. Collected {len(self.observations)} observations."
        )
        return self.observations
