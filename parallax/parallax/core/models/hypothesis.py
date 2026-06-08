import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from parallax.core.database import Base


class Hypothesis(Base):
    """
    Persists every hypothesis the Hypothesis Engine forms during an investigation.
    Links to the APK being analyzed and to the Experiments that test it.
    """

    __tablename__ = "hypotheses"

    hypothesis_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), index=True
    )
    apk_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    claim: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    initial_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    final_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    unresolved_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)

    formed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    expose_in_irt: Mapped[bool] = mapped_column(Boolean, default=False)
    irt_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    formed_by_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    spawned_from: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("hypotheses.hypothesis_id", ondelete="SET NULL"), nullable=True
    )

    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment", back_populates="hypothesis", cascade="all, delete-orphan"
    )

    @property
    def effective_confidence(self) -> float:
        val = self.initial_confidence if self.final_confidence is None else self.final_confidence
        return float(val)


class Experiment(Base):
    """
    One Experiment is one action taken to test a Hypothesis.
    """

    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("hypotheses.hypothesis_id", ondelete="CASCADE"), index=True
    )

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_used: Mapped[str] = mapped_column(String(64), nullable=False)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Float, nullable=True)  # ms

    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_citations: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_attempts: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    hypothesis: Mapped[Hypothesis] = relationship("Hypothesis", back_populates="experiments")
