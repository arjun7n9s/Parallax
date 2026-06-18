"""Tests for batch submission (3.2b): multi-file ingest + per-batch status."""

import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

import parallax.workers.triage_worker  # noqa: F401
from parallax.api.main import app
from parallax.core.database import get_session


def _files(n, valid=True):
    magic = b"PK\x03\x04" if valid else b"BAD!"
    return [
        ("files", (f"m{i}.apk", BytesIO(magic + f" apk {i}".encode()), "application/octet-stream"))
        for i in range(n)
    ]


class TestBatchSubmit:
    @patch("parallax.workers.triage_worker.run_triage_pipeline.delay")
    @patch("parallax.api.routes.analyze.get_minio_client")
    def test_batch_returns_batch_id_and_per_file_results(
        self, mock_minio, mock_delay, client: TestClient
    ):
        mock_minio.return_value = MagicMock()
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None  # no dedup hit
        mock_session.execute = AsyncMock(return_value=result)

        def mock_add(obj):
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        mock_session.add.side_effect = mock_add
        app.dependency_overrides[get_session] = lambda: mock_session

        resp = client.post("/api/v1/analyze/batch", files=_files(3))
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert "batch_id" in body
        assert body["total"] == 3
        assert body["submitted"] == 3
        assert all("submission_id" in r for r in body["results"])
        assert mock_delay.call_count == 3

    @patch("parallax.workers.triage_worker.run_triage_pipeline.delay")
    @patch("parallax.api.routes.analyze.get_minio_client")
    def test_invalid_file_reported_without_aborting_batch(
        self, mock_minio, mock_delay, client: TestClient
    ):
        mock_minio.return_value = MagicMock()
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result)
        mock_session.add.side_effect = lambda o: setattr(o, "created_at", None)
        app.dependency_overrides[get_session] = lambda: mock_session

        # One valid APK + one with bad magic bytes.
        files = _files(1, valid=True) + _files(1, valid=False)
        resp = client.post("/api/v1/analyze/batch", files=files)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert body["total"] == 2
        assert body["submitted"] == 1
        errored = [r for r in body["results"] if "error" in r]
        assert len(errored) == 1
        assert "magic bytes" in errored[0]["error"]

    def test_batch_over_limit_rejected(self, client: TestClient):
        # 101 files exceeds the 100-APK cap; rejected before any processing.
        resp = client.post("/api/v1/analyze/batch", files=_files(101))
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()


class TestBatchStatus:
    def test_unknown_batch_404(self, client: TestClient):
        mock_session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result)
        app.dependency_overrides[get_session] = lambda: mock_session

        resp = client.get(f"/api/v1/analyze/batch/{uuid.uuid4()}")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_status_aggregates_per_sample(self, client: TestClient):
        def _sub(status, verdict=None):
            s = MagicMock()
            s.id = uuid.uuid4()
            s.file_name = "m.apk"
            s.status = status
            s.verdict = verdict
            s.final_score = None
            return s

        subs = [_sub("complete", "HIGH"), _sub("complete", "CLEAN"), _sub("dynamic")]
        mock_session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = subs
        mock_session.execute = AsyncMock(return_value=result)
        app.dependency_overrides[get_session] = lambda: mock_session

        resp = client.get(f"/api/v1/analyze/batch/{uuid.uuid4()}")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["by_status"]["complete"] == 2
        assert body["by_status"]["dynamic"] == 1
        assert body["complete"] is False  # one still running
        assert len(body["submissions"]) == 3
