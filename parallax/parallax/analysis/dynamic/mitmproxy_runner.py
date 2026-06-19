import asyncio
import logging
import threading
import time
from contextlib import suppress
from typing import Callable, Optional

from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

logger = logging.getLogger(__name__)


class MitmproxyRunnerError(Exception):
    pass


class TrafficInterceptorAddon:
    """
    Mitmproxy addon that intercepts flows and forwards them to a callback.
    """

    def __init__(self, submission_id: str, on_flow_callback: Callable[[dict], None]):
        self.submission_id = submission_id
        self.on_flow_callback = on_flow_callback

    def request(self, flow: http.HTTPFlow):
        # We can also capture requests, but usually capturing responses is enough
        # to get both request and response data.
        pass

    def response(self, flow: http.HTTPFlow):
        """
        Captured a completed request/response cycle.
        """
        try:
            req = flow.request
            res = flow.response

            ts = flow.request.timestamp_start
            captured_at_ms = int(ts * 1000) if ts else int(time.time() * 1000)

            args_payload: dict = {
                "method": req.method,
                "url": req.url,
                "host": req.host,
                "headers": dict(req.headers),
                "request_body_size": len(req.content) if req.content else 0,
            }
            payload = {
                "type": "observation",
                "schema_version": "1.0",
                "hypothesis_id": None,  # Generic network traffic doesn't have a specific hypothesis yet
                "hook": "mitmproxy.http",
                "captured_at_ms": captured_at_ms,
                "thread_id": None,
                "thread_name": None,
                "caller_package": None,  # Cannot easily determine package from raw IP traffic
                "args": args_payload,
                "return_value": {
                    "status_code": res.status_code if res else 0,
                    "response_size": len(res.content) if res and res.content else 0,
                    "headers": dict(res.headers) if res else {},
                },
                "exception": None,
                "session_id": self.submission_id,
            }

            # Attempt structured decoding of non-trivial protocols (DoH, gRPC,
            # WebSocket) carried over the HTTP response body.
            try:
                from parallax.analysis.dynamic.protocol_decoders import decode_payload

                content_type = res.headers.get("content-type", "") if res else ""
                body = res.content if res else b""
                decoded = decode_payload(content_type, body or b"")
                if decoded:
                    args_payload["decoded_protocol"] = decoded
            except Exception:
                pass

            self.on_flow_callback(payload)
        except Exception as e:
            logger.error(f"Error processing captured flow: {e}", exc_info=True)


class MitmproxyRunner:
    """
    Runs an embedded Mitmproxy instance to capture network traffic during dynamic analysis.
    """

    def __init__(
        self, submission_id: str, listen_port: int, on_flow_callback: Callable[[dict], None]
    ):
        self.submission_id = submission_id
        self.listen_port = listen_port
        self.on_flow_callback = on_flow_callback

        self.master: Optional[DumpMaster] = None
        self.runner_thread: Optional[threading.Thread] = None
        self.runner_error: Optional[str] = None

    def _run_master(self) -> None:
        """Drive mitmproxy's async master inside the runner thread.

        mitmproxy 11 exposes ``DumpMaster.run`` as a coroutine. Passing it
        directly to ``Thread(target=...)`` creates the coroutine but never
        awaits it, which leaves capture dead while only emitting a runtime
        warning. Each runner thread owns a short-lived event loop so the async
        master can run until ``shutdown()`` is called from ``stop``.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            if self.master is not None:
                loop.run_until_complete(self.master.run())
        except Exception as exc:  # noqa: BLE001 - surface through runner_error/logs
            self.runner_error = f"{type(exc).__name__}: {exc}"
            logger.error("Mitmproxy runner failed: %s", self.runner_error, exc_info=True)
        finally:
            loop.close()

    @staticmethod
    def _detach_mitmproxy_handlers() -> None:
        """Remove mitmproxy handlers whose event loop is already shut down.

        Embedded mitmproxy installs a root logging handler that forwards records
        to its master loop. After ``shutdown()`` that loop is closed, and a later
        Celery success log can crash the worker with ``RuntimeError: Event loop
        is closed``. Detaching only mitmproxy-owned handlers keeps PARALLAX
        logging intact while preventing a successful sandbox run from killing
        the worker.
        """
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            module = handler.__class__.__module__
            if module.startswith("mitmproxy."):
                root_logger.removeHandler(handler)
                with suppress(Exception):
                    handler.close()

    async def start(self) -> None:
        """
        Starts the mitmproxy master asynchronously.
        """
        try:
            opts = Options(listen_host="0.0.0.0", listen_port=self.listen_port)  # nosec B104
            self.master = DumpMaster(
                opts,
                with_termlog=False,
                with_dumper=False,
            )
            addon = TrafficInterceptorAddon(self.submission_id, self.on_flow_callback)
            self.master.addons.add(addon)

            logger.info(f"Starting Mitmproxy on port {self.listen_port}")
            self.runner_error = None
            self.runner_thread = threading.Thread(target=self._run_master, daemon=True)
            self.runner_thread.start()
        except Exception as e:
            raise MitmproxyRunnerError(f"Failed to start mitmproxy: {e}")

    async def stop(self) -> None:
        """
        Stops the mitmproxy master.
        """
        if self.master:
            logger.info("Shutting down Mitmproxy")
            self.master.shutdown()

        if self.runner_thread and self.runner_thread.is_alive():
            # Wait briefly for thread to finish after shutdown
            self.runner_thread.join(timeout=2.0)
            self.runner_thread = None

        self._detach_mitmproxy_handlers()
