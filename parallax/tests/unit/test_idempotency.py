"""Tests for stage-level idempotency (Phase 1, task 1.4): a redelivered Celery
task must not re-run a stage that already completed."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from parallax.core.models import Submission
from parallax.workers.idempotency import stage_already_done


class TestStageAlreadyDone:
    @pytest.mark.parametrize(
        "stage,status,done",
        [
            ("dynamic", "reasoning", True),
            ("dynamic", "complete", True),
            ("dynamic", "dynamic", False),
            ("dynamic", "static", False),
            ("reasoning", "complete", True),
            ("reasoning", "reasoning", False),
            ("static", "dynamic", True),
            ("triage", "static", True),
            ("triage", "queued", False),
            # failed is retryable, never "done"; unknown/None never "done".
            ("dynamic", "failed", False),
            ("dynamic", "pending", False),
            ("dynamic", None, False),
        ],
    )
    def test_truth_table(self, stage, status, done):
        assert stage_already_done(status, stage) is done


def _session_with(submission):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = submission
    session.execute.return_value = result
    ctx = AsyncMock()
    ctx.__aenter__.return_value = session
    return ctx


class TestRedeliveryGuard:
    @pytest.mark.asyncio
    @patch("parallax.workers.dynamic_worker.SandboxRunner")
    @patch("parallax.workers.dynamic_worker.get_minio_client")
    @patch("parallax.workers.dynamic_worker.async_session")
    async def test_dynamic_skips_when_already_reasoning(
        self, mock_async_session, mock_minio, mock_sandbox
    ):
        from parallax.workers.dynamic_worker import _async_run_dynamic_pipeline

        sub = Submission(id=uuid.uuid4(), sha256="h", status="reasoning", package_name="com.x")
        mock_async_session.return_value = _session_with(sub)

        await _async_run_dynamic_pipeline(str(sub.id))

        # Redelivery is a no-op: no APK download, no sandbox run.
        mock_minio.assert_not_called()
        mock_sandbox.assert_not_called()

    @pytest.mark.asyncio
    @patch("parallax.workers.reasoning_worker.run_cortex")
    @patch("parallax.workers.reasoning_worker.async_session")
    async def test_reasoning_skips_when_complete(self, mock_async_session, mock_run_cortex):
        from parallax.workers.reasoning_worker import _async_run_reasoning_pipeline

        sub = Submission(id=uuid.uuid4(), sha256="h", status="complete", package_name="com.x")
        mock_async_session.return_value = _session_with(sub)

        await _async_run_reasoning_pipeline(str(sub.id))

        mock_run_cortex.assert_not_called()
