import logging
import threading
import time
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

            payload = {
                "type": "observation",
                "schema_version": "1.0",
                "hypothesis_id": None,  # Generic network traffic doesn't have a specific hypothesis yet
                "hook": "mitmproxy.http",
                "captured_at_ms": captured_at_ms,
                "thread_id": None,
                "thread_name": None,
                "caller_package": None,  # Cannot easily determine package from raw IP traffic
                "args": {
                    "method": req.method,
                    "url": req.url,
                    "host": req.host,
                    "headers": dict(req.headers),
                    "request_body_size": len(req.content) if req.content else 0,
                },
                "return_value": {
                    "status_code": res.status_code if res else 0,
                    "response_size": len(res.content) if res and res.content else 0,
                    "headers": dict(res.headers) if res else {},
                },
                "exception": None,
                "session_id": self.submission_id,
            }
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
            self.runner_thread = threading.Thread(target=self.master.run, daemon=True)
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
