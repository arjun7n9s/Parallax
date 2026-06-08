"""
APK submission and analysis triggering endpoints.
"""

import hashlib
import os
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
):
    """
    Submit an APK for analysis.
    Computes hashes, stores the original binary in MinIO, and queues for triage.
    """
    if not file.filename or not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are supported.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
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
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )

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
        await db.refresh(new_submission)

        # TODO: Enqueue Celery task for triaging

        return new_submission

    except HTTPException:
        raise  # Re-raise our own validation errors
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process APK submission: {str(e)}"
        )
    finally:
        # Always clean up the temp file — even on error
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
