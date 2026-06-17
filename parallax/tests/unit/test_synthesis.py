"""Tests for structured synthesis output."""

import pytest

from parallax.ai.agents import synthesis as synthesis_agent
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    BehaviorPhase,
    CodeInterpreterOutput,
    RiskComponents,
    RiskScore,
    SynthesisOutput,
    VisualIntelOutput,
)


def _risk() -> RiskScore:
    return RiskScore(
        evidence_score=72.0,
        calibrated_score=72.0,
        verdict="HIGH",
        components=RiskComponents(code_intent_risk=0.8, network_exfiltration=0.5),
        weights={"code_intent_risk": 0.2, "network_exfiltration": 0.15},
    )


@pytest.mark.asyncio
async def test_synthesis_accepts_legacy_findings_and_fills_risk(monkeypatch):
    async def fake_complete_json(role, prompt, system):
        assert role == "synthesis"
        assert "evidence table" in prompt.lower()
        return {
            "executive_summary": "High-risk app with credential theft indicators.",
            "technical_findings": ["Overlay credential capture"],
            "evidence_table": [
                {
                    "technique": "overlay",
                    "evidence": "SYSTEM_ALERT_WINDOW and AccessibilityService",
                    "confidence": 0.8,
                }
            ],
        }

    monkeypatch.setattr(synthesis_agent.llm, "complete_json", fake_complete_json)

    out = await synthesis_agent.run_synthesis(
        code=CodeInterpreterOutput(),
        behavior=BehaviorAnalystOutput(),
        intel=None,
        visual=VisualIntelOutput(),
        debate=None,
        risk=_risk(),
        package_name="com.fake.bank",
    )

    assert isinstance(out, SynthesisOutput)
    assert out.key_findings == ["Overlay credential capture"]
    assert out.evidence_table[0].technique == "overlay"
    assert any(row.component == "code_intent_risk" for row in out.risk_breakdown)


@pytest.mark.asyncio
async def test_synthesis_fallback_is_structured(monkeypatch):
    async def failing_complete_json(role, prompt, system):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(synthesis_agent.llm, "complete_json", failing_complete_json)

    out = await synthesis_agent.run_synthesis(
        code=CodeInterpreterOutput(
            intent_classification="banking_trojan",
            risk_level="HIGH",
            confidence=0.9,
            evidence=["AccessibilityService overlay"],
            attck_techniques=["T1417.002"],
            reasoning="Overlay steals credentials.",
        ),
        behavior=BehaviorAnalystOutput(
            kill_chain=[
                BehaviorPhase(
                    phase="exfiltration",
                    actions=["POST credentials to C2"],
                    risk="HIGH",
                )
            ],
            overall_narrative="Credentials were exfiltrated.",
            network_iocs=["http://evil.example/c2"],
        ),
        intel=None,
        visual=VisualIntelOutput(
            phishing_detected=True,
            brand_impersonation="SBI YONO",
            brand_impersonation_score=0.9,
            confidence=0.85,
        ),
        debate=None,
        risk=_risk(),
        package_name="com.fake.bank",
    )

    assert out.executive_summary.startswith("Automated verdict HIGH")
    assert out.key_findings
    assert out.evidence_table
    assert out.attck[0].t_code == "T1417.002"
    assert out.iocs[0].value == "http://evil.example/c2"
    assert out.risk_breakdown
