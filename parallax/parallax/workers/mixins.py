"""Shared Celery task base for the analysis pipeline.

Workers inherit RetryableTask so transient failures retry with exponential
backoff and jitter, and permanent failures do not. A worker signals "transient"
by letting a TransientError (InfraError / LLMError / CircuitOpenError) propagate
out of its task body; permanent and unknown failures are handled in-worker
(status set to failed) and never re-raised, so they are not retried.

When retries are exhausted, on_failure logs a dead-letter record so a stuck
analysis is visible rather than silently lost.
"""

from __future__ import annotations

import logging

try:
    from celery import Task
except ImportError:  # lightweight dev venvs without celery
    Task = object  # type: ignore[assignment,misc]

from parallax.core.errors import TransientError

logger = logging.getLogger(__name__)


class RetryableTask(Task):
    abstract = True
    # Celery retries the task automatically when the body raises one of these.
    autoretry_for = (TransientError,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    # Re-deliver if the worker dies mid-task; the stage idempotency guard makes
    # re-delivery safe (a completed stage is skipped).
    acks_late = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: D401
        logger.error(
            "task %r dead-lettered (task_id=%s, args=%s): %s",
            getattr(self, "name", "?"),
            task_id,
            args,
            exc,
        )
