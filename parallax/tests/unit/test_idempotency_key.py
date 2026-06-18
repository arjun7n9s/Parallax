"""Tests for the Idempotency-Key submission helper and its route wiring."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

import parallax.workers.triage_worker  # noqa: F401
from parallax.api import idempotency
from parallax.api.main import app
from parallax.core.database import get_session


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, k):
        return self.store.get(k)

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.store:
            return None
        self.store[k] = v
        return True


class TestHelper:
    def test_store_then_lookup_roundtrip(self):
        c = FakeRedis()
        assert idempotency.lookup_submission_id(c, "key-1") is None
        idempotency.remember_submission_id(c, "key-1", "sub-123")
        assert idempotency.lookup_submission_id(c, "key-1") == "sub-123"

    def test_nx_first_writer_wins(self):
        c = FakeRedis()
        idempotency.remember_submission_id(c, "k", "first")
        idempotency.remember_submission_id(c, "k", "second")
        assert idempotency.lookup_submission_id(c, "k") == "first"

    def test_decodes_bytes(self):
        c = FakeRedis()
        c.store[idempotency._redis_key("k")] = b"sub-bytes"
        assert idempotency.lookup_submission_id(c, "k") == "sub-bytes"

    def test_lookup_fails_open_on_redis_error(self):
        class Boom:
            def get(self, k):
                raise ConnectionError("redis down")

        assert idempotency.lookup_submission_id(Boom(), "k") is None

    def test_store_fails_open_on_redis_error(self):
        class Boom:
            def set(self, *a, **k):
                raise ConnectionError("redis down")

        # Must not raise.
        idempotency.remember_submission_id(Boom(), "k", "sub")


def _submit(client, key=None):
    files = {
        "file": (
            "m.apk",
            BytesIO(b"PK\x03\x04 fake apk"),
            "application/vnd.android.package-archive",
        )
    }
    headers = {"Idempotency-Key": key} if key else {}
    return client.post("/api/v1/analyze", files=files, headers=headers)


class TestRouteReplay:
    @patch("parallax.api.routes.analyze.remember_submission_id")
    @patch("parallax.api.routes.analyze.lookup_submission_id")
    @patch("parallax.workers.heartbeat.get_redis")
    @patch("parallax.workers.triage_worker.run_triage_pipeline.delay")
    @patch("parallax.api.routes.analyze.get_minio_client")
    def test_replayed_key_returns_same_submission_without_reprocessing(
        self, mock_minio, mock_delay, mock_redis, mock_lookup, mock_remember, client: TestClient
    ):
        import uuid
        from datetime import datetime, timezone

        existing_id = uuid.uuid4()

        # Idempotency lookup reports this key was already used.
        mock_lookup.return_value = str(existing_id)
        mock_redis.return_value = FakeRedis()

        existing = MagicMock()
        existing.id = existing_id
        existing.sha256 = "d" * 64
        existing.md5 = "e" * 32
        existing.file_name = "m.apk"
        existing.file_size = 12
        existing.status = "complete"
        existing.priority = "normal"
        existing.s3_path = "s3://apks/x.apk"
        existing.verdict = "HIGH"
        existing.final_score = 80.0
        existing.triage_score = None
        existing.package_name = "com.evil"
        existing.metadata_json = None
        existing.created_at = datetime.now(timezone.utc)
        existing.updated_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=result)
        app.dependency_overrides[get_session] = lambda: mock_session

        resp = _submit(client, key="abc-123")
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        assert resp.json()["sha256"] == "d" * 64
        # Short-circuited before queuing any new work.
        mock_delay.assert_not_called()
        mock_minio.assert_not_called()
