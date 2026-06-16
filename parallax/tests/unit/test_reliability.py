"""Tests for the reliability core: typed errors, circuit breaker, and the
LLM boundary that uses them (Phase 1, tasks 1.5 and 1.6)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from parallax.core.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from parallax.core.errors import (
    DataError,
    InfraError,
    LLMBadOutputError,
    LLMError,
    ParallaxError,
    PermanentError,
    TransientError,
    is_retryable,
)


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


# ----------------------------------------------------------- error hierarchy
class TestErrorHierarchy:
    def test_transient_vs_permanent(self):
        assert issubclass(InfraError, TransientError)
        assert issubclass(LLMError, TransientError)
        assert issubclass(DataError, PermanentError)
        assert issubclass(LLMBadOutputError, PermanentError)
        assert issubclass(TransientError, ParallaxError)

    def test_is_retryable(self):
        assert is_retryable(InfraError("db down")) is True
        assert is_retryable(LLMError("502")) is True
        assert is_retryable(DataError("bad apk")) is False
        assert is_retryable(LLMBadOutputError("junk")) is False
        assert is_retryable(ValueError("other")) is False


# ----------------------------------------------------------- circuit breaker
class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_opens_after_threshold_then_fails_fast(self):
        clk = _Clock()
        cb = CircuitBreaker("x", failure_threshold=3, recovery_timeout=10, time_fn=clk)

        async def boom():
            raise RuntimeError("down")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(boom)
        assert cb.state is CircuitState.OPEN

        # When open, the factory is NOT invoked and we fail fast.
        calls = {"n": 0}

        async def probe():
            calls["n"] += 1
            return "ok"

        with pytest.raises(CircuitOpenError):
            await cb.call(probe)
        assert calls["n"] == 0

    @pytest.mark.asyncio
    async def test_half_open_closes_on_success(self):
        clk = _Clock()
        cb = CircuitBreaker("x", failure_threshold=1, recovery_timeout=10, time_fn=clk)

        async def boom():
            raise RuntimeError("down")

        with pytest.raises(RuntimeError):
            await cb.call(boom)
        assert cb.state is CircuitState.OPEN

        clk.t = 11  # past the recovery window

        async def ok():
            return "recovered"

        assert await cb.call(ok) == "recovered"
        assert cb.state is CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failed_probe_reopens(self):
        clk = _Clock()
        cb = CircuitBreaker("x", failure_threshold=1, recovery_timeout=10, time_fn=clk)

        async def boom():
            raise RuntimeError("down")

        with pytest.raises(RuntimeError):
            await cb.call(boom)
        clk.t = 11
        with pytest.raises(RuntimeError):
            await cb.call(boom)  # probe fails
        assert cb.state is CircuitState.OPEN

    def test_circuit_open_is_transient(self):
        # An open circuit is a transient condition: the worker may retry later.
        assert isinstance(CircuitOpenError("open"), InfraError)
        assert is_retryable(CircuitOpenError("open"))


# ----------------------------------------------------------- LLM boundary
def _aiml_provider(monkeypatch, create_fn):
    from parallax.ai.llm import LLMProvider
    from parallax.core.config import settings

    monkeypatch.setattr(settings, "LLM_MODE", "auto")
    monkeypatch.setattr(settings, "CLOUD_PROVIDER", "aiml")
    monkeypatch.setattr(settings, "AIML_API", "test-key")
    p = LLMProvider()
    p._aiml = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_fn)),
        close=AsyncMock(),
    )
    return p


class TestRetryableTask:
    def test_retry_config(self):
        from parallax.workers.mixins import RetryableTask

        assert RetryableTask.autoretry_for == (TransientError,)
        assert RetryableTask.max_retries == 3
        assert RetryableTask.retry_backoff is True
        assert RetryableTask.acks_late is True

    def test_pipeline_workers_inherit_retryable(self):
        # Each worker's task base must be a RetryableTask so transient failures
        # auto-retry with backoff.
        from parallax.workers.mixins import RetryableTask

        for mod in (
            "parallax.workers.triage_worker",
            "parallax.workers.static_worker",
            "parallax.workers.dynamic_worker",
            "parallax.workers.reasoning_worker",
            "parallax.workers.delivery_worker",
        ):
            m = __import__(mod, fromlist=["AsyncSQLAlchemyTask"])
            assert issubclass(m.AsyncSQLAlchemyTask, RetryableTask), mod


class TestLLMBoundary:
    @pytest.mark.asyncio
    async def test_backend_failure_becomes_llmerror(self, monkeypatch):
        async def create(**kwargs):
            raise RuntimeError("upstream 502")

        p = _aiml_provider(monkeypatch, create)
        with pytest.raises(LLMError):
            await p.complete_text("synthesis", "hi")

    @pytest.mark.asyncio
    async def test_circuit_opens_after_repeated_failures(self, monkeypatch):
        calls = {"n": 0}

        async def create(**kwargs):
            calls["n"] += 1
            raise RuntimeError("upstream 502")

        p = _aiml_provider(monkeypatch, create)
        for _ in range(5):  # default threshold
            with pytest.raises(LLMError):
                await p.complete_text("synthesis", "hi")
        assert calls["n"] == 5
        # Next call fails fast: circuit open, backend not hit again.
        with pytest.raises(CircuitOpenError):
            await p.complete_text("synthesis", "hi")
        assert calls["n"] == 5

    @pytest.mark.asyncio
    async def test_complete_json_raises_on_unparseable_output(self, monkeypatch):
        async def create(**kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json at all"))]
            )

        p = _aiml_provider(monkeypatch, create)
        with pytest.raises(LLMBadOutputError):
            await p.complete_json("synthesis", "hi")
