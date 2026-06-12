"""Unit tests for the AI Reasoning Cortex deterministic logic."""

import os
import tempfile

from parallax.ai import orchestration
from parallax.ai.debate import run_debate
from parallax.ai.re_workbench.code_selector import score_text, select_relevant_code
from parallax.ai.risk import compute_risk
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    BehaviorPhase,
    CodeInterpreterOutput,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)


def _clean_code():
    return CodeInterpreterOutput(intent_classification="clean", risk_level="LOW", confidence=0.6)


def _malicious_behavior():
    return BehaviorAnalystOutput(
        risk_level="CRITICAL",
        confidence=0.85,
        network_iocs=["http://185.220.101.47/c2", "evil.example.com"],
        kill_chain=[BehaviorPhase(phase="exfiltration", actions=["POST creds"], risk="CRITICAL")],
    )


def test_debate_detects_evasion():
    d = run_debate(_clean_code(), _malicious_behavior(), IntelCorrelatorOutput(), VisualIntelOutput())
    assert d.evasion_suspected is True
    assert d.confidence_modifier >= 0.15
    assert len(d.contradictions) == 1
    assert "code_interpreter" in d.contradictions[0].between


def test_debate_detects_dormant_payload():
    code = CodeInterpreterOutput(intent_classification="banking_trojan", risk_level="HIGH")
    behavior = BehaviorAnalystOutput(risk_level="LOW", observed_behaviors=[])
    d = run_debate(code, behavior, IntelCorrelatorOutput(), VisualIntelOutput())
    assert d.evasion_suspected is False
    assert any("dormant" in c.description.lower() for c in d.contradictions)


def test_risk_score_monotonic_and_bounded():
    d = run_debate(_clean_code(), _malicious_behavior(), IntelCorrelatorOutput(), VisualIntelOutput())
    r = compute_risk(
        permissions=[
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
            "android.permission.RECEIVE_SMS",
            "android.permission.SYSTEM_ALERT_WINDOW",
        ],
        code=_clean_code(),
        behavior=_malicious_behavior(),
        intel=IntelCorrelatorOutput(),
        visual=VisualIntelOutput(),
        debate=d,
    )
    assert 0 <= r.evidence_score <= 100
    assert r.components.network_exfiltration >= 0.8
    assert abs(sum(r.weights.values()) - 1.0) < 1e-6
    assert r.verdict in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAN")


def test_risk_clean_app_is_low():
    r = compute_risk(
        permissions=["android.permission.WAKE_LOCK", "android.permission.INTERNET"],
        code=_clean_code(),
        behavior=BehaviorAnalystOutput(risk_level="LOW"),
        intel=IntelCorrelatorOutput(),
        visual=VisualIntelOutput(),
        debate=run_debate(_clean_code(), BehaviorAnalystOutput(risk_level="LOW"), IntelCorrelatorOutput(), VisualIntelOutput()),
    )
    assert r.verdict in ("LOW", "CLEAN")


def test_ioc_extraction():
    iocs = orchestration._extract_iocs(
        [{"args": {"url": "http://185.220.101.47/gate.php"}, "event_type": "HttpURLConnection.connect"}],
        _malicious_behavior(),
        _clean_code(),
    )
    assert "185.220.101.47" in iocs["ips"]
    assert "evil.example.com" in iocs["domains"]
    assert any("gate.php" in u for u in iocs["urls"])


def test_code_selector_scores_sensitive_apis():
    score, matched = score_text("class X extends AccessibilityService { SmsManager m; }")
    assert score > 0
    assert "AccessibilityService" in matched
    assert "SmsManager" in matched


def test_code_selector_picks_relevant_files():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "sources")
        os.makedirs(src)
        with open(os.path.join(src, "Evil.java"), "w") as f:
            f.write("class Evil extends AccessibilityService { void x(){ new SmsManager(); } }")
        with open(os.path.join(src, "Boring.java"), "w") as f:
            f.write("class Boring { int add(int a, int b){ return a+b; } }")
        code, selected, urls = select_relevant_code(d)
        assert "Evil.java" in " ".join(selected)
        assert "Boring.java" not in " ".join(selected)
