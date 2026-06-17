"""Tests for high-risk LLM debate traces."""

import pytest

from parallax.ai import debate
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    BehaviorPhase,
    CodeInterpreterOutput,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)


def _clean_code() -> CodeInterpreterOutput:
    return CodeInterpreterOutput(intent_classification="clean", risk_level="LOW", confidence=0.6)


def _malicious_behavior() -> BehaviorAnalystOutput:
    return BehaviorAnalystOutput(
        risk_level="CRITICAL",
        confidence=0.9,
        overall_narrative="Credentials were posted to a command-and-control endpoint.",
        kill_chain=[BehaviorPhase(phase="exfiltration", actions=["POST credentials"])],
    )


@pytest.mark.asyncio
async def test_high_risk_claim_triggers_llm_debate(monkeypatch):
    async def fake_complete_json(role, prompt, system):
        assert role == "debate"
        assert "HIGH-RISK CLAIMS" in prompt
        return {
            "traces": [
                {
                    "claim": "Runtime behavior is CRITICAL",
                    "for_case": "Observed credential exfiltration.",
                    "against_case": "Could be test telemetry, but no benign context is present.",
                    "judge_verdict": "MALICIOUS",
                    "judge_reasoning": "Dynamic exfiltration outweighs clean static surface.",
                    "confidence": 0.86,
                }
            ]
        }

    monkeypatch.setattr(debate.llm, "complete_json", fake_complete_json)

    result = await debate.run_debate_with_llm(
        _clean_code(), _malicious_behavior(), IntelCorrelatorOutput(), VisualIntelOutput()
    )

    assert result.evasion_suspected is True
    assert result.llm_trace
    assert result.llm_trace[0].judge_verdict == "MALICIOUS"
    assert "LLM debate completed" in result.notes


@pytest.mark.asyncio
async def test_low_risk_claim_skips_llm(monkeypatch):
    async def should_not_call(role, prompt, system):
        raise AssertionError("LLM should not be called for low-risk debate")

    monkeypatch.setattr(debate.llm, "complete_json", should_not_call)

    result = await debate.run_debate_with_llm(
        CodeInterpreterOutput(intent_classification="clean", risk_level="LOW"),
        BehaviorAnalystOutput(risk_level="LOW"),
        IntelCorrelatorOutput(),
        VisualIntelOutput(),
    )

    assert result.llm_trace == []
    assert result.evasion_suspected is False


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_deterministic(monkeypatch):
    async def failing_complete_json(role, prompt, system):
        raise RuntimeError("debate backend down")

    monkeypatch.setattr(debate.llm, "complete_json", failing_complete_json)

    result = await debate.run_debate_with_llm(
        _clean_code(), _malicious_behavior(), IntelCorrelatorOutput(), VisualIntelOutput()
    )

    assert result.evasion_suspected is True
    assert result.confidence_modifier >= 0.15
    assert result.llm_trace == []
