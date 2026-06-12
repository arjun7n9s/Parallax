import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from parallax.core.database import Base


class TaintFlow(Base):
    """
    A FlowDroid static taint flow: sensitive data travelling from a source
    API (SMS body, contacts, location, ...) to a sink (network, file, IPC).
    Produced by the static worker, consumed by the Reasoning Cortex.
    """

    __tablename__ = "taint_flows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_class: Mapped[str] = mapped_column(String(512), nullable=False)
    source_method: Mapped[str] = mapped_column(String(256), nullable=False)
    sink_class: Mapped[str] = mapped_column(String(512), nullable=False)
    sink_method: Mapped[str] = mapped_column(String(256), nullable=False)

    # Intermediate methods on the source->sink path
    path: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    risk: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM", index=True)
    attck_technique: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "source": f"{self.source_class}.{self.source_method}",
            "sink": f"{self.sink_class}.{self.sink_method}",
            "path": self.path or [],
            "risk": self.risk,
            "attck_technique": self.attck_technique,
        }
