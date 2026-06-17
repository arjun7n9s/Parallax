"""Tests for malware pattern memory extraction and persistence payloads."""

import pytest

from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    BehaviorPhase,
    ClassRole,
    CodeInterpreterOutput,
    CortexResult,
    MethodIntent,
    RiskScore,
    VisualIntelOutput,
)
from parallax.knowledge import pattern_memory

_PERMS = [
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.RECEIVE_SMS",
    "android.permission.SYSTEM_ALERT_WINDOW",
]


def _cortex() -> CortexResult:
    code = CodeInterpreterOutput(
        intent_classification="banking_trojan",
        risk_level="HIGH",
        confidence=0.88,
        evidence=["AccessibilityService overlay", "SmsManager OTP interception"],
        attack_flow=["accessibility enablement", "overlay credential theft", "C2 exfiltration"],
        class_roles=[
            ClassRole(
                class_name="OverlayService",
                role="credential_overlay",
                confidence=0.9,
                evidence=["SYSTEM_ALERT_WINDOW", "AccessibilityService"],
            ),
            ClassRole(
                class_name="OverlayServiceCopy",
                role="credential_overlay",
                confidence=0.9,
                evidence=["SYSTEM_ALERT_WINDOW", "AccessibilityService"],
            ),
        ],
        method_intents=[
            MethodIntent(
                method="stealOtp",
                intent="sms_otp_exfiltration",
                sources=["SmsMessage.getMessageBody", "SmsMessage.getMessageBody"],
                sinks=["HttpURLConnection.getOutputStream"],
            )
        ],
    )
    behavior = BehaviorAnalystOutput(
        confidence=0.8,
        kill_chain=[
            BehaviorPhase(
                phase="privilege_escalation",
                actions=["requested accessibility"],
                duration_ms=500,
                risk="HIGH",
            ),
            BehaviorPhase(
                phase="exfiltration",
                actions=["POST credentials", "POST OTP"],
                duration_ms=12_000,
                risk="CRITICAL",
            ),
        ],
    )
    return CortexResult(
        sha256="a" * 64,
        verdict="HIGH",
        risk=RiskScore(verdict="HIGH", calibrated_score=75),
        attck_techniques=["T1417.002"],
        iocs={"domains": ["evil.example", "evil.example"], "ips": ["185.220.101.47"]},
        kill_chain=behavior.kill_chain,
        code_interpreter=code,
        behavior_analyst=behavior,
        visual=VisualIntelOutput(
            phishing_detected=True,
            brand_impersonation="SBI YONO",
            brand_impersonation_score=0.95,
        ),
    )


def _patterns() -> list[dict]:
    return pattern_memory.extract_patterns(
        _cortex(),
        _PERMS,
        apkid={"matches": {"DexGuard": ["anti_tamper"]}},
    )


def test_pattern_ids_are_stable_across_runs():
    first = [p["pattern_id"] for p in _patterns()]
    second = [p["pattern_id"] for p in _patterns()]
    assert first == second


def test_patterns_are_deduped_within_one_sample():
    patterns = _patterns()
    ids = [p["pattern_id"] for p in patterns]
    assert len(ids) == len(set(ids))
    assert (
        sum(
            1
            for p in patterns
            if p["category"] == "c2_pattern" and p["signature"] == "evil.example"
        )
        == 1
    )


def test_code_idiom_patterns_include_roles_and_source_sink():
    code_idioms = [p for p in _patterns() if p["category"] == "code_idiom"]
    assert any(p["signature_type"] == "role" for p in code_idioms)
    assert any("sms_otp_exfiltration" in p["signature"] for p in code_idioms)
    assert any("HttpURLConnection.getOutputStream" in p["signature"] for p in code_idioms)


def test_fraud_flow_patterns_include_static_and_runtime_sequences():
    flows = [p for p in _patterns() if p["category"] == "fraud_flow"]
    assert any(p["signature_type"] == "sequence" for p in flows)
    assert any(p["signature_type"] == "runtime_sequence" for p in flows)
    assert any("POST credentials" in p["signature"] for p in flows)


def test_behavioral_timing_bucket_is_extracted():
    timing = [p for p in _patterns() if p["category"] == "behavioral_timing"]
    assert timing
    assert "10-60s" in timing[0]["signature"]


@pytest.mark.asyncio
async def test_enrich_pattern_memory_writes_unique_patterns(monkeypatch):
    captured = {}

    async def fake_run_write(cypher, **params):
        captured.update(params)
        return []

    monkeypatch.setattr(pattern_memory.neo4j_client, "run_write", fake_run_write)

    count = await pattern_memory.enrich_pattern_memory("a" * 64, _cortex(), _PERMS, None)

    ids = [p["pattern_id"] for p in captured["patterns"]]
    assert count == len(captured["patterns"])
    assert len(ids) == len(set(ids))
