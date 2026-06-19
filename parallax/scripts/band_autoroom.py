"""Auto-open a live Band room when a PARALLAX analysis completes.

Runs in the band venv (.venv-band) alongside band_orchestrator.py. Polls the
PARALLAX DB; when a submission reaches `complete` with a cortex result and has
no Band room yet, it opens a live room via live_case.open_live_case and records
the room id on the submission so it is never reopened.

This is the bridge that makes the dashboard -> Band flow automatic: an analyst
submits an APK in the UI, the pipeline runs, and the moment it completes the 8
Band agents are handed the real evidence and start collaborating — no manual
step.

Usage (after starting band_orchestrator.py):
    .venv-band/Scripts/python scripts/band_autoroom.py
    .venv-band/Scripts/python scripts/band_autoroom.py --all   # also room pre-existing completes
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from parallax.agents.band.live_case import open_live_case
from parallax.core.database import async_session
from parallax.core.models import Submission

logger = logging.getLogger("band_autoroom")


async def _complete_ids() -> set[str]:
    async with async_session() as db:
        rows = (
            (await db.execute(select(Submission.id).where(Submission.status == "complete")))
            .scalars()
            .all()
        )
    return {str(r) for r in rows}


async def _record_room(submission_id: str, room_id: str) -> None:
    async with async_session() as db:
        sub = (
            await db.execute(select(Submission).where(Submission.id == submission_id))
        ).scalar_one()
        md = dict(sub.metadata_json or {})
        md["band_room_id"] = room_id
        sub.metadata_json = md
        flag_modified(sub, "metadata_json")
        await db.commit()


async def watch(interval: float, room_existing: bool) -> None:
    # Unless --all, skip submissions that were already complete at startup so we
    # only open rooms for analyses the analyst runs during this session.
    skip = set() if room_existing else await _complete_ids()
    if skip:
        logger.info("Ignoring %d pre-existing complete submission(s).", len(skip))
    logger.info("Watching for completed analyses (every %.0fs)…", interval)

    while True:
        try:
            async with async_session() as db:
                rows = (
                    (await db.execute(select(Submission).where(Submission.status == "complete")))
                    .scalars()
                    .all()
                )
            for sub in rows:
                sid = str(sub.id)
                md = sub.metadata_json or {}
                if sid in skip or md.get("band_room_id") or not md.get("cortex_result"):
                    continue
                logger.info("New completed analysis %s (%s) — opening Band room…", sid, sub.verdict)
                try:
                    room_id = await open_live_case(sid)
                    await _record_room(sid, room_id)
                    logger.info("Opened Band room %s for %s", room_id, sub.file_name)
                except Exception as exc:  # noqa: BLE001 - keep watching on a single failure
                    logger.warning("Failed to open room for %s: %s", sid, exc)
                    skip.add(sid)  # don't hammer a broken one every tick
        except Exception as exc:  # noqa: BLE001
            logger.warning("watch loop error: %s", exc)
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-open Band rooms for completed analyses.")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument(
        "--all", action="store_true", help="Also open rooms for already-complete submissions."
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(watch(args.interval, args.all))


if __name__ == "__main__":
    main()
