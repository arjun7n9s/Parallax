"""
APK submission and analysis triggering endpoints.
"""

import hashlib
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.schemas.submission import SubmissionResponse
from parallax.core.database import get_session
from parallax.core.models import Submission
from parallax.core.storage import APK_BUCKET, minio_client

router = APIRouter(prefix="/analyze", tags=["Analyze"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_apk(
    file: Annotated[UploadFile, File(...)],
    db: AsyncSession = Depends(get_session),
):
    """
    Submit an APK for analysis.
    Computes hashes, stores the original binary in MinIO, and queues for triage.
    """
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are supported.")

    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    file_size = 0

    # Write to a temporary file while hashing to avoid loading large APKs entirely in memory
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        while chunk := await file.read(8192):
            sha256_hash.update(chunk)
            md5_hash.update(chunk)
            temp_file.write(chunk)
            file_size += len(chunk)
        temp_file_path = temp_file.name

    sha256_hex = sha256_hash.hexdigest()
    md5_hex = md5_hash.hexdigest()

    # Check if this SHA256 already exists
    existing = await db.execute(select(Submission).where(Submission.sha256 == sha256_hex))
    if existing_sub := existing.scalar_one_or_none():
        # Clean up temp file
        import os

        os.unlink(temp_file_path)
        return existing_sub

    s3_path = f"s3://{APK_BUCKET}/{sha256_hex}.apk"

    # Upload to MinIO
    try:
        minio_client.fput_object(
            bucket_name=APK_BUCKET,
            object_name=f"{sha256_hex}.apk",
            file_path=temp_file_path,
            content_type="application/vnd.android.package-archive",
        )
    except Exception as e:
        import os

        os.unlink(temp_file_path)
        raise HTTPException(
            status_code=500, detail=f"Failed to store APK in object storage: {str(e)}"
        )

    # Clean up temp file
    import os

    os.unlink(temp_file_path)

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
