"""Tests for PARALLAX x Band room protocol models."""

from __future__ import annotations

from parallax.agents.band.room_protocol import (
    AgentMessage,
    CaseRoom,
    Challenge,
    EvidenceBundleRef,
)


def _bundle() -> EvidenceBundleRef:
    return EvidenceBundleRef(
        url="https://example.test/bundle.json",
        bucket="parallax-case-bundles",
        object_name="submissions/s1/bundle.json",
        sha256="a" * 64,
        byte_size=128,
    )


def test_challenge_open_property_tracks_status():
    challenge = Challenge(
        target_claim_id="claim-1",
        challenger_id="validator",
        reason="Accessibility permission alone is insufficient.",
        severity="major",
    )

    assert challenge.is_open is True
    challenge.status = "accepted"
    assert challenge.is_open is False


def test_case_room_deduplicates_participants_and_lists_open_challenges():
    challenge = Challenge(
        target_claim_id="claim-1",
        challenger_id="validator",
        reason="Show timeline evidence.",
        severity="blocking",
    )
    message = AgentMessage(
        message_type="challenge",
        sender_id="validator",
        sender_type="agent",
        body="Need timeline proof.",
        attached_challenges=[challenge],
    )

    room = CaseRoom(
        case_id="CASE-FR-2026-00421",
        submission_id="sub-1",
        band_room_id="room-1",
        evidence_bundle=_bundle(),
        participants=["a", "a", "b"],
        messages=[message],
    )

    assert room.participants == ["a", "b"]
    assert room.open_challenges == [challenge]
