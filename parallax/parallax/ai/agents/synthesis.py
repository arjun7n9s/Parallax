"""Synthesis agent — final evidence-first report, IRT and recommendations."""

from __future__ import annotations

import json
import logging

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import SYNTHESIS_SYSTEM
from parallax.ai.schemas import (
    ATTCKEvidenceRow,
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    DebateResult,
    EvidenceTableRow,
    IntelCorrelatorOutput,
    IOCContextRow,
    IRTEntry,
    RiskBreakdownRow,
    RiskScore,
    SynthesisOutput,
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
) -> SynthesisOutput:
    """Return structured synthesis output.

    The numeric verdict/score are fixed by the deterministic risk module; the
    synthesis agent organizes the evidence into report/UI sections.
    """
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
            "Write the evidence-first report, evidence table, risk breakdown, "
            "ATT&CK mapping, IOC context, IRT and recommendations.",
        ]
    )

    try:
        raw = await llm.complete_json("synthesis", prompt, SYNTHESIS_SYSTEM)
    except Exception as exc:
        logger.warning("Synthesis LLM failed, using deterministic fallback: %s", exc)
        raw = {}

    if not raw:
        # Deterministic fallback so a synthesis-LLM outage never drops the report.
        return _fallback(code, behavior, intel, visual, risk)

    # Backward-compatible alias: older prompts/tests may still return
    # technical_findings. The structured contract calls them key_findings.
    if "key_findings" not in raw and "technical_findings" in raw:
        raw["key_findings"] = raw.get("technical_findings", [])

    out = SynthesisOutput.model_validate(raw)
    if not out.risk_breakdown:
        out.risk_breakdown = _risk_breakdown(risk)
    return out


def _fallback(
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    risk: RiskScore,
) -> SynthesisOutput:
    findings: list[str] = []
    irt: list[IRTEntry] = []
    evidence: list[EvidenceTableRow] = []
    attck: list[ATTCKEvidenceRow] = []
    iocs: list[IOCContextRow] = []
    if code and code.intent_classification not in ("clean", "uncertain"):
        findings.append(f"Code intent: {code.intent_classification} ({code.risk_level}).")
        evidence.extend(
            EvidenceTableRow(technique="", evidence=e, confidence=code.confidence)
            for e in code.evidence[:5]
        )
        attck.extend(
            ATTCKEvidenceRow(technique="", t_code=t, evidence="Mapped from static code evidence")
            for t in code.attck_techniques
        )
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
        evidence.extend(
            EvidenceTableRow(technique=p.phase, evidence=", ".join(p.actions), confidence=0.7)
            for p in behavior.kill_chain
        )
        for value in behavior.network_iocs:
            iocs.append(IOCContextRow(type="other", value=value, context="Runtime network IOC"))
    if visual and visual.phishing_detected:
        findings.append(
            f"Visual phishing of {visual.brand_impersonation} "
            f"(similarity {visual.brand_impersonation_score:.2f})."
        )
        evidence.append(
            EvidenceTableRow(
                technique="brand_impersonation",
                evidence=f"Visual phishing of {visual.brand_impersonation}",
                confidence=visual.confidence or visual.brand_impersonation_score,
            )
        )
    summary = (
        f"Automated verdict {risk.verdict} (score {risk.calibrated_score}/100). "
        "Generated without the synthesis LLM (fallback path)."
    )
    return SynthesisOutput(
        executive_summary=summary,
        key_findings=findings,
        evidence_table=evidence,
        risk_breakdown=_risk_breakdown(risk),
        attck=attck,
        iocs=iocs,
        irt=irt,
        recommendations=[],
    )


def _risk_breakdown(risk: RiskScore) -> list[RiskBreakdownRow]:
    rows: list[RiskBreakdownRow] = []
    for component, score in risk.components.model_dump().items():
        weight = risk.weights.get(component, 0.0)
        rows.append(
            RiskBreakdownRow(
                component=component,
                score=float(score),
                weight=weight,
                contribution=round(float(score) * weight * 100.0, 2),
            )
        )
    return rows
