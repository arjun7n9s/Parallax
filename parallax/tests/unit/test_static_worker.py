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


@pytest.mark.asyncio
@patch("parallax.workers.static_worker.get_minio_client")
@patch("parallax.workers.static_worker.run_androguard")
@patch("parallax.workers.static_worker.run_yara")
@patch("parallax.workers.static_worker.run_jadx")
@patch("parallax.workers.static_worker.async_session")
async def test_static_worker_success(
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
