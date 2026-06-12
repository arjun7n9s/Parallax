"""Synthesis agent — final evidence-first report, IRT and recommendations."""

from __future__ import annotations

import json
import logging

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import SYNTHESIS_SYSTEM
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    DebateResult,
    IntelCorrelatorOutput,
    IRTEntry,
    Recommendation,
    RiskScore,
    VisualIntelOutput,
)

logger = logging.getLogger(__name__)


def _agent_summary(
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    debate: DebateResult | None,
) -> dict:
    return {
        "code_interpreter": code.model_dump(mode="json") if code else None,
        "behavior_analyst": behavior.model_dump(mode="json") if behavior else None,
        "intel_correlator": intel.model_dump(mode="json") if intel else None,
        "visual": visual.model_dump(mode="json") if visual else None,
        "debate": debate.model_dump(mode="json") if debate else None,
    }


async def run_synthesis(
    *,
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    debate: DebateResult | None,
    risk: RiskScore,
    package_name: str,
) -> dict:
    """Return a dict with executive_summary, technical_findings, irt,
    recommendations. The numeric verdict/score are fixed by the risk module."""
    prompt = "\n".join(
        [
            f"PACKAGE: {package_name}",
            f"FINAL VERDICT (fixed): {risk.verdict}",
            f"RISK SCORE (fixed): {risk.calibrated_score}/100 "
            f"(evidence {risk.evidence_score}, +/-{risk.confidence_interval})",
            "RISK COMPONENTS:",
            json.dumps(risk.components.model_dump(mode="json"), indent=2),
            "",
            "AGENT OUTPUTS:",
            json.dumps(_agent_summary(code, behavior, intel, visual, debate), indent=2),
            "",
            "Write the evidence-first report, IRT and recommendations.",
        ]
    )

    try:
        raw = await llm.complete_json("synthesis", prompt, SYNTHESIS_SYSTEM)
    except Exception as exc:
        logger.warning("Synthesis LLM failed, using deterministic fallback: %s", exc)
        raw = {}

    irt = [IRTEntry.model_validate(e) for e in raw.get("irt", [])]
    recs = [Recommendation.model_validate(r) for r in raw.get("recommendations", [])]

    if not raw:
        # Deterministic fallback so a synthesis-LLM outage never drops the report.
        return _fallback(code, behavior, intel, visual, risk)

    return {
        "executive_summary": raw.get("executive_summary", ""),
        "technical_findings": raw.get("technical_findings", []),
        "irt": irt,
        "recommendations": recs,
    }


def _fallback(
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    risk: RiskScore,
) -> dict:
    findings: list[str] = []
    irt: list[IRTEntry] = []
    if code and code.intent_classification not in ("clean", "uncertain"):
        findings.append(f"Code intent: {code.intent_classification} ({code.risk_level}).")
        irt.append(
            IRTEntry(
                status="CONFIRMED",
                claim=f"Static code intent is {code.intent_classification}",
                explanation=code.reasoning[:400],
                evidence=code.evidence[:5],
            )
        )
    if behavior and behavior.kill_chain:
        findings.append(behavior.overall_narrative[:300])
    if visual and visual.phishing_detected:
        findings.append(
            f"Visual phishing of {visual.brand_impersonation} "
            f"(similarity {visual.brand_impersonation_score:.2f})."
        )
    summary = (
        f"Automated verdict {risk.verdict} (score {risk.calibrated_score}/100). "
        "Generated without the synthesis LLM (fallback path)."
    )
    return {
        "executive_summary": summary,
        "technical_findings": findings,
        "irt": irt,
        "recommendations": [],
    }
