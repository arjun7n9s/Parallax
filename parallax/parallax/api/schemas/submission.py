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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54",
                "file_name": "sample.apk",
                "file_size": 2489132,
                "sha256": "a" * 64,
                "md5": "b" * 32,
                "package_name": "com.example.app",
                "status": "queued",
                "priority": "normal",
                "triage_score": None,
                "final_score": None,
                "verdict": None,
                "created_at": "2026-06-18T10:00:00Z",
                "updated_at": "2026-06-18T10:00:00Z",
                "metadata": None,
            }
        },
    )


class BatchSubmissionResult(BaseModel):
    """Per-file outcome returned by batch submission."""

    file_name: str | None = None
    submission_id: str | None = None
    status: str | None = None
    error: str | None = None


class BatchSubmissionResponse(BaseModel):
    """Response returned by POST /analyze/batch."""

    batch_id: str
    total: int
    submitted: int
    results: list[BatchSubmissionResult]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "60c97ebb-a5cc-462d-84ba-ef2200f21b08",
                "total": 2,
                "submitted": 1,
                "results": [
                    {
                        "file_name": "sample-1.apk",
                        "submission_id": "6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54",
                        "status": "queued",
                    },
                    {
                        "file_name": "not-an-apk.txt",
                        "error": "Only .apk files are supported.",
                    },
                ],
            }
        }
    )


class BatchStatusItem(BaseModel):
    submission_id: str
    file_name: str
    status: str
    verdict: str | None = None
    score: float | None = None


class BatchStatusResponse(BaseModel):
    """Per-sample status returned by GET /analyze/batch/{batch_id}."""

    batch_id: str
    total: int
    by_status: dict[str, int]
    complete: bool
    submissions: list[BatchStatusItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "60c97ebb-a5cc-462d-84ba-ef2200f21b08",
                "total": 2,
                "by_status": {"complete": 1, "dynamic": 1},
                "complete": False,
                "submissions": [
                    {
                        "submission_id": "6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54",
                        "file_name": "sample-1.apk",
                        "status": "complete",
                        "verdict": "HIGH",
                        "score": 78.0,
                    },
                    {
                        "submission_id": "2c404c37-fc5b-46ad-98f6-1f6f9a0da013",
                        "file_name": "sample-2.apk",
                        "status": "dynamic",
                    },
                ],
            }
        }
    )
