"""Reasoning worker — runs the AI Cortex on a submission's collected evidence.

This closes the ``dynamic -> reasoning -> complete`` transition. It pulls the
real static artifact, decompiled code, runtime observations and screenshots,
runs the cortex, and persists the verdict, score, IOCs and full result.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
import zipfile

from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from parallax.ai.orchestration import run_cortex
from parallax.core.database import async_session
from parallax.core.errors import TransientError
from parallax.core.metrics import record_stage_failure, record_verdict
from parallax.core.models import IOC, Observation, Submission, TaintFlow
from parallax.core.storage import DECOMPILED_BUCKET, SCREENSHOTS_BUCKET, get_minio_client
from parallax.workers.celery_app import celery_app
from parallax.workers.heartbeat import stage_context
from parallax.workers.idempotency import stage_already_done
from parallax.workers.mixins import RetryableTask

logger = logging.getLogger(__name__)


def async_to_sync(awaitable):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.ensure_future(awaitable)
    return asyncio.run(awaitable)


class AsyncSQLAlchemyTask(RetryableTask):
    abstract = True

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@celery_app.task(
    bind=True,
    base=AsyncSQLAlchemyTask,
    name="parallax.workers.reasoning_worker.run_reasoning_pipeline",
)
def run_reasoning_pipeline(self, submission_id_str: str):
    logger.info("Starting reasoning pipeline for submission: %s", submission_id_str)
    async_to_sync(_async_run_reasoning_pipeline(submission_id_str))


def _download_decompiled(sha256: str, temp_dir: str) -> str | None:
    """Fetch and unzip the decompiled code; return the local sources dir."""
    client = get_minio_client()
    zip_path = os.path.join(temp_dir, f"{sha256}_decompiled.zip")
    try:
        client.fget_object(DECOMPILED_BUCKET, f"{sha256}.zip", zip_path)
    except Exception as exc:
        logger.warning("No decompiled code for %s: %s", sha256, exc)
        return None
    out_dir = os.path.join(temp_dir, "decompiled")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(out_dir)
    except zipfile.BadZipFile:
        return None
    return out_dir


def _list_screenshots(submission_id_str: str) -> list[str]:
    client = get_minio_client()
    try:
        objs = client.list_objects(
            SCREENSHOTS_BUCKET, prefix=f"{submission_id_str}/", recursive=True
        )
        return [o.object_name for o in objs]
    except Exception as exc:
        logger.warning("Could not list screenshots for %s: %s", submission_id_str, exc)
        return []


def _observation_to_dict(obs: Observation) -> dict:
    return {
        "source": obs.source,
        "event_type": obs.event_type,
        "args": obs.args,
        "return_value": obs.return_value,
        "exception": obs.exception,
        "captured_at_ms": obs.captured_at_ms,
        "caller_package": obs.caller_package,
    }


@stage_context("reasoning")
async def _async_run_reasoning_pipeline(submission_id_str: str):
    try:
        submission_id = uuid.UUID(submission_id_str)
    except ValueError:
        logger.error("Invalid submission ID: %s", submission_id_str)
        return

    temp_dir = None
    try:
        async with async_session() as db:
            result = await db.execute(select(Submission).where(Submission.id == submission_id))
            submission = result.scalar_one_or_none()
            if not submission:
                logger.error("Submission %s not found.", submission_id_str)
                return

            # Idempotency: a redelivered reasoning task must not re-run the
            # (expensive) cortex and duplicate IOCs / graph writes once complete.
            if stage_already_done(submission.status, "reasoning"):
                logger.info(
                    "Reasoning already done for %s (status=%s); skipping redelivery.",
                    submission_id_str,
                    submission.status,
                )
                return

            submission.status = "reasoning"
            await db.commit()

            sha256 = submission.sha256
            metadata = submission.metadata_json or {}
            artifact = metadata.get("re_workbench_artifact", {})
            apkid = metadata.get("apkid")

            temp_dir = tempfile.mkdtemp()
            sources_dir = _download_decompiled(sha256, temp_dir)
            screenshot_keys = _list_screenshots(submission_id_str)

            obs_result = await db.execute(
                select(Observation).where(Observation.submission_id == submission_id)
            )
            observations = [_observation_to_dict(o) for o in obs_result.scalars().all()]

            taint_result = await db.execute(
                select(TaintFlow).where(TaintFlow.submission_id == submission_id)
            )
            taint_flows = [t.to_dict() for t in taint_result.scalars().all()]

            logger.info(
                "Cortex inputs for %s: %d observations, %d taint flows, %d screenshots, sources=%s",
                sha256,
                len(observations),
                len(taint_flows),
                len(screenshot_keys),
                bool(sources_dir),
            )

            # Cross-sample retrieval: find prior submissions that look like this
            # one so the Intel Correlator can attribute family/campaign.
            related_samples = await _retrieve_related(artifact, submission_id_str)

            cortex = await run_cortex(
                submission_id=submission_id_str,
                sha256=sha256,
                artifact=artifact,
                sources_dir=sources_dir,
                observations=observations,
                screenshot_keys=screenshot_keys,
                apkid=apkid,
                related_samples=related_samples,
                taint_flows=taint_flows,
            )

            # Persist verdict + score + full result.
            submission.final_score = cortex.risk.calibrated_score
            submission.verdict = cortex.verdict
            record_verdict(cortex.verdict)
            metadata["cortex_result"] = cortex.to_dict()
            submission.metadata_json = metadata
            # JSON columns are not change-tracked on in-place mutation; flag it
            # explicitly so the cortex_result actually persists for delivery.
            flag_modified(submission, "metadata_json")

            # Persist extracted IOCs (deduped per submission).
            await _persist_iocs(db, submission_id, cortex, observations)

            submission.status = "complete"
            await db.commit()
            logger.info(
                "Reasoning complete for %s: verdict=%s score=%s",
                sha256,
                cortex.verdict,
                cortex.risk.calibrated_score,
            )

            # Enrich the TAIG graph + vector store (the self-improving loop)
            # after the analyst-facing result is committed. This keeps optional
            # knowledge backends from blocking webhooks, Band room creation, or
            # the dashboard's complete state during live demos.
            try:
                await asyncio.wait_for(
                    _enrich_knowledge(sha256, submission_id_str, artifact, cortex),
                    timeout=20.0,
                )
            except TimeoutError:
                logger.warning(
                    "Knowledge enrichment timed out for %s; result already complete.",
                    sha256,
                )

            # Phase 6 delivery is triggered here once the delivery worker exists.
            try:
                from parallax.workers.delivery_worker import run_delivery_pipeline

                run_delivery_pipeline.delay(submission_id_str)
            except ImportError:
                logger.debug("Delivery worker not available; skipping report generation.")

    except TransientError:
        raise  # transient (infra/LLM/circuit-open): let Celery retry the task
    except Exception as exc:
        record_stage_failure("reasoning", exc)
        logger.exception("Error during reasoning pipeline for %s", submission_id_str)
        try:
            async with async_session() as db:
                result = await db.execute(select(Submission).where(Submission.id == submission_id))
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = "failed"
                    await db.commit()
        except Exception:
            pass
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def _retrieve_related(artifact: dict, submission_id_str: str) -> list[dict]:
    """Query the vector store for prior submissions similar to this one."""
    try:
        from parallax.knowledge.qdrant_store import search_similar

        features = artifact.get("static_features", {}) if artifact else {}
        yara = [m.get("rule") for m in artifact.get("yara_matches", [])] if artifact else []
        query = " ".join(
            [
                features.get("package_name", ""),
                " ".join(features.get("permissions", [])[:15]),
                " ".join(str(y) for y in yara),
            ]
        ).strip()
        if not query:
            return []
        return await search_similar(query, top_k=5, exclude_id=submission_id_str)
    except Exception as exc:
        logger.debug("Related-sample retrieval skipped: %s", exc)
        return []


async def _enrich_knowledge(sha256, submission_id_str, artifact, cortex) -> None:
    """Populate Neo4j + index the submission vector. Failures are non-fatal."""
    features = artifact.get("static_features", {}) if artifact else {}
    try:
        from parallax.knowledge.population import populate_graph

        await populate_graph(
            sha256=sha256,
            package=features.get("package_name", "unknown"),
            app_name=features.get("app_name", ""),
            permissions=features.get("permissions", []),
            cortex=cortex,
        )
    except Exception as exc:
        logger.warning("Graph enrichment skipped: %s", exc)
    try:
        from parallax.knowledge.qdrant_store import index_submission

        await index_submission(submission_id_str, sha256, cortex)
    except Exception as exc:
        logger.warning("Vector indexing skipped: %s", exc)
    try:
        from parallax.knowledge.pattern_memory import enrich_pattern_memory

        await enrich_pattern_memory(sha256, cortex, features.get("permissions", []), None)
    except Exception as exc:
        logger.warning("Pattern memory enrichment skipped: %s", exc)


async def _persist_iocs(
    db, submission_id: uuid.UUID, cortex, observations: list[dict] | None = None
) -> None:
    # IOCs confirmed in runtime traffic are stronger evidence than strings
    # that only appear in decompiled code or agent narratives.
    runtime_blob = " ".join(
        str(o.get("args")) + " " + str(o.get("event_type")) for o in (observations or [])
    )
    type_map = {"urls": "url", "domains": "domain", "ips": "ip"}
    for bucket, ioc_type in type_map.items():
        for value in cortex.iocs.get(bucket, []):
            observed_live = bool(runtime_blob) and value in runtime_blob
            db.add(
                IOC(
                    submission_id=submission_id,
                    ioc_type=ioc_type,
                    value=value,
                    context=(
                        "observed in runtime traffic"
                        if observed_live
                        else "extracted from static code/agent evidence"
                    ),
                    confidence=0.85 if observed_live else 0.6,
                    source_agent="cortex",
                )
            )
