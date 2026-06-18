"""
Endpoint for fetching the status of an ongoing or completed analysis.
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.schemas.submission import SubmissionResponse
from parallax.api.security import get_request_tenant
from parallax.core.database import get_session
from parallax.core.models import Hypothesis, Submission

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/{submission_id}", response_model=dict[str, Any])
async def get_analysis_status(
    request: Request, submission_id: uuid.UUID, db: AsyncSession = Depends(get_session)
):
    """
    Fetch the current status of an analysis, including triage score and active hypotheses.
    """
    tenant_id = get_request_tenant(request)
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.tenant_id == tenant_id,
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Fetch related hypotheses for V2
    hypotheses_result = await db.execute(
        select(Hypothesis).where(Hypothesis.apk_sha256 == submission.sha256)
    )
    hypotheses = hypotheses_result.scalars().all()

    response_data = SubmissionResponse.model_validate(submission).model_dump(mode="json")

    # Append hypothesis engine data
    response_data["hypotheses"] = [
        {
            "id": h.hypothesis_id,
            "claim": h.claim,
            "status": h.status,
            "confidence": h.effective_confidence,
            "irt_label": h.irt_label,
        }
        for h in hypotheses
        if h.expose_in_irt
    ]

    return response_data


@router.get("/{submission_id}/stream")
async def stream_analysis_status(request: Request, submission_id: uuid.UUID):
    """
    Server-Sent Events (SSE) endpoint for individual analysis status.
    Streams the full submission detail and hypotheses, updating every 2 seconds.
    """

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            from parallax.core.database import async_session_maker

            async with async_session_maker() as session:
                tenant_id = get_request_tenant(request)
                result = await session.execute(
                    select(Submission).where(
                        Submission.id == submission_id,
                        Submission.tenant_id == tenant_id,
                    )
                )
                submission = result.scalar_one_or_none()

                if not submission:
                    break

                hypotheses_result = await session.execute(
                    select(Hypothesis).where(Hypothesis.apk_sha256 == submission.sha256)
                )
                hypotheses = hypotheses_result.scalars().all()

                response_data = SubmissionResponse.model_validate(submission).model_dump(
                    mode="json"
                )
                response_data["hypotheses"] = [
                    {
                        "id": h.hypothesis_id,
                        "claim": h.claim,
                        "status": h.status,
                        "confidence": h.effective_confidence,
                        "irt_label": h.irt_label,
                    }
                    for h in hypotheses
                    if h.expose_in_irt
                ]

                yield f"data: {json.dumps(response_data)}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
