"""Structured room message protocol. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

MessageType = Literal["evidence", "hypothesis", "challenge", "request", "decision", "escalation"]
SenderType = Literal["agent", "human", "system"]
ChallengeSeverity = Literal["minor", "major", "blocking"]
ChallengeStatus = Literal["pending", "accepted", "rejected", "escalated", "expired"]
CaseRoomStatus = Literal["open", "provisional", "converged", "escalated", "approved"]
DecisionStatus = Literal["provisional", "final", "escalated"]


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceRef(BaseModel):
    """Pointer into an immutable PARALLAX evidence bundle."""

    evidence_id: str
    evidence_type: str
    path: str
    summary: str = ""


class EvidenceBundleRef(BaseModel):
    """Immutable evidence bundle location and integrity metadata."""

    url: HttpUrl | str
    bucket: str
    object_name: str
    sha256: str = Field(min_length=64, max_length=64)
    byte_size: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    stale_as_of: datetime = Field(default_factory=utc_now)
    content_type: str = "application/json"


class EvidenceClaim(BaseModel):
    """A single factual claim an agent makes about evidence."""

    claim_id: str = Field(default_factory=lambda: _short_id("claim"))
    claim_text: str = Field(min_length=1)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    agent_id: str = Field(min_length=1)
    supports_or_contradicts: list[str] = Field(default_factory=list)


class Challenge(BaseModel):
    """One agent disputes another agent's claim."""

    challenge_id: str = Field(default_factory=lambda: _short_id("chal"))
    target_claim_id: str = Field(min_length=1)
    challenger_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    severity: ChallengeSeverity
    status: ChallengeStatus = "pending"
    deadline_turns: int = Field(default=2, ge=1)
    deadline_seconds: int = Field(default=120, ge=1)
    resolution_text: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.status == "pending"


class AgentMessage(BaseModel):
    """One structured message in a Band case room."""

    message_id: str = Field(default_factory=lambda: _short_id("msg"))
    message_type: MessageType
    timestamp: datetime = Field(default_factory=utc_now)
    sender_id: str = Field(min_length=1)
    sender_type: SenderType
    body: str = Field(min_length=1)
    mentions: list[str] = Field(default_factory=list)
    attached_claims: list[EvidenceClaim] = Field(default_factory=list)
    attached_challenges: list[Challenge] = Field(default_factory=list)
    bundle_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class ActionPacket(BaseModel):
    """Final or provisional action packet awaiting human approval."""

    decision_id: str = Field(default_factory=lambda: _short_id("decision"))
    status: DecisionStatus
    summary: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)
    unresolved_challenge_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class CaseRoom(BaseModel):
    """PARALLAX case room state mirrored to Band."""

    case_id: str = Field(min_length=1)
    submission_id: str = Field(min_length=1)
    band_room_id: str
    evidence_bundle: EvidenceBundleRef
    created_at: datetime = Field(default_factory=utc_now)
    status: CaseRoomStatus = "open"
    participants: list[str] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    final_action_packet: ActionPacket | None = None

    @field_validator("participants")
    @classmethod
    def _unique_participants(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @property
    def open_challenges(self) -> list[Challenge]:
        return [
            challenge
            for message in self.messages
            for challenge in message.attached_challenges
            if challenge.is_open
        ]
