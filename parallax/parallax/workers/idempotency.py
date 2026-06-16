"""Stage-level idempotency for the analysis pipeline.

Celery delivers at least once, so a task can be handed to a worker twice. The
expensive stages (dynamic instrumentation, the reasoning cortex) must not re-run
and duplicate observations or LLM cost on redelivery. Each stage records its
progress in the submission status; a redelivered task whose submission has
already advanced past that stage is a no-op.

Re-analysis is still possible: callers that genuinely want to reprocess reset
the submission status first (the in-process pipeline driver does this).
"""

from __future__ import annotations

# Linear order of the pipeline statuses.
_ORDER = ["queued", "triaging", "static", "dynamic", "reasoning", "complete"]

# The status a submission has once a given stage has finished its work.
_STAGE_DONE_AT = {
    "triage": "static",
    "static": "dynamic",
    "dynamic": "reasoning",
    "reasoning": "complete",
}


def stage_already_done(status: str | None, stage: str) -> bool:
    """True if ``stage`` has already completed for a submission in ``status``.

    A redelivered task should skip when this returns True. Unknown statuses
    (for example a freshly seeded submission) are treated as not-done so the
    stage runs normally. ``failed`` is never "done", so a failed analysis can be
    retried.
    """
    done_at = _STAGE_DONE_AT.get(stage)
    if done_at is None or status is None or status not in _ORDER:
        return False
    return _ORDER.index(status) >= _ORDER.index(done_at)
