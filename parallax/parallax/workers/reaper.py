"""Orphan reaper: re-queue analyses whose worker died mid-stage.

A live stage keeps ``hb:{submission_id}`` fresh in Redis (see ``heartbeat.py``).
This Celery-beat task finds submissions still in a non-terminal status whose
heartbeat has expired and which have been untouched for at least the grace
window, then re-dispatches the worker for their current stage. The stage
idempotency guard (``stage_already_done``) makes restarting a stage safe, and
completed stages are skipped, so resuming never duplicates work or LLM cost.

Safety: if Redis is unreachable the whole run is skipped — a missed reap is
recovered on the next tick, but a false reap would double-dispatch live work.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from parallax.core.config import settings
from parallax.core.database import async_session
from parallax.core.metrics import record_orphan_reaped
from parallax.core.models import Submission
from parallax.workers.celery_app import celery_app
from parallax.workers.heartbeat import get_redis, is_alive

logger = logging.getLogger(__name__)

# Current in-progress status -> the task that resumes that stage. The status
# field is the checkpoint; resuming the matching worker re-enters at that stage.
RESUME_DISPATCH: dict[str, str] = {
    "queued": "parallax.workers.triage_worker.run_triage_pipeline",
    "triaging": "parallax.workers.triage_worker.run_triage_pipeline",
    "static": "parallax.workers.static_worker.run_static_pipeline",
    "dynamic": "parallax.workers.dynamic_worker.run_dynamic_pipeline",
    "reasoning": "parallax.workers.reasoning_worker.run_reasoning_pipeline",
}
NON_TERMINAL: tuple[str, ...] = tuple(RESUME_DISPATCH.keys())


def find_orphans(submissions: list[Any], client: Any, now: datetime, grace_s: int) -> list[Any]:
    """Pure selection. From non-terminal candidates, return those untouched for
    longer than the grace window and with no live heartbeat. Raises whatever
    ``is_alive`` raises on a Redis connection error, so the caller can abort."""
    cutoff = now - timedelta(seconds=grace_s)
    orphans = []
    for s in submissions:
        if s.status not in RESUME_DISPATCH:
            continue
        updated = s.updated_at
        if updated is not None:
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if updated > cutoff:
                continue  # touched recently — give the worker time to heartbeat
        if is_alive(client, str(s.id)):
            continue  # worker is still alive
        orphans.append(s)
    return orphans


async def _areap(now: datetime) -> list[str]:
    try:
        client = get_redis()
        client.ping()
    except Exception as exc:  # noqa: BLE001 - Redis down: skip, never false-reap
        logger.warning("orphan reaper: Redis unavailable, skipping run: %s", exc)
        return []

    async with async_session() as db:
        result = await db.execute(select(Submission).where(Submission.status.in_(NON_TERMINAL)))
        candidates = list(result.scalars().all())

    try:
        orphans = find_orphans(candidates, client, now, settings.ORPHAN_GRACE_SECONDS)
    except Exception as exc:  # noqa: BLE001 - Redis blip mid-scan: skip this run
        logger.warning("orphan reaper: Redis error during scan, skipping run: %s", exc)
        return []

    reaped: list[str] = []
    for s in orphans:
        task = RESUME_DISPATCH[s.status]
        sid = str(s.id)
        celery_app.send_task(task, args=[sid])
        record_orphan_reaped(s.status)
        logger.warning(
            "orphan reaper: re-queued submission %s at stage %s via %s", sid, s.status, task
        )
        reaped.append(sid)
    return reaped


@celery_app.task(name="parallax.workers.reaper.reap_orphans")
def reap_orphans() -> list[str]:
    """Beat entry point. Returns the ids re-queued (handy for tests/logs)."""
    return asyncio.run(_areap(datetime.now(timezone.utc)))
