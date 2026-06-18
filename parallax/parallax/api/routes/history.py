"""
Paginated analysis history endpoint.
"""

from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from parallax.api.schemas.submission import SubmissionResponse
from parallax.api.security import get_request_tenant
from parallax.core.database import get_session
from parallax.core.models import Submission


class AnalysisStatusFilter(str, Enum):
    queued = "queued"
    triaging = "triaging"
    static = "static"
    dynamic = "dynamic"
    reasoning = "reasoning"
    complete = "complete"
    failed = "failed"


router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=dict)
async def get_analysis_history(
    request: Request,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    status_filter: Annotated[
        AnalysisStatusFilter | None, Query(alias="status", description="Filter by analysis status")
    ] = None,
    db: AsyncSession = Depends(get_session),
):
    """
    Get paginated list of past analyses.

    Returns submissions ordered by most recent first, with total count for pagination.
    """
    query = select(Submission).where(Submission.tenant_id == get_request_tenant(request))

    if status_filter:
        query = query.where(Submission.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    query = query.order_by(Submission.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    submissions = result.scalars().all()

    return {
        "items": [SubmissionResponse.model_validate(s) for s in submissions],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }
