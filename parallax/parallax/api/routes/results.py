"""Analysis result + artifact retrieval endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.core.database import get_session
from parallax.core.models import Submission
from parallax.core.storage import REPORTS_BUCKET, get_minio_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["results"])


async def _get_submission(submission_id: str, db: AsyncSession) -> Submission:
    try:
        sid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid submission id")
    result = await db.execute(select(Submission).where(Submission.id == sid))
    sub: Submission | None = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.get("/{submission_id}/result")
async def get_result(submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db)
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
async def get_irt(submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db)
    cortex = (sub.metadata_json or {}).get("cortex_result", {})
    return {"verdict": cortex.get("verdict"), "irt": cortex.get("irt", [])}


@router.get("/{submission_id}/fraud-chain")
async def get_fraud_chain(submission_id: str, db: AsyncSession = Depends(get_session)):
    sub = await _get_submission(submission_id, db)
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


@router.get("/{submission_id}/report.html")
async def get_report_html(submission_id: str):
    return Response(_fetch_artifact(submission_id, "report.html"), media_type="text/html")


@router.get("/{submission_id}/report.pdf")
async def get_report_pdf(submission_id: str):
    return Response(_fetch_artifact(submission_id, "report.pdf"), media_type="application/pdf")


@router.get("/{submission_id}/stix")
async def get_stix(submission_id: str):
    return Response(
        _fetch_artifact(submission_id, "bundle.stix.json"), media_type="application/json"
    )


@router.get("/{submission_id}/yara")
async def get_yara(submission_id: str):
    return Response(_fetch_artifact(submission_id, "rule.yar"), media_type="text/plain")


@router.get("/{submission_id}/fraud-rules")
async def get_fraud_rules(submission_id: str):
    return Response(
        _fetch_artifact(submission_id, "fraud_rules.json"), media_type="application/json"
    )
