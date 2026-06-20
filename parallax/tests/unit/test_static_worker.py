import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from parallax.core.models import Submission
from parallax.workers.static_worker import _async_run_static_pipeline


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture(autouse=True)
def _stub_dynamic_dispatch(monkeypatch):
    """The static worker enqueues the dynamic stage via Celery .delay() on
    success. Stub it so the unit test never needs a live Redis broker — in CI
    the real .delay() fails to connect and the worker marks the submission
    'failed' instead of advancing to 'dynamic'."""
    import parallax.workers.dynamic_worker as dw

    monkeypatch.setattr(dw.run_dynamic_pipeline, "delay", lambda *a, **k: None, raising=False)


@pytest.mark.asyncio
@patch("parallax.workers.static_worker.get_minio_client")
@patch("parallax.workers.static_worker.run_androguard")
@patch("parallax.workers.static_worker.run_yara")
@patch("parallax.workers.static_worker.run_jadx")
@patch("parallax.workers.static_worker.async_session")
@patch("parallax.workers.static_worker.HypothesisEngine.process_static_results")
async def test_static_worker_success(
    mock_process_static_results,
    mock_async_session,
    mock_run_jadx,
    mock_run_yara,
    mock_run_androguard,
    mock_get_minio_client,
    mock_db,
):
    # Setup mocks
    sub_id = uuid.uuid4()
    submission = Submission(id=sub_id, sha256="fakehash123", status="triaging")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = submission
    mock_db.execute.return_value = mock_result

    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_db
    mock_async_session.return_value = mock_session_context

    mock_minio = MagicMock()
    mock_get_minio_client.return_value = mock_minio

    mock_run_androguard.return_value = {
        "package_name": "com.evil.app",
        "app_name": "Evil",
        "version_name": "1.0",
        "version_code": "1",
        "min_sdk": "21",
        "target_sdk": "30",
        "main_activity": ".MainActivity",
        "permissions": ["android.permission.INTERNET"],
        "activities": [".MainActivity"],
        "services": [],
        "receivers": [],
        "providers": [],
        "is_valid": True,
    }

    mock_run_yara.return_value = [
        {
            "rule": "Android_BankingTrojan",
            "namespace": "baseline",
            "tags": [],
            "meta": {},
            "strings": [],
        }
    ]

    mock_run_jadx.return_value = {"status": "success", "output_dir": "/tmp/jadx_out"}

    # Run
    await _async_run_static_pipeline(str(sub_id))

    # Assert
    assert submission.status == "dynamic"
    assert "re_workbench_artifact" in submission.metadata_json
    assert submission.package_name == "com.evil.app"


@pytest.mark.asyncio
@patch("parallax.workers.static_worker.flag_modified")
@patch("parallax.workers.static_worker.get_minio_client")
@patch("parallax.workers.static_worker.run_androguard")
@patch("parallax.workers.static_worker.run_yara")
@patch("parallax.workers.static_worker.run_jadx")
@patch("parallax.workers.static_worker.async_session")
@patch("parallax.workers.static_worker.HypothesisEngine.process_static_results")
async def test_static_worker_flags_metadata_modified_for_persistence(
    mock_process_static_results,
    mock_async_session,
    mock_run_jadx,
    mock_run_yara,
    mock_run_androguard,
    mock_get_minio_client,
    mock_flag_modified,
    mock_db,
):
    """Regression: the RE-workbench artifact is written to a JSONB column via
    in-place mutation, which SQLAlchemy does NOT change-track. Without an
    explicit flag_modified the artifact is silently dropped on commit and the
    cortex analyses empty input (false CLEAN). Assert the column is flagged.

    The pre-fix code passed `re_workbench_artifact in submission.metadata_json`
    (an in-memory check) while the data never reached the DB -- this test
    guards the actual fix.
    """
    sub_id = uuid.uuid4()
    submission = Submission(id=sub_id, sha256="fakehash123", status="triaging")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = submission
    mock_db.execute.return_value = mock_result
    ctx = AsyncMock()
    ctx.__aenter__.return_value = mock_db
    mock_async_session.return_value = ctx
    mock_get_minio_client.return_value = MagicMock()
    mock_run_androguard.return_value = {"package_name": "com.evil.app", "is_valid": True}
    mock_run_yara.return_value = []
    mock_run_jadx.return_value = {"status": "success", "output_dir": "/tmp/jadx_out"}

    await _async_run_static_pipeline(str(sub_id))

    mock_flag_modified.assert_called_once_with(submission, "metadata_json")
