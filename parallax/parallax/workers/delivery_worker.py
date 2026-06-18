"""Delivery worker — generate and store all output artifacts for a submission.

Runs after the cortex completes: builds the fraud attack chain, HTML+PDF report,
STIX 2.1 bundle, auto-generated YARA rule and fraud rules, stores them in MinIO,
and dispatches completion webhooks.
"""

from __future__ import annotations

import asyncio
import io
import logging
import uuid

from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified

from parallax.ai.schemas import CortexResult
from parallax.core.database import async_session
from parallax.core.models import Submission
from parallax.core.storage import REPORTS_BUCKET, get_minio_client
from parallax.workers.celery_app import celery_app
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
    name="parallax.workers.delivery_worker.run_delivery_pipeline",
)
def run_delivery_pipeline(self, submission_id_str: str):
    logger.info("Starting delivery pipeline for submission: %s", submission_id_str)
    async_to_sync(_async_run_delivery(submission_id_str))


def _put(client, key: str, data: bytes, content_type: str) -> str:
    client.put_object(
        REPORTS_BUCKET, key, data=io.BytesIO(data), length=len(data), content_type=content_type
    )
    return f"s3://{REPORTS_BUCKET}/{key}"


async def _async_run_delivery(submission_id_str: str):
    from parallax.delivery.fraud_chain import build_fraud_chain
    from parallax.delivery.fraud_rules import generate_fraud_rules
    from parallax.delivery.report_generator import render_html, render_pdf
    from parallax.delivery.stix_exporter import build_stix_json
    from parallax.delivery.yara_generator import generate_yara_rule

    try:
        submission_id = uuid.UUID(submission_id_str)
    except ValueError:
        logger.error("Invalid submission ID: %s", submission_id_str)
        return

    async with async_session() as db:
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()
        if not submission or not submission.metadata_json:
            logger.error("No submission/cortex result for %s", submission_id_str)
            return

        cortex_dict = submission.metadata_json.get("cortex_result")
        if not cortex_dict:
            logger.warning("No cortex_result for %s; skipping delivery.", submission_id_str)
            return

        cortex = CortexResult.model_validate(cortex_dict)
        artifact = submission.metadata_json.get("re_workbench_artifact", {})
        permissions = artifact.get("static_features", {}).get("permissions", [])
        sha256 = submission.sha256
        package = submission.package_name or "unknown"
        submission_webhook = submission.webhook_url

        fraud_chain = build_fraud_chain(cortex, permissions)
        client = get_minio_client()
        artifacts: dict[str, str] = {}
        # Per-artifact outcome so a missing artifact is diagnosable from the
        # API ("failed: <reason>" / "skipped: <reason>"), not a silent 404.
        artifact_status: dict[str, str] = {}

        # HTML report
        try:
            html = render_html(sha256, package, cortex, fraud_chain)
            artifacts["report_html"] = _put(
                client, f"{submission_id_str}/report.html", html.encode(), "text/html"
            )
            artifact_status["report_html"] = "success"
        except Exception as exc:
            logger.warning("HTML report failed: %s", exc)
            artifact_status["report_html"] = f"failed: {exc}"

        # PDF report
        try:
            pdf = render_pdf(sha256, package, cortex, fraud_chain)
            if pdf:
                artifacts["report_pdf"] = _put(
                    client, f"{submission_id_str}/report.pdf", pdf, "application/pdf"
                )
                artifact_status["report_pdf"] = "success"
            else:
                artifact_status["report_pdf"] = "skipped: PDF renderer unavailable"
        except Exception as exc:
            logger.warning("PDF report failed: %s", exc)
            artifact_status["report_pdf"] = f"failed: {exc}"

        # STIX bundle
        try:
            stix = build_stix_json(sha256, package, cortex)
            artifacts["stix"] = _put(
                client, f"{submission_id_str}/bundle.stix.json", stix.encode(), "application/json"
            )
            artifact_status["stix"] = "success"
        except Exception as exc:
            logger.warning("STIX export failed: %s", exc)
            artifact_status["stix"] = f"failed: {exc}"

        # YARA rule
        try:
            rule = generate_yara_rule(sha256, package, cortex, date=str(submission.created_at)[:10])
            if rule:
                artifacts["yara"] = _put(
                    client, f"{submission_id_str}/rule.yar", rule.encode(), "text/plain"
                )
                artifact_status["yara"] = "success"
            else:
                artifact_status["yara"] = "skipped: not enough distinctive strings"
        except Exception as exc:
            logger.warning("YARA generation failed: %s", exc)
            artifact_status["yara"] = f"failed: {exc}"

        # Fraud rules
        try:
            import json

            rules = generate_fraud_rules(sha256, package, cortex)
            artifacts["fraud_rules"] = _put(
                client,
                f"{submission_id_str}/fraud_rules.json",
                json.dumps(rules, indent=2).encode(),
                "application/json",
            )
            artifact_status["fraud_rules"] = "success"
        except Exception as exc:
            logger.warning("Fraud rule generation failed: %s", exc)
            artifact_status["fraud_rules"] = f"failed: {exc}"

        # Persist artifact index + fraud chain back onto the submission.
        meta = submission.metadata_json
        meta["delivery_artifacts"] = artifacts
        meta["delivery_artifacts_status"] = artifact_status
        meta["fraud_chain"] = fraud_chain
        submission.metadata_json = meta
        flag_modified(submission, "metadata_json")  # JSONB in-place mutation not tracked
        await db.commit()
        logger.info("Delivery complete for %s: %s", sha256, artifact_status)

    # Webhooks (outside the DB session).
    try:
        from parallax.delivery.webhook_dispatcher import (
            EVENT_ANALYSIS_COMPLETED,
            EVENT_VERDICT_CRITICAL,
            dispatch,
            dispatch_to_url,
        )

        payload = {
            "submission_id": submission_id_str,
            "sha256": sha256,
            "package": package,
            "verdict": cortex.verdict,
            "score": cortex.risk.calibrated_score,
            "artifacts": list(artifacts.keys()),
        }
        await dispatch(EVENT_ANALYSIS_COMPLETED, payload)
        if cortex.verdict == "CRITICAL":
            await dispatch(EVENT_VERDICT_CRITICAL, payload)
        # Per-submission subscriber (the webhook_url passed at submit time).
        if submission_webhook:
            await dispatch_to_url(submission_webhook, EVENT_ANALYSIS_COMPLETED, payload)
    except Exception as exc:
        logger.warning("Webhook dispatch failed: %s", exc)
