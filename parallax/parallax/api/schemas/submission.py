"""
Pydantic schemas for APK submission data contracts.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubmissionBase(BaseModel):
    """Base fields shared across submission models."""

    file_name: str
    file_size: int


class SubmissionCreate(SubmissionBase):
    """Internal model for creating a submission record before DB persistence."""

    sha256: str
    md5: str
    s3_path: str


class SubmissionResponse(SubmissionBase):
    """API response model for an analysis submission."""

    id: UUID
    sha256: str
    md5: str
    package_name: str | None = None
    status: str
    priority: str
    triage_score: float | None = None
    final_score: float | None = None
    verdict: str | None = None
    created_at: datetime
    updated_at: datetime

    # Expose metadata_json as just metadata if present
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_json")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
