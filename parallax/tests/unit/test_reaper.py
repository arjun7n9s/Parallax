"""Tests for the orphan reaper's pure selection logic and resume dispatch map."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from parallax.workers import reaper
from parallax.workers.idempotency import _ORDER

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class FakeRedis:
    def __init__(self, alive_ids=()):
        self.alive = set(alive_ids)

    def exists(self, key):
        # key is hb:{id}
        return 1 if key.removeprefix("hb:") in self.alive else 0


def _sub(sid, status, updated_at):
    return SimpleNamespace(id=sid, status=status, updated_at=updated_at)


class TestResumeDispatch:
    def test_covers_every_non_terminal_status(self):
        # Every pipeline status except the terminal ones must be resumable.
        non_terminal = [s for s in _ORDER if s != "complete"]
        for status in non_terminal:
            assert status in reaper.RESUME_DISPATCH, f"no resume target for {status}"

    def test_excludes_terminal_statuses(self):
        assert "complete" not in reaper.RESUME_DISPATCH
        assert "failed" not in reaper.RESUME_DISPATCH

    def test_targets_are_real_task_names(self):
        for status, task in reaper.RESUME_DISPATCH.items():
            assert task.startswith("parallax.workers.")
            assert task.endswith("_pipeline")


class TestFindOrphans:
    def test_old_and_no_heartbeat_is_orphan(self):
        subs = [_sub("a", "dynamic", NOW - timedelta(seconds=600))]
        orphans = reaper.find_orphans(subs, FakeRedis(), NOW, grace_s=90)
        assert [s.id for s in orphans] == ["a"]

    def test_live_heartbeat_is_not_orphan(self):
        subs = [_sub("a", "dynamic", NOW - timedelta(seconds=600))]
        orphans = reaper.find_orphans(subs, FakeRedis(alive_ids=["a"]), NOW, grace_s=90)
        assert orphans == []

    def test_recently_updated_is_not_orphan(self):
        # Within the grace window -> give the worker time to start heartbeating.
        subs = [_sub("a", "static", NOW - timedelta(seconds=10))]
        orphans = reaper.find_orphans(subs, FakeRedis(), NOW, grace_s=90)
        assert orphans == []

    def test_terminal_status_never_reaped(self):
        subs = [
            _sub("done", "complete", NOW - timedelta(seconds=600)),
            _sub("dead", "failed", NOW - timedelta(seconds=600)),
        ]
        assert reaper.find_orphans(subs, FakeRedis(), NOW, grace_s=90) == []

    def test_null_updated_at_treated_as_old(self):
        subs = [_sub("a", "reasoning", None)]
        orphans = reaper.find_orphans(subs, FakeRedis(), NOW, grace_s=90)
        assert [s.id for s in orphans] == ["a"]

    def test_naive_updated_at_assumed_utc(self):
        # A naive timestamp inside the window is still treated as recent.
        naive_recent = (NOW - timedelta(seconds=5)).replace(tzinfo=None)
        subs = [_sub("a", "dynamic", naive_recent)]
        assert reaper.find_orphans(subs, FakeRedis(), NOW, grace_s=90) == []

    def test_redis_error_propagates(self):
        class Boom:
            def exists(self, *a, **k):
                raise ConnectionError("redis down")

        subs = [_sub("a", "dynamic", NOW - timedelta(seconds=600))]
        with pytest.raises(ConnectionError):
            reaper.find_orphans(subs, Boom(), NOW, grace_s=90)
