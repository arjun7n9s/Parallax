import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from parallax.core.database import Base


class Observation(Base):
    """
    A generic dynamic observation captured during sandbox execution.
    Can come from Frida hooks, mitmproxy, or ADB logcat.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "frida", "mitmproxy", "logcat", "strace"
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    # Specific hook name, API call, or network destination (e.g. "SmsManager.sendTextMessage")
    event_type: Mapped[str] = mapped_column(String(256), nullable=False)

    # Process/Thread metadata
    thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thread_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    caller_package: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Captured JSON arguments/payloads
    args: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    return_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exception: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    captured_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentObservationLink(Base):
    """
    Join table linking an Observation to the Hypothesis that specifically asked for it.
    This resolves Option B in the architecture document.
    """

    __tablename__ = "experiment_observation_links"

    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hypotheses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Could be useful to know if this observation directly proved/disproved it,
    # but initially just records that the observation was triggered by this experiment.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
