"""Tests for opening PARALLAX x Band case rooms."""

from __future__ import annotations

import pytest

from parallax.agents.band.band_adapter import BandAdapter, BandConfig
from parallax.agents.band.case_room import open_case_room
from parallax.agents.band.room_protocol import EvidenceBundleRef


@pytest.mark.asyncio
async def test_open_case_room_snapshots_and_posts_initial_message():
    adapter = BandAdapter(BandConfig(mode="mock"))

    async def fake_snapshot(_submission_id: str) -> EvidenceBundleRef:
        return EvidenceBundleRef(
            url="https://example.test/bundle.json",
            bucket="parallax-case-bundles",
            object_name="submissions/s1/bundle.json",
            sha256="b" * 64,
            byte_size=256,
        )

    room = await open_case_room(
        "sub-1",
        case_id="CASE-FR-2026-00421",
        adapter=adapter,
        snapshot_fn=fake_snapshot,
    )

    assert room.case_id == "CASE-FR-2026-00421"
    assert room.evidence_bundle.sha256 == "b" * 64
    assert room.messages[0].bundle_sha256 == "b" * 64
    assert adapter.get_messages(room.band_room_id)[0]["metadata"]["message_type"] == "request"
