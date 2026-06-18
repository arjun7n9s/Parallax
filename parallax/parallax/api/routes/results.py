"""Analysis result + artifact retrieval endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.security import get_request_actor, get_request_tenant
from parallax.core.audit import write_audit_log
from parallax.core.config import settings
from parallax.core.database import get_session
from parallax.core.models import Submission
from parallax.core.storage import (
    QUARANTINE_BUCKET,
    REPORTS_BUCKET,
    get_minio_client,
    signed_get_url,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["results"])


async def _get_submission(submission_id: str, db: AsyncSession, tenant_id: str) -> Submission:
    try:
        sid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid submission id")
    result = await db.execute(
        select(Submission).where(
            Submission.id == sid,
            Submission.tenant_id == tenant_id,
        )
    )
    sub: Submission | None = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.get("/{submission_id}/result")
async def get_result(request: Request, submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    meta = sub.metadata_json or {}
    return {
        "submission_id": submission_id,
        "sha256": sub.sha256,
        "package_name": sub.package_name,
        "status": sub.status,
        "verdict": sub.verdict,
        "final_score": sub.final_score,
        "cortex_result": meta.get("cortex_result"),
        "fraud_chain": meta.get("fraud_chain"),
        "artifacts": meta.get("delivery_artifacts"),
    }


@router.get("/{submission_id}/irt")
async def get_irt(request: Request, submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    cortex = (sub.metadata_json or {}).get("cortex_result", {})
    return {"verdict": cortex.get("verdict"), "irt": cortex.get("irt", [])}


@router.get("/{submission_id}/fraud-chain")
async def get_fraud_chain(
    request: Request, submission_id: str, db: AsyncSession = Depends(get_session)
):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    return {"fraud_chain": (sub.metadata_json or {}).get("fraud_chain", [])}


def _fetch_artifact(submission_id: str, filename: str) -> bytes:
    client = get_minio_client()
    resp = None
    try:
        resp = client.get_object(REPORTS_BUCKET, f"{submission_id}/{filename}")
        return bytes(resp.read())
    except Exception:
        raise HTTPException(status_code=404, detail=f"Artifact {filename} not found")
    finally:
        if resp is not None:
            resp.close()
            resp.release_conn()


async def _audit_artifact_access(
    request: Request,
    db: AsyncSession,
    sub: Submission,
    action: str,
    artifact: str,
) -> None:
    await write_audit_log(
        db,
        tenant_id=get_request_tenant(request),
        actor=get_request_actor(request),
        action=action,
        submission_id=sub.id,
        detail={"artifact": artifact},
    )
    await db.commit()


@router.get("/{submission_id}/quarantine-url")
async def get_quarantine_url(
    request: Request, submission_id: str, db: AsyncSession = Depends(get_session)
):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    url = signed_get_url(QUARANTINE_BUCKET, f"{sub.sha256}.apk")
    await _audit_artifact_access(request, db, sub, "artifact.signed_url_issued", "quarantine_apk")
    return {
        "submission_id": submission_id,
        "artifact": "quarantine_apk",
        "expires_in_seconds": settings.SIGNED_URL_TTL_SECONDS,
        "url": url,
    }


@router.get("/{submission_id}/report.html")
async def get_report_html(
    request: Request, submission_id: str, db: AsyncSession = Depends(get_session)
):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    await _audit_artifact_access(request, db, sub, "artifact.downloaded", "report.html")
    return Response(_fetch_artifact(submission_id, "report.html"), media_type="text/html")


@router.get("/{submission_id}/report.pdf")
async def get_report_pdf(
    request: Request, submission_id: str, db: AsyncSession = Depends(get_session)
):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    await _audit_artifact_access(request, db, sub, "artifact.downloaded", "report.pdf")
    return Response(_fetch_artifact(submission_id, "report.pdf"), media_type="application/pdf")


@router.get("/{submission_id}/stix")
async def get_stix(request: Request, submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    await _audit_artifact_access(request, db, sub, "artifact.downloaded", "bundle.stix.json")
    return Response(
        _fetch_artifact(submission_id, "bundle.stix.json"), media_type="application/json"
    )


@router.get("/{submission_id}/yara")
async def get_yara(request: Request, submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    await _audit_artifact_access(request, db, sub, "artifact.downloaded", "rule.yar")
    return Response(_fetch_artifact(submission_id, "rule.yar"), media_type="text/plain")


@router.get("/{submission_id}/fraud-rules")
async def get_fraud_rules(
    request: Request, submission_id: str, db: AsyncSession = Depends(get_session)
):
    sub = await _get_submission(submission_id, db, get_request_tenant(request))
    await _audit_artifact_access(request, db, sub, "artifact.downloaded", "fraud_rules.json")
    return Response(
        _fetch_artifact(submission_id, "fraud_rules.json"), media_type="application/json"
    )
