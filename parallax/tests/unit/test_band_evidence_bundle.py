"""Tests for immutable Band evidence bundle creation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from parallax.agents.band.evidence_bundle import build_evidence_bundle


def test_build_evidence_bundle_uses_repo_models_shape():
    submission = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id="bank-a",
        sha256="a" * 64,
        md5="b" * 32,
        file_name="sample.apk",
        file_size=42,
        package_name="com.fake.bank",
        status="complete",
        priority="normal",
        triage_score=20.0,
        final_score=81.0,
        verdict="CRITICAL",
        s3_path="s3://parallax-apks/a.apk",
        metadata_json={
            "permissions": ["android.permission.RECEIVE_SMS"],
            "target_sdk": 31,
            "cortex_result": {
                "intel_correlator": {
                    "family_attribution": "Cerberus",
                    "family_confidence": 0.82,
                }
            },
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    hypothesis = SimpleNamespace(
        hypothesis_id="HYP-1",
        claim="Intercepts OTP",
        category="sms",
        initial_confidence=0.7,
        final_confidence=None,
        effective_confidence=0.7,
        status="PENDING",
        status_reason=None,
        recommended_next_step="Run SMS hook",
        formed_by_agent="hypothesis_engine",
        formed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        resolved_at=None,
    )
    observation = SimpleNamespace(
        id=uuid.uuid4(),
        source="frida",
        event_type="SmsManager.sendTextMessage",
        thread_id=1,
        thread_name="main",
        caller_package="com.fake.bank",
        args={"dest": "123"},
        return_value={},
        exception=None,
        captured_at_ms=123456,
        session_id="s1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    ioc = SimpleNamespace(
        id=uuid.uuid4(),
        ioc_type="domain",
        value="evil.example",
        context="c2",
        confidence=0.9,
        source_agent="intel",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    taint = SimpleNamespace(to_dict=lambda: {"source": "Sms.get", "sink": "URL.open"})

    bundle = build_evidence_bundle(
        submission=submission,
        hypotheses=[hypothesis],
        observations=[observation],
        iocs=[ioc],
        taint_flows=[taint],
        snapshot_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert bundle["submission"]["sha256"] == "a" * 64
    assert bundle["metadata"]["permissions"] == ["android.permission.RECEIVE_SMS"]
    assert bundle["hypotheses"][0]["hypothesis_id"] == "HYP-1"
    assert bundle["observations"][0]["event_type"] == "SmsManager.sendTextMessage"
    assert bundle["risk"]["family"] == "Cerberus"
