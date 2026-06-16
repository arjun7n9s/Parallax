"""A small async circuit breaker for external-service calls.

When a dependency (an LLM provider, a database, an object store) starts failing,
every analysis would otherwise wait out the full timeout before failing. A
circuit breaker detects the failure pattern, opens, and fails fast for a cooling
period, then probes once before closing again.

    CLOSED      calls flow; failures are counted
    OPEN        calls are rejected immediately (fail fast) until recovery_timeout
    HALF_OPEN   one trial call is allowed; success closes, failure re-opens

The clock is injectable so tests advance time without sleeping.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from parallax.core.errors import InfraError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(InfraError):
    """Raised when a call is rejected because the breaker is open (fail fast)."""


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._time = time_fn
        self.state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def _allow(self) -> bool:
        if self.state is CircuitState.OPEN:
            if self._time() - self._opened_at >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit '%s' half-open: probing", self.name)
                return True
            return False
        return True  # CLOSED or HALF_OPEN both allow the call

    def _on_success(self) -> None:
        if self.state is not CircuitState.CLOSED:
            logger.info("circuit '%s' closing after success", self.name)
        self.state = CircuitState.CLOSED
        self._failures = 0

    def _on_failure(self) -> None:
        self._failures += 1
        # A failed probe in HALF_OPEN, or crossing the threshold in CLOSED, opens.
        if self.state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
            if self.state is not CircuitState.OPEN:
                logger.warning(
                    "circuit '%s' opening after %d failure(s)", self.name, self._failures
                )
            self.state = CircuitState.OPEN
            self._opened_at = self._time()

    async def call(self, factory: Callable[[], Awaitable[T]]) -> T:
        """Run ``factory()`` under the breaker. Raises CircuitOpenError if open."""
        if not self._allow():
            raise CircuitOpenError(f"circuit '{self.name}' is open; failing fast")
        try:
            result = await factory()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result
