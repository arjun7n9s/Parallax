"""Tests for the liveness heartbeat helpers, refresher thread, and the
stage_context decorator that workers use."""

import time

import pytest
import structlog

from parallax.core.config import settings
from parallax.workers import heartbeat as hb


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.sets = 0
        self.deletes = 0

    def set(self, key, value, ex=None):
        self.store[key] = value
        self.sets += 1

    def exists(self, key):
        return 1 if key in self.store else 0

    def delete(self, key):
        self.deletes += 1
        self.store.pop(key, None)


class TestHelpers:
    def test_key_format(self):
        assert hb.heartbeat_key("abc") == "hb:abc"

    def test_mark_is_alive_clear_roundtrip(self):
        client = FakeRedis()
        assert hb.is_alive(client, "s1") is False
        hb.mark_alive(client, "s1", "static")
        assert hb.is_alive(client, "s1") is True
        assert client.store["hb:s1"] == "static"
        hb.clear(client, "s1")
        assert hb.is_alive(client, "s1") is False

    def test_mark_alive_swallows_client_error(self):
        class Boom:
            def set(self, *a, **k):
                raise ConnectionError("redis down")

        # Must not raise — a dead heartbeat must never break a stage.
        hb.mark_alive(Boom(), "s1", "static")

    def test_is_alive_propagates_connection_error(self):
        class Boom:
            def exists(self, *a, **k):
                raise ConnectionError("redis down")

        # The reaper relies on this raising so it can skip rather than false-reap.
        with pytest.raises(ConnectionError):
            hb.is_alive(Boom(), "s1")


class TestHeartbeatThread:
    def test_disabled_is_noop(self, monkeypatch):
        monkeypatch.setattr(settings, "HEARTBEAT_ENABLED", False, raising=False)
        client = FakeRedis()
        h = hb.Heartbeat("s1", "static", client=client).start()
        h.stop()
        assert client.sets == 0

    def test_refreshes_then_clears(self, monkeypatch):
        monkeypatch.setattr(settings, "HEARTBEAT_ENABLED", True, raising=False)
        client = FakeRedis()
        h = hb.Heartbeat("s1", "dynamic", client=client, interval=0.01, ttl=1).start()
        # Initial mark + at least one refresh tick.
        time.sleep(0.05)
        h.stop()
        assert client.sets >= 2
        assert client.deletes == 1
        assert "hb:s1" not in client.store


class TestStageContext:
    def teardown_method(self):
        structlog.contextvars.clear_contextvars()

    @pytest.mark.asyncio
    async def test_binds_context_and_passes_through(self, monkeypatch):
        # Heartbeat disabled (default autouse) -> decorator still binds + clears.
        seen = {}

        @hb.stage_context("static")
        async def fake_stage(submission_id_str):
            seen.update(structlog.contextvars.get_contextvars())
            return f"ran:{submission_id_str}"

        result = await fake_stage("sub-9")
        assert result == "ran:sub-9"
        assert seen["submission_id"] == "sub-9"
        assert seen["stage"] == "static"
        # Context cleared after the stage exits.
        assert structlog.contextvars.get_contextvars() == {}

    @pytest.mark.asyncio
    async def test_clears_context_even_on_error(self):
        @hb.stage_context("reasoning")
        async def boom(submission_id_str):
            raise ValueError("stage blew up")

        with pytest.raises(ValueError):
            await boom("sub-err")
        assert structlog.contextvars.get_contextvars() == {}
