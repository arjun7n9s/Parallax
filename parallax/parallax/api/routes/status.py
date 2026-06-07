"""
Analysis status query endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.schemas.submission import SubmissionResponse
from parallax.core.database import get_session
from parallax.core.models import Submission

router = APIRouter(prefix="/analysis", tags=["Analyze"])


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_analysis_status(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get the status of an APK analysis by its submission ID.
    """
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    return submission
