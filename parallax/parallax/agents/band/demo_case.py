"""Synthetic Band demo case runner. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from parallax.agents.band.agents import (
    add_challenge,
    build_action_packet,
    resolve_challenge,
    run_room_round,
)
from parallax.agents.band.band_adapter import BandAdapter, BandConfig
from parallax.agents.band.case_room import open_case_room
from parallax.agents.band.room_protocol import EvidenceBundleRef
from parallax.agents.band.transcript_export import export_markdown

logger = logging.getLogger(__name__)


def synthetic_fraud_case() -> dict:
    """Return deterministic synthetic data for the Band demo transcript."""
    return {
        "case_id": "CASE-FR-2026-00421",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "customer_report": (
            "INR 3.4L lost after installing 'SBI YONO KYC Update' APK from a WhatsApp link."
        ),
        "transactions": [
            {"amount_inr": 52000, "beneficiary": "upi-mule-001", "minute": 0},
            {"amount_inr": 48000, "beneficiary": "upi-mule-002", "minute": 2},
            {"amount_inr": 75000, "beneficiary": "upi-mule-003", "minute": 4},
            {"amount_inr": 65000, "beneficiary": "upi-mule-001", "minute": 7},
            {"amount_inr": 100000, "beneficiary": "upi-mule-002", "minute": 11},
        ],
        "policy_context": {
            "reported_after_minutes": 41,
            "credential_shared": False,
            "synthetic": True,
        },
    }


async def _synthetic_bundle(submission_id: str) -> EvidenceBundleRef:
    """Return a deterministic bundle pointer for offline Band demos."""
    payload = json.dumps(
        {"submission_id": submission_id, **synthetic_fraud_case()},
        sort_keys=True,
    ).encode("utf-8")
    import hashlib

    sha256 = hashlib.sha256(payload).hexdigest()
    return EvidenceBundleRef(
        url=f"https://example.test/parallax/demo/{submission_id}/bundle.json",
        bucket="parallax-case-bundles",
        object_name=f"demo/{submission_id}/bundle.json",
        sha256=sha256,
        byte_size=len(payload),
        content_type="application/json",
    )


async def run_demo(
    submission_id: str,
    *,
    output_dir: str = "demo-output",
    case_id: str = "CASE-FR-2026-00421",
    adapter: BandAdapter | None = None,
) -> Path:
    """Drive the deterministic eight-agent room loop and export transcript artifacts."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    adapter = adapter or BandAdapter(BandConfig(mode="mock"))

    room = await open_case_room(
        submission_id,
        case_id=case_id,
        adapter=adapter,
        snapshot_fn=_synthetic_bundle,
    )
    (out / "room.opened.json").write_text(room.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Room opened: %s", room.case_id)

    round_one = run_room_round(room, adapter=adapter)
    device_claim = next(
        claim
        for message in round_one
        if "device-compromi" in message.sender_id
        for claim in message.attached_claims
    )
    challenge_message = add_challenge(
        room,
        target_claim_id=device_claim.claim_id,
        reason=(
            "Confidence 0.91 overclaims unless dynamic SMS evidence is tied to the "
            "same bundle hash and install timeline."
        ),
        severity="major",
        adapter=adapter,
    )

    run_room_round(room, adapter=adapter)
    challenge = challenge_message.attached_challenges[0]
    resolve_challenge(
        room,
        challenge.challenge_id,
        accepted=True,
        resolution_text=(
            "Accepted. Device-compromise confidence is interpreted as joint evidence "
            "from static permissions plus dynamic SMS timeline, not permissions alone."
        ),
        adapter=adapter,
    )
    run_room_round(room, adapter=adapter)
    build_action_packet(room)

    (out / "transcript.json").write_text(room.model_dump_json(indent=2), encoding="utf-8")
    (out / "transcript.md").write_text(export_markdown(room), encoding="utf-8")
    if room.final_action_packet:
        (out / "action_packet.json").write_text(
            room.final_action_packet.model_dump_json(indent=2),
            encoding="utf-8",
        )
    logger.info("Demo complete. Transcript exported to %s", out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic PARALLAX x Band demo.")
    parser.add_argument("submission_id", nargs="?", default="demo-submission-001")
    parser.add_argument("--output-dir", default="demo-output")
    parser.add_argument("--case-id", default="CASE-FR-2026-00421")
    args = parser.parse_args()
    asyncio.run(run_demo(args.submission_id, output_dir=args.output_dir, case_id=args.case_id))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
