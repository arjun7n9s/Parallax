"""Immutable PARALLAX evidence snapshot. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from uuid import UUID

from sqlalchemy import select

from parallax.agents.band.room_protocol import EvidenceBundleRef
from parallax.core.database import async_session
from parallax.core.models import IOC, Hypothesis, Observation, Submission, TaintFlow
from parallax.core.storage import get_minio_client

CASE_BUNDLE_BUCKET = "parallax-case-bundles"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _uuid(value: Any) -> str:
    return str(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def collect_submission_evidence(submission_id: str | UUID) -> dict[str, Any]:
    """Collect the current live DB evidence for a submission."""
    sid = UUID(str(submission_id))
    async with async_session() as db:
        submission = (await db.execute(select(Submission).where(Submission.id == sid))).scalar_one()
        hypotheses = (
            (await db.execute(select(Hypothesis).where(Hypothesis.submission_id == sid)))
            .scalars()
            .all()
        )
        observations = (
            (await db.execute(select(Observation).where(Observation.submission_id == sid)))
            .scalars()
            .all()
        )
        iocs = (await db.execute(select(IOC).where(IOC.submission_id == sid))).scalars().all()
        taint_flows = (
            (await db.execute(select(TaintFlow).where(TaintFlow.submission_id == sid)))
            .scalars()
            .all()
        )
    return build_evidence_bundle(
        submission=submission,
        hypotheses=hypotheses,
        observations=observations,
        iocs=iocs,
        taint_flows=taint_flows,
        snapshot_at=_utc_now(),
    )


def build_evidence_bundle(
    *,
    submission: Submission,
    hypotheses: list[Hypothesis],
    observations: list[Observation],
    iocs: list[IOC],
    taint_flows: list[TaintFlow],
    snapshot_at: datetime,
) -> dict[str, Any]:
    """Build the immutable JSON payload agents reason over."""
    metadata = submission.metadata_json or {}
    cortex = metadata.get("cortex_result") or {}
    confidence = metadata.get("confidence") or {}
    return {
        "schema_version": "1.0",
        "snapshot_at": snapshot_at.isoformat(),
        "evidence_stale_as_of": snapshot_at.isoformat(),
        "submission": {
            "id": _uuid(submission.id),
            "tenant_id": submission.tenant_id,
            "sha256": submission.sha256,
            "md5": submission.md5,
            "file_name": submission.file_name,
            "file_size": submission.file_size,
            "package_name": submission.package_name,
            "status": submission.status,
            "priority": submission.priority,
            "triage_score": submission.triage_score,
            "final_score": submission.final_score,
            "verdict": submission.verdict,
            "s3_path": submission.s3_path,
            "created_at": _iso(submission.created_at),
            "updated_at": _iso(submission.updated_at),
        },
        "metadata": {
            "permissions": metadata.get("permissions") or [],
            "target_sdk": metadata.get("target_sdk"),
            "launch_strategy": metadata.get("launch_strategy"),
            "frida_error": metadata.get("frida_error"),
            "confidence": confidence,
        },
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "claim": h.claim,
                "category": h.category,
                "initial_confidence": h.initial_confidence,
                "final_confidence": h.final_confidence,
                "effective_confidence": h.effective_confidence,
                "status": h.status,
                "status_reason": h.status_reason,
                "recommended_next_step": h.recommended_next_step,
                "formed_by_agent": h.formed_by_agent,
                "formed_at": _iso(h.formed_at),
                "resolved_at": _iso(h.resolved_at),
            }
            for h in hypotheses
        ],
        "observations": [
            {
                "id": _uuid(o.id),
                "source": o.source,
                "event_type": o.event_type,
                "thread_id": o.thread_id,
                "thread_name": o.thread_name,
                "caller_package": o.caller_package,
                "args": o.args,
                "return_value": o.return_value,
                "exception": o.exception,
                "captured_at_ms": o.captured_at_ms,
                "session_id": o.session_id,
                "created_at": _iso(o.created_at),
            }
            for o in observations
        ],
        "iocs": [
            {
                "id": _uuid(i.id),
                "ioc_type": i.ioc_type,
                "value": i.value,
                "context": i.context,
                "confidence": i.confidence,
                "source_agent": i.source_agent,
                "created_at": _iso(i.created_at),
            }
            for i in iocs
        ],
        "taint_flows": [flow.to_dict() for flow in taint_flows],
        "cortex_result": cortex,
        "risk": {
            "final_score": submission.final_score,
            "verdict": submission.verdict,
            "family": (cortex.get("intel_correlator") or {}).get("family_attribution"),
            "family_confidence": (cortex.get("intel_correlator") or {}).get("family_confidence"),
        },
    }


async def snapshot_evidence_bundle(submission_id: str | UUID) -> EvidenceBundleRef:
    """Write an immutable evidence bundle to MinIO and return its signed reference."""
    bundle = await collect_submission_evidence(submission_id)
    payload = json.dumps(bundle, indent=2, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    snapshot_at = _utc_now()
    object_name = (
        f"submissions/{submission_id}/bundle-"
        f"{snapshot_at.strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}.json"
    )

    client = get_minio_client()
    if not client.bucket_exists(CASE_BUNDLE_BUCKET):
        client.make_bucket(CASE_BUNDLE_BUCKET)
    client.put_object(
        CASE_BUNDLE_BUCKET,
        object_name,
        BytesIO(payload),
        len(payload),
        content_type="application/json",
    )
    url = client.presigned_get_object(CASE_BUNDLE_BUCKET, object_name, expires=timedelta(days=7))
    return EvidenceBundleRef(
        url=url,
        bucket=CASE_BUNDLE_BUCKET,
        object_name=object_name,
        sha256=digest,
        byte_size=len(payload),
        created_at=snapshot_at,
        stale_as_of=snapshot_at,
    )
