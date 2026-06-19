"""Band room transcript exporter. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

from parallax.agents.band.room_protocol import CaseRoom


def export_markdown(case_room: CaseRoom) -> str:
    """Render a compact audit transcript for demo artifacts."""
    lines = [
        f"# {case_room.case_id} Band Transcript",
        "",
        f"- Submission: `{case_room.submission_id}`",
        f"- Band room: `{case_room.band_room_id}`",
        f"- Bundle SHA-256: `{case_room.evidence_bundle.sha256}`",
        f"- Evidence stale as of: `{case_room.evidence_bundle.stale_as_of.isoformat()}`",
        "",
        "## Messages",
        "",
    ]
    for message in case_room.messages:
        mentions = ", ".join(message.mentions) or "-"
        lines.extend(
            [
                f"### {message.timestamp.isoformat()} - {message.sender_id}",
                "",
                f"- Type: `{message.message_type}`",
                f"- Mentions: {mentions}",
                "",
                message.body,
                "",
            ]
        )
    return "\n".join(lines)
