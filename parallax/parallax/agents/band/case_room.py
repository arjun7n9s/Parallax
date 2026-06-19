"""Case room lifecycle helpers. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

from parallax.agents.band.agents import agent_by_role, participant_refs
from parallax.agents.band.band_adapter import BandAdapter
from parallax.agents.band.evidence_bundle import snapshot_evidence_bundle
from parallax.agents.band.room_protocol import AgentMessage, CaseRoom, EvidenceBundleRef

logger = logging.getLogger(__name__)

SnapshotFn = Callable[[str], Awaitable[EvidenceBundleRef]]


def _case_id() -> str:
    return f"CASE-FR-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"


async def open_case_room(
    submission_id: str,
    *,
    case_id: str | None = None,
    adapter: BandAdapter | None = None,
    snapshot_fn: SnapshotFn = snapshot_evidence_bundle,
) -> CaseRoom:
    """Snapshot evidence, create a Band room, and post the case-open message."""
    case_id = case_id or _case_id()
    adapter = adapter or BandAdapter()
    evidence_bundle = await snapshot_fn(submission_id)
    participants = participant_refs()
    room = adapter.create_chatroom(name=f"PARALLAX {case_id}", participants=participants)
    room_id = str(room["id"])

    intake = agent_by_role("intake").participant_ref
    body = (
        f"Case {case_id} opened. Immutable evidence bundle "
        f"{evidence_bundle.sha256[:12]} is available for review. "
        "Specialist agents are recruited for bounded adversarial investigation."
    )
    message = AgentMessage(
        message_type="request",
        sender_id=intake,
        sender_type="agent",
        body=body,
        mentions=participants,
        bundle_sha256=evidence_bundle.sha256,
    )
    adapter.post_message(
        room_id,
        sender_id=intake,
        body=body,
        mentions=participants,
        metadata=message.model_dump(mode="json"),
    )

    logger.info("Opened Band case room %s for submission %s", room_id, submission_id)
    return CaseRoom(
        case_id=case_id,
        submission_id=submission_id,
        band_room_id=room_id,
        evidence_bundle=evidence_bundle,
        participants=participants,
        messages=[message],
    )
