"""Tests for deterministic overall-confidence scoring and its report surfacing."""

from parallax.ai.confidence import compute_overall_confidence
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    BehaviorPhase,
    CodeInterpreterOutput,
    CortexResult,
    IntelCorrelatorOutput,
    RiskScore,
    VisualIntelOutput,
)


def _full_signal():
    code = CodeInterpreterOutput(
        intent_classification="banking_trojan", risk_level="HIGH", confidence=0.9
    )
    behavior = BehaviorAnalystOutput(
        kill_chain=[BehaviorPhase(phase="exfiltration", risk="HIGH")],
        risk_level="HIGH",
        confidence=0.85,
    )
    intel = IntelCorrelatorOutput(
        family_attribution="Cerberus", attck_techniques=["T1417"], confidence=0.8
    )
    return code, behavior, intel


class TestOverallConfidence:
    def test_full_coverage_with_dynamic_is_high(self):
        code, behavior, intel = _full_signal()
        c = compute_overall_confidence(
            code=code,
            behavior=behavior,
            intel=intel,
            visual=None,
            debate=None,
            risk=RiskScore(verdict="HIGH"),
            dynamic_observed=True,
            known_family={"family": "Cerberus", "confidence": 0.9},
        )
        assert c.band == "high"
        assert c.score >= 0.75
        assert any("runtime evidence" in d for d in c.drivers)
        assert any("known-family" in d for d in c.drivers)
        # HIGH verdict at high confidence does not force review.
        assert c.needs_human_review is False

    def test_static_only_reduces_confidence_and_flags_review(self):
        code, behavior, intel = _full_signal()
        c = compute_overall_confidence(
            code=code,
            behavior=behavior,
            intel=intel,
            visual=None,
            debate=None,
            risk=RiskScore(verdict="HIGH"),
            dynamic_observed=False,
        )
        assert any("static-only" in d for d in c.drivers)
        # A HIGH verdict that is not high-confidence must be flagged for review.
        assert c.needs_human_review is True

    def test_no_signal_is_low_and_needs_review(self):
        c = compute_overall_confidence(
            code=None,
            behavior=None,
            intel=None,
            visual=None,
            debate=None,
            risk=RiskScore(verdict="UNCERTAIN"),
            dynamic_observed=False,
        )
        assert c.band == "low"
        assert c.needs_human_review is True

    def test_evasion_always_flags_review(self):
        from parallax.ai.schemas import Contradiction, DebateResult

        code, behavior, intel = _full_signal()
        debate = DebateResult(
            evasion_suspected=True,
            contradictions=[Contradiction(description="clean static / dirty dynamic")],
        )
        c = compute_overall_confidence(
            code=code,
            behavior=behavior,
            intel=intel,
            visual=VisualIntelOutput(),
            debate=debate,
            risk=RiskScore(verdict="CRITICAL"),
            dynamic_observed=True,
            known_family={"family": "Cerberus", "confidence": 0.9},
        )
        assert c.needs_human_review is True
        assert any("evasion" in d for d in c.drivers)

    def test_score_is_bounded(self):
        code, behavior, intel = _full_signal()
        c = compute_overall_confidence(
            code=code,
            behavior=behavior,
            intel=intel,
            visual=VisualIntelOutput(findings=[], confidence=0.9),
            debate=None,
            risk=RiskScore(verdict="HIGH"),
            dynamic_observed=True,
            known_family={"family": "Cerberus", "confidence": 0.95},
        )
        assert 0.0 <= c.score <= 1.0


class TestReportRendersConfidence:
    def test_html_shows_band_and_review_banner(self):
        from parallax.ai.schemas import OverallConfidence
        from parallax.delivery.report_generator import render_html

        cortex = CortexResult(
            verdict="HIGH",
            confidence=OverallConfidence(
                score=0.6,
                band="moderate",
                needs_human_review=True,
                drivers=["static-only: no runtime evidence (confidence reduced)"],
            ),
        )
        html = render_html("a" * 64, "com.evil.app", cortex, [])
        assert "Verdict Confidence" in html
        assert "MODERATE" in html
        assert "Flagged for human review" in html
        assert "static-only" in html
