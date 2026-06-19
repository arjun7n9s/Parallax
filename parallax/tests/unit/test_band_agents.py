"""Tests for deterministic PARALLAX x Band agents."""

from __future__ import annotations

import pytest

from parallax.agents.band import agents as band_agents
from parallax.agents.band.agents import (
    AGENTS,
    add_challenge,
    build_action_packet,
    resolve_challenge,
    run_room_round,
    run_room_round_live,
)
from parallax.agents.band.band_adapter import BandAdapter, BandConfig
from parallax.agents.band.room_protocol import CaseRoom, EvidenceBundleRef


def _room() -> CaseRoom:
    return CaseRoom(
        case_id="CASE-FR-2026-00421",
        submission_id="sub-1",
        band_room_id="room-1",
        evidence_bundle=EvidenceBundleRef(
            url="https://example.test/bundle.json",
            bucket="parallax-case-bundles",
            object_name="submissions/sub-1/bundle.json",
            sha256="c" * 64,
            byte_size=512,
        ),
    )


def test_room_round_posts_one_message_per_agent():
    adapter = BandAdapter(BandConfig(mode="mock"))
    room = _room()

    messages = run_room_round(room, adapter=adapter)

    assert len(messages) == len(AGENTS) == 8
    assert len(room.messages) == 8
    assert len(adapter.get_messages(room.band_room_id)) == 8
    assert all(message.attached_claims for message in messages)


def test_challenge_resolution_unblocks_final_action_packet():
    adapter = BandAdapter(BandConfig(mode="mock"))
    room = _room()
    first_round = run_room_round(room, adapter=adapter)
    target_claim = first_round[1].attached_claims[0]

    challenge_message = add_challenge(
        room,
        target_claim_id=target_claim.claim_id,
        reason="Static permission claim needs dynamic corroboration.",
        adapter=adapter,
    )
    provisional = build_action_packet(room)

    assert provisional.status == "provisional"
    assert provisional.unresolved_challenge_ids == [
        challenge_message.attached_challenges[0].challenge_id
    ]

    resolve_challenge(
        room,
        challenge_message.attached_challenges[0].challenge_id,
        accepted=True,
        resolution_text="Dynamic SMS timeline corroborates the static claim.",
        adapter=adapter,
    )
    final = build_action_packet(room)

    assert final.status == "final"
    assert final.unresolved_challenge_ids == []
    assert room.status == "converged"


@pytest.mark.parametrize("agent", AGENTS)
def test_each_stub_agent_returns_cited_claims(agent):
    room = _room()

    claims = agent.respond(room)

    assert claims
    assert all(claim.agent_id == agent.descriptor.participant_ref for claim in claims)
    assert all(claim.evidence_refs for claim in claims)


@pytest.mark.asyncio
async def test_live_round_uses_llm_for_three_credibility_sensitive_agents(monkeypatch):
    calls: list[str] = []

    async def fake_llm_claim(
        prompt: str, system: str, *, role: str, fallback: str, temperature=0.2
    ):
        calls.append(role)
        return f"LLM {role} claim grounded in transcript"

    monkeypatch.setattr(band_agents, "llm_claim", fake_llm_claim)
    adapter = BandAdapter(BandConfig(mode="mock"))
    room = _room()

    messages = await run_room_round_live(room, adapter=adapter)

    assert len(messages) == 8
    assert calls == ["behavior_analyst", "evidence_validator", "synthesis"]
    live_messages = [
        message
        for message in messages
        if message.sender_id
        in {
            band_agents.agent_by_role("device_compromise").participant_ref,
            band_agents.agent_by_role("evidence_validator").participant_ref,
            band_agents.agent_by_role("decision_convenor").participant_ref,
        }
    ]
    assert len(live_messages) == 3
    assert all("LLM" in message.attached_claims[0].claim_text for message in live_messages)


@pytest.mark.asyncio
async def test_llm_claim_falls_back_when_gateway_fails(monkeypatch):
    class BrokenLLM:
        async def complete_text(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    import parallax.ai.llm as llm_module

    monkeypatch.setattr(llm_module, "llm", BrokenLLM())

    text = await band_agents.llm_claim(
        "prompt",
        "system",
        role="synthesis",
        fallback="deterministic fallback",
    )

    assert text == "deterministic fallback"
