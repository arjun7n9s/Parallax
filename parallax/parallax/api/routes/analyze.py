"""
APK submission and analysis triggering endpoints (single + batch).
"""

import hashlib
import os
import tempfile
import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.idempotency import lookup_submission_id, remember_submission_id
from parallax.api.schemas.submission import (
    BatchStatusResponse,
    BatchSubmissionResponse,
    SubmissionResponse,
)
from parallax.core.config import settings
from parallax.core.database import get_session
from parallax.core.models import Submission
from parallax.core.storage import APK_BUCKET, get_minio_client

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# APK files are ZIP archives — the first 4 bytes are always the PK magic header.
_APK_MAGIC = b"PK\x03\x04"

# A single batch may carry at most this many APKs (bounds memory + queue burst).
_MAX_BATCH = 100


async def _ingest_apk(
    file: UploadFile,
    db: AsyncSession,
    *,
    webhook_url: str | None = None,
    batch_id: uuid.UUID | None = None,
) -> Submission:
    """Stream-hash, dedup, store, and queue one APK. Returns the (possibly
    pre-existing) Submission. Raises HTTPException on a client/validation error.

    Shared by the single and batch endpoints so both have identical ingest
    semantics (magic-byte check, size limit, sha256 content dedup)."""
    if not file.filename or not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are supported.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5(usedforsecurity=False)
    file_size = 0
    temp_file_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".apk") as temp_file:
            temp_file_path = temp_file.name
            is_first_chunk = True
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )
                if is_first_chunk:
                    if not chunk[:4].startswith(_APK_MAGIC):
                        raise HTTPException(
                            status_code=400,
                            detail="File does not appear to be a valid APK (invalid magic bytes).",
                        )
                    is_first_chunk = False
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
                temp_file.write(chunk)

        sha256_hex = sha256_hash.hexdigest()
        md5_hex = md5_hash.hexdigest()

        # Content dedup: an identical APK reuses its existing submission.
        existing = await db.execute(select(Submission).where(Submission.sha256 == sha256_hex))
        existing_sub = cast(Submission | None, existing.scalar_one_or_none())
        if existing_sub:
            return existing_sub

        s3_path = f"s3://{APK_BUCKET}/{sha256_hex}.apk"
        get_minio_client().fput_object(
            bucket_name=APK_BUCKET,
            object_name=f"{sha256_hex}.apk",
            file_path=temp_file_path,
            content_type="application/vnd.android.package-archive",
        )

        new_submission = Submission(
            id=uuid.uuid4(),
            sha256=sha256_hex,
            md5=md5_hex,
            file_name=file.filename,
            file_size=file_size,
            status="queued",
            priority="normal",
            s3_path=s3_path,
            webhook_url=webhook_url or None,
            batch_id=batch_id,
        )
        db.add(new_submission)
        await db.commit()

        from parallax.workers.triage_worker import run_triage_pipeline

        run_triage_pipeline.delay(str(new_submission.id))
        return new_submission
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit one APK for analysis",
    description=(
        "Upload one APK, persist the binary to object storage, deduplicate by SHA-256, "
        "and enqueue triage. Optional `webhook_url` receives a signed completion payload. "
        "Use `Idempotency-Key` for safe client retries."
    ),
    responses={
        400: {"description": "The uploaded file is not an APK or has invalid APK magic bytes."},
        413: {"description": "The APK exceeds the configured upload size limit."},
        500: {"description": "Storage or queueing failed while processing the submission."},
    },
)
async def submit_apk(
    file: Annotated[UploadFile, File(...)],
    db: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    webhook_url: Annotated[str | None, Form()] = None,
):
    """
    Submit an APK for analysis.
    Computes hashes, stores the original binary in MinIO, and queues for triage.

    Supplying an ``Idempotency-Key`` header makes retries safe: the same key
    within 24h returns the original submission instead of creating a duplicate.
    An optional ``webhook_url`` form field receives the signed result on completion.
    """
    # Idempotency-Key short-circuit: a retried request returns the same submission
    # without re-uploading or re-hashing. Redis-backed; degrades gracefully.
    idem_client = None
    if idempotency_key:
        try:
            from parallax.workers.heartbeat import get_redis

            idem_client = get_redis()
            prior_id = lookup_submission_id(idem_client, idempotency_key)
            if prior_id:
                prior = await db.execute(select(Submission).where(Submission.id == prior_id))
                if prior_sub := prior.scalar_one_or_none():
                    return prior_sub
        except Exception:  # noqa: BLE001 - idempotency is best-effort
            idem_client = None

    try:
        new_submission = await _ingest_apk(file, db, webhook_url=webhook_url)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to process APK submission: {e}")

    if idempotency_key and idem_client is not None:
        remember_submission_id(idem_client, idempotency_key, str(new_submission.id))
    return new_submission


@router.post(
    "/batch",
    response_model=BatchSubmissionResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a batch of APKs",
    description=(
        "Upload up to 100 APKs in one request. Each file is validated independently; "
        "bad files are reported inline and do not abort the rest of the batch."
    ),
    responses={
        400: {"description": "No files were supplied or the batch exceeds the 100-APK limit."}
    },
)
async def submit_batch(
    files: Annotated[list[UploadFile], File(...)],
    db: AsyncSession = Depends(get_session),
    webhook_url: Annotated[str | None, Form()] = None,
):
    """
    Submit up to 100 APKs as one batch. Returns a ``batch_id`` plus a per-file
    outcome. A file that fails validation is reported inline and does not abort
    the rest of the batch. Track progress via ``GET /analyze/batch/{batch_id}``.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > _MAX_BATCH:
        raise HTTPException(
            status_code=400, detail=f"Batch size exceeds the {_MAX_BATCH}-APK limit."
        )

    batch_id = uuid.uuid4()
    results: list[dict] = []
    for f in files:
        try:
            sub = await _ingest_apk(f, db, webhook_url=webhook_url, batch_id=batch_id)
            results.append(
                {"file_name": f.filename, "submission_id": str(sub.id), "status": sub.status}
            )
        except HTTPException as exc:
            results.append({"file_name": f.filename, "error": exc.detail})
        except Exception as exc:  # noqa: BLE001
            results.append({"file_name": f.filename, "error": str(exc)})

    accepted = sum(1 for r in results if "submission_id" in r)
    return {
        "batch_id": str(batch_id),
        "total": len(files),
        "submitted": accepted,
        "results": results,
    }


@router.get(
    "/batch/{batch_id}",
    response_model=BatchStatusResponse,
    response_model_exclude_none=True,
    summary="Get batch analysis status",
    description=("Return per-sample progress, verdicts and aggregate status counts for a batch."),
    responses={404: {"description": "The batch id is unknown."}},
)
async def batch_status(batch_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    """Per-sample progress + verdicts for a batch. 404 if the batch is unknown."""
    res = await db.execute(select(Submission).where(Submission.batch_id == batch_id))
    subs = list(res.scalars().all())
    if not subs:
        raise HTTPException(status_code=404, detail="Batch not found.")

    terminal = {"complete", "failed"}
    by_status: dict[str, int] = {}
    items = []
    for s in subs:
        by_status[s.status] = by_status.get(s.status, 0) + 1
        items.append(
            {
                "submission_id": str(s.id),
                "file_name": s.file_name,
                "status": s.status,
                "verdict": s.verdict,
                "score": s.final_score,
            }
        )
    return {
        "batch_id": str(batch_id),
        "total": len(subs),
        "by_status": by_status,
        "complete": all(s.status in terminal for s in subs),
        "submissions": items,
    }
