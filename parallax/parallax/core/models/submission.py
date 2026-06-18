"""
SQLAlchemy ORM models for PARALLAX core tables.

These are the foundational tables required by Phase 0.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from parallax.core.database import Base


class Submission(Base):
    """An APK submitted for analysis."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    md5: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    package_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "queued",
            "triaging",
            "static",
            "dynamic",
            "reasoning",
            "complete",
            "failed",
            name="analysis_status",
        ),
        default="queued",
    )
    priority: Mapped[str] = mapped_column(
        Enum("critical", "high", "normal", "low", name="analysis_priority"),
        default="normal",
    )
    triage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    s3_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Optional per-submission completion webhook (HMAC-signed POST on terminal status).
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Groups submissions made together via POST /analyze/batch. Null = single submit.
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IOC(Base):
    """Indicator of Compromise extracted from an analysis."""

    __tablename__ = "iocs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ioc_type: Mapped[str] = mapped_column(
        Enum("ip", "domain", "url", "hash", "email", "certificate", "yara_rule", name="ioc_type"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Immutable audit trail for every system action."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)  # agent name or "system"
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
