"""Unit tests for the delivery layer (fraud chain, STIX, YARA, rules, report)."""

import json

from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    CortexResult,
    IntelCorrelatorOutput,
    RiskScore,
    VisualIntelOutput,
)
from parallax.delivery.fraud_chain import build_fraud_chain
from parallax.delivery.fraud_rules import generate_fraud_rules
from parallax.delivery.report_generator import render_html, render_pdf
from parallax.delivery.stix_exporter import build_stix_json
from parallax.delivery.yara_generator import generate_yara_rule
from parallax.knowledge.pattern_memory import extract_patterns

_SHA = "abcdef12" * 8
_PERMS = [
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.RECEIVE_SMS",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.READ_PHONE_STATE",
]


def _cortex() -> CortexResult:
    return CortexResult(
        sha256=_SHA,
        verdict="CRITICAL",
        risk=RiskScore(evidence_score=88.0, calibrated_score=88.0, verdict="CRITICAL"),
        executive_summary="Banking trojan impersonating SBI.",
        technical_findings=["overlay captures credentials", "SMS OTP intercepted"],
        attck_techniques=["T1417.002", "T1582"],
        iocs={
            "domains": ["evil-c2.com"],
            "ips": ["185.220.101.47"],
            "urls": ["http://evil-c2.com/g"],
        },
        code_interpreter=CodeInterpreterOutput(
            intent_classification="banking_trojan",
            risk_level="CRITICAL",
            evidence=["AccessibilityService overlay", "SmsManager intercept"],
            attack_flow=["accessibility", "overlay", "capture creds", "exfiltrate"],
        ),
        behavior_analyst=BehaviorAnalystOutput(
            risk_level="CRITICAL", observed_behaviors=["sms intercepted", "http post c2"]
        ),
        visual=VisualIntelOutput(
            phishing_detected=True, brand_impersonation="SBI YONO", brand_impersonation_score=0.95
        ),
        intel_correlator=IntelCorrelatorOutput(
            family_attribution="SharkBot", family_confidence=0.8
        ),
    )


def test_fraud_chain_stages_ordered_and_evidenced():
    fc = build_fraud_chain(_cortex(), _PERMS)
    stages = [s["stage"] for s in fc]
    assert "brand_impersonation" in stages
    assert "otp_interception" in stages
    assert "exfiltration" in stages
    # Ordering is monotonic by defined stage order.
    orders = [s["order"] for s in fc]
    assert orders == sorted(orders)


def test_stix_bundle_valid():
    bundle = build_stix_json(_SHA, "com.fake.sbi", _cortex())
    data = json.loads(bundle)
    assert data["type"] == "bundle"
    types = {o["type"] for o in data["objects"]}
    assert "malware" in types
    assert "indicator" in types or "attack-pattern" in types


def test_yara_rule_compiles_and_has_distinctive_strings():
    rule = generate_yara_rule(_SHA, "com.fake.sbi", _cortex(), "2026-06-12")
    assert rule is not None
    assert "PARALLAX_AUTO_" in rule
    assert "evil-c2.com" in rule


def test_fraud_rules_generated():
    rules = generate_fraud_rules(_SHA, "com.fake.sbi", _cortex())
    assert len(rules["dsl"]) >= 1
    assert len(rules["suricata"]) >= 1
    # C2 block rule must be present.
    assert any(
        "evil-c2.com" in r.get("id", "") or "evil-c2.com" in json.dumps(r) for r in rules["dsl"]
    )


def test_report_renders_html_and_pdf():
    fc = build_fraud_chain(_cortex(), _PERMS)
    html = render_html(_SHA, "com.fake.sbi", _cortex(), fc)
    assert "PARALLAX Investigation Report" in html
    assert "CRITICAL" in html
    pdf = render_pdf(_SHA, "com.fake.sbi", _cortex(), fc)
    assert pdf[:4] == b"%PDF"


def test_pattern_extraction_covers_categories():
    patterns = extract_patterns(_cortex(), _PERMS, apkid={"matches": {"DexGuard": []}})
    cats = {p["category"] for p in patterns}
    assert "fraud_flow" in cats
    assert "c2_pattern" in cats
    assert "ui_phishing_template" in cats
    assert "permission_api_chain" in cats
