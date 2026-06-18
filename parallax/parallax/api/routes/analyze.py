"""
APK submission and analysis triggering endpoints.
"""

import hashlib
import os
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.idempotency import lookup_submission_id, remember_submission_id
from parallax.api.schemas.submission import SubmissionResponse
from parallax.core.config import settings
from parallax.core.database import get_session
from parallax.core.models import Submission
from parallax.core.storage import APK_BUCKET, get_minio_client

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# APK files are ZIP archives — the first 4 bytes are always the PK magic header.
_APK_MAGIC = b"PK\x03\x04"


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_apk(
    file: Annotated[UploadFile, File(...)],
    db: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """
    Submit an APK for analysis.
    Computes hashes, stores the original binary in MinIO, and queues for triage.

    Supplying an ``Idempotency-Key`` header makes retries safe: the same key
    within 24h returns the original submission instead of creating a duplicate.
    """
    if not file.filename or not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are supported.")

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

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5(usedforsecurity=False)
    file_size = 0
    temp_file_path: str | None = None

    try:
        # Write to a temporary file while hashing — avoids loading large APKs entirely in memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".apk") as temp_file:
            temp_file_path = temp_file.name
            is_first_chunk = True

            while chunk := await file.read(8192):
                file_size += len(chunk)

                # Enforce file size limit
                if file_size > max_bytes:
                    msg = f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                    raise HTTPException(status_code=413, detail=msg)

                # Validate APK magic bytes from the first chunk
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

        # Check if this SHA256 already exists (dedup)
        existing = await db.execute(select(Submission).where(Submission.sha256 == sha256_hex))
        if existing_sub := existing.scalar_one_or_none():
            return existing_sub

        s3_path = f"s3://{APK_BUCKET}/{sha256_hex}.apk"

        # Upload to MinIO
        get_minio_client().fput_object(
            bucket_name=APK_BUCKET,
            object_name=f"{sha256_hex}.apk",
            file_path=temp_file_path,
            content_type="application/vnd.android.package-archive",
        )

        # Create submission record
        new_submission = Submission(
            id=uuid.uuid4(),
            sha256=sha256_hex,
            md5=md5_hex,
            file_name=file.filename,
            file_size=file_size,
            status="queued",
            priority="normal",
            s3_path=s3_path,
        )

        db.add(new_submission)
        await db.commit()
        # Enqueue Celery task for triaging
        from parallax.workers.triage_worker import run_triage_pipeline

        run_triage_pipeline.delay(str(new_submission.id))

        # Bind the idempotency key so a retry returns this same submission.
        if idempotency_key and idem_client is not None:
            remember_submission_id(idem_client, idempotency_key, str(new_submission.id))

        return new_submission

    except HTTPException:
        raise  # Re-raise our own validation errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process APK submission: {str(e)}")
    finally:
        # Always clean up the temp file — even on error
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
