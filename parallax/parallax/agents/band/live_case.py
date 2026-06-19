"""Open a REAL Band case room from a completed PARALLAX submission.

Unlike demo_case.py (synthetic, offline transcript), this drives the *live*
Band platform: it reads a real submission's analysis from the PARALLAX DB,
snapshots an immutable evidence bundle, creates a Band chat room via the agent
REST API, adds the specialist agents as participants, and posts an intake
message carrying the real findings (the connected remote agents reason over the
message content, so the evidence must be in the body — a bundle URL alone is
not something an LLM can fetch).

The remote agents started by band_orchestrator.py then collaborate in the room.

Usage:
    .venv-band/Scripts/python -m parallax.agents.band.live_case <submission_id>
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re

from parallax.agents.band.agents import AGENT_ROSTER, agent_by_role
from parallax.agents.band.evidence_bundle import (
    collect_submission_evidence,
    snapshot_evidence_bundle,
)
from parallax.core.config import settings

logger = logging.getLogger(__name__)

_IP_RE = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")


def _defang(text: str) -> str:
    """Neutralize live IOCs (URLs/IPs) so the Band platform's WAF doesn't reject
    the message, while keeping them human/agent-readable. Standard threat-intel
    defanging — the agents understand hxxp / [.] notation."""
    text = text.replace("https://", "hxxps[://]").replace("http://", "hxxp[://]")
    text = _IP_RE.sub(lambda m: "[.]".join(m.groups()), text)
    return text


def _fmt_iocs(iocs: list[dict], limit: int = 8) -> str:
    rows = [f"  - {i.get('ioc_type')}: {i.get('value')}" for i in iocs[:limit]]
    extra = f"\n  - (+{len(iocs) - limit} more)" if len(iocs) > limit else ""
    return ("\n".join(rows) + extra) if rows else "  - none extracted"


def build_intake_message(bundle: dict) -> str:
    """Compose the real case-opening message from a PARALLAX evidence bundle."""
    sub = bundle.get("submission", {})
    risk = bundle.get("risk", {})
    cortex = bundle.get("cortex_result", {}) or {}
    meta = bundle.get("metadata", {}) or {}
    perms = [p for p in (meta.get("permissions") or []) if "permission" in p][:10]
    findings = (cortex.get("technical_findings") or [])[:5]
    attck = (cortex.get("attck_techniques") or [])[:8]
    iocs = bundle.get("iocs", [])

    mentions = " ".join(f"@{a.handle}" for a in AGENT_ROSTER if a.role != "intake")
    finding_lines = [f"  - {f}" for f in findings] or ["  - (see evidence bundle)"]
    lines = [
        f"**PARALLAX case opened — {sub.get('package_name') or sub.get('file_name')}**",
        f"Immutable evidence bundle sha256 `{bundle.get('_bundle_sha256','')[:16]}` "
        f"(snapshot {bundle.get('snapshot_at','')}).",
        "",
        f"- APK sha256: `{sub.get('sha256','')}`",
        f"- Verdict: **{risk.get('verdict') or sub.get('verdict')}**  "
        f"(score {risk.get('final_score') or sub.get('final_score')}/100)",
        f"- Family attribution: {risk.get('family') or 'unattributed'} "
        f"(conf {risk.get('family_confidence') or 0})",
        f"- Dangerous permissions: {', '.join(perms) or 'none flagged'}",
        f"- ATT&CK: {', '.join(attck) or 'none mapped'}",
        "",
        "Key technical findings:",
        *finding_lines,
        "",
        "Indicators of compromise:",
        _fmt_iocs(iocs),
        "",
        f"{mentions} — open a bounded adversarial investigation. Trace fund/abuse "
        "paths, attribute the family, challenge weak claims, assess customer "
        "liability, and converge on an action packet for the human officer. "
        "Cite evidence from this bundle; do not invent facts.",
    ]
    return _defang("\n".join(lines))


async def open_live_case(submission_id: str, *, case_id: str | None = None) -> str:
    """Create a real Band room for a submission and post the intake message.
    Returns the Band room id."""
    from band.client.rest import (
        ChatMessageRequest,
        ChatMessageRequestMentionsItem,
        ChatRoomRequest,
        ParticipantRequest,
        RestClient,
    )

    # Real evidence from the PARALLAX DB + an immutable MinIO snapshot.
    bundle = await collect_submission_evidence(submission_id)
    ref = await snapshot_evidence_bundle(submission_id)
    bundle["_bundle_sha256"] = ref.sha256

    intake = agent_by_role("intake")
    if not (intake.configured_id and intake.configured_api_key):
        raise ValueError("Intake agent Band credentials are not configured.")

    client = RestClient(api_key=intake.configured_api_key, base_url=settings.BAND_REST_URL)
    case_id = case_id or f"PARALLAX-{bundle['submission']['sha256'][:10]}"

    room = client.agent_api_chats.create_agent_chat(chat=ChatRoomRequest(task_id=None))
    data = getattr(room, "data", None)
    room_id = getattr(data, "id", None)
    if room_id is None:  # defensive: dig the id out of the serialized response
        d = room.model_dump() if hasattr(room, "model_dump") else dict(room)
        room_id = (d.get("data") or {}).get("id") or d.get("id")
    logger.info("Created Band room %s (case %s)", room_id, case_id)

    # Add the seven specialist agents as participants.
    for agent in AGENT_ROSTER:
        if agent.role == "intake" or not agent.configured_id:
            continue
        try:
            client.agent_api_participants.add_agent_chat_participant(
                room_id,
                participant=ParticipantRequest(participant_id=agent.configured_id, role="member"),
            )
            logger.info("Added participant %s", agent.role)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not add %s: %s", agent.role, exc)

    mentions = [
        ChatMessageRequestMentionsItem(id=a.configured_id, handle=a.handle, name=a.display_name)
        for a in AGENT_ROSTER
        if a.role != "intake" and a.configured_id
    ]
    client.agent_api_messages.create_agent_chat_message(
        room_id,
        message=ChatMessageRequest(content=build_intake_message(bundle), mentions=mentions),
    )
    logger.info("Posted intake message to room %s", room_id)
    return str(room_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Open a live Band case from a PARALLAX submission.")
    parser.add_argument("submission_id")
    parser.add_argument("--case-id", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    room_id = asyncio.run(open_live_case(args.submission_id, case_id=args.case_id))
    print(f"Live Band room opened: {room_id}")


if __name__ == "__main__":
    main()
