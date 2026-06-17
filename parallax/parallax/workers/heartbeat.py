"""Liveness heartbeat for in-flight analyses.

A running stage refreshes ``hb:{submission_id}`` in Redis on a short interval
with a TTL a few times that interval. If the worker process dies, the key
expires and the orphan reaper (see ``reaper.py``) re-queues the analysis from
its current stage.

Everything here is best-effort: Redis being unavailable must never break an
analysis, so writes degrade to no-ops. The reaper treats Redis errors as
"don't reap" so a transient blip can never cause a false re-dispatch.

``stage_context`` is the single entry point workers use: it binds the
submission id + stage to the log context and runs the heartbeat for the
lifetime of the stage, cleaning both up on exit.
"""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from parallax.core.config import settings
from parallax.core.logging import bind_log_context, clear_log_context

logger = logging.getLogger(__name__)


def heartbeat_key(submission_id: str) -> str:
    return f"hb:{submission_id}"


def get_redis() -> Any:
    """A short-timeout Redis client. Separate from the Celery broker client so a
    slow/borked broker connection can't wedge the heartbeat."""
    import redis as redis_lib

    return redis_lib.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
    )


def mark_alive(client: Any, submission_id: str, stage: str, ttl: int | None = None) -> None:
    try:
        client.set(heartbeat_key(submission_id), stage, ex=ttl or settings.HEARTBEAT_TTL)
    except Exception as exc:  # noqa: BLE001 - heartbeat must never break a stage
        logger.debug("heartbeat mark_alive failed for %s: %s", submission_id, exc)


def is_alive(client: Any, submission_id: str) -> bool:
    """True if a live heartbeat exists. Raises on a connection error so the
    reaper can distinguish "no heartbeat" (orphan) from "Redis unreachable"
    (skip the whole run) rather than reaping everything on a blip."""
    return bool(client.exists(heartbeat_key(submission_id)))


def clear(client: Any, submission_id: str) -> None:
    try:
        client.delete(heartbeat_key(submission_id))
    except Exception as exc:  # noqa: BLE001
        logger.debug("heartbeat clear failed for %s: %s", submission_id, exc)


class Heartbeat:
    """Refreshes a submission's heartbeat on a daemon thread until stopped.

    No-op when ``HEARTBEAT_ENABLED`` is false or no Redis client is obtainable,
    so unit tests and Redis-less environments simply skip it.
    """

    def __init__(
        self,
        submission_id: str,
        stage: str,
        *,
        client: Any = None,
        interval: float | None = None,
        ttl: int | None = None,
    ) -> None:
        self.submission_id = submission_id
        self.stage = stage
        self._client = client
        self._interval = interval if interval is not None else settings.HEARTBEAT_INTERVAL
        self._ttl = ttl if ttl is not None else settings.HEARTBEAT_TTL
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Heartbeat":
        if not settings.HEARTBEAT_ENABLED:
            return self
        if self._client is None:
            try:
                self._client = get_redis()
            except Exception as exc:  # noqa: BLE001
                logger.debug("heartbeat disabled (no redis client): %s", exc)
                return self
        mark_alive(self._client, self.submission_id, self.stage, self._ttl)
        self._thread = threading.Thread(
            target=self._run, name=f"hb-{self.submission_id}", daemon=True
        )
        self._thread.start()
        return self

    def _run(self) -> None:
        # wait() returns True only when stop is set -> loop exits cleanly; on
        # timeout it returns False and we refresh.
        while not self._stop.wait(self._interval):
            mark_alive(self._client, self.submission_id, self.stage, self._ttl)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._client is not None and settings.HEARTBEAT_ENABLED:
            clear(self._client, self.submission_id)


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def stage_context(stage: str) -> Callable[[F], F]:
    """Decorator for a worker's ``_async_run_*`` coroutine: bind log context +
    run the heartbeat for the whole stage, tearing both down on exit. The
    wrapped coroutine's first positional arg must be ``submission_id_str``."""

    def deco(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(submission_id_str: str, *args: Any, **kwargs: Any) -> Any:
            bind_log_context(submission_id=submission_id_str, stage=stage)
            hb = Heartbeat(submission_id_str, stage).start()
            try:
                return await fn(submission_id_str, *args, **kwargs)
            finally:
                hb.stop()
                clear_log_context()

        return wrapper  # type: ignore[return-value]

    return deco
