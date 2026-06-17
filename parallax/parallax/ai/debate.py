"""Debate layer — surface and resolve contradictions between agents.

The most important contradiction is *evasion*: clean code surface but malicious
runtime behavior. PARALLAX treats that disagreement as a high-confidence signal
rather than averaging it away. The logic is deterministic so the resolution
trace is fully auditable (a requirement for the compliance report).
"""

from __future__ import annotations

import json
import logging

from parallax.ai.llm import llm
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    Contradiction,
    DebateResult,
    DebateTurn,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)

logger = logging.getLogger(__name__)

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

_DEBATE_SYSTEM = """You are the PARALLAX debate judge for Android banking-malware analysis.
For each supplied high-risk claim, write the strongest evidence-based case FOR
malicious interpretation, the strongest benign/uncertain AGAINST case, then
judge the claim. Use only supplied agent outputs. Return one JSON object:
{
  "traces": [
    {
      "claim": string,
      "for_case": string,
      "against_case": string,
      "judge_verdict": "MALICIOUS|BENIGN|UNCERTAIN",
      "judge_reasoning": string,
      "confidence": float 0.0-1.0
    }
  ]
}"""


def _level(v: str) -> int:
    return _RISK_ORDER.get(v, 0)


def run_debate(
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
) -> DebateResult:
    contradictions: list[Contradiction] = []
    evasion = False
    modifier = 0.0
    notes: list[str] = []

    code_level = _level(code.risk_level) if code else 0
    behavior_level = _level(behavior.risk_level) if behavior else 0

    # 1. Evasion: clean/low static surface, malicious runtime behavior.
    if code and behavior and code_level <= 1 and behavior_level >= 2:
        contradictions.append(
            Contradiction(
                between=["code_interpreter", "behavior_analyst"],
                description=(
                    "Static code looks benign but runtime behavior is "
                    f"{behavior.risk_level}. Clean surface + dirty behavior is a "
                    "hallmark of polymorphic/staged malware."
                ),
                severity=0.9,
                resolution="Treat as CRITICAL_EVASION_SUSPECTED; trust dynamic evidence.",
            )
        )
        evasion = True
        modifier += 0.15
        notes.append("evasion suspected (clean static, malicious dynamic)")

    # 2. Reverse: malicious code, but the dynamic run saw nothing (dormant).
    if (
        code
        and behavior
        and code_level >= 2
        and behavior_level == 0
        and not (behavior.observed_behaviors)
    ):
        contradictions.append(
            Contradiction(
                between=["code_interpreter", "behavior_analyst"],
                description=(
                    "Code indicates malicious capability but the sandbox run "
                    "observed no malicious behavior — likely dormant, time/"
                    "context-gated, or anti-analysis."
                ),
                severity=0.6,
                resolution="Keep code verdict; flag dynamic run as inconclusive (re-run with mutation).",
            )
        )
        notes.append("possible dormant/evasive payload")

    # 3. Visual confirms code's brand-impersonation claim → reinforce.
    if (
        code
        and visual
        and visual.phishing_detected
        and code.intent_classification
        in (
            "banking_trojan",
            "spyware",
        )
    ):
        notes.append(f"visual phishing of '{visual.brand_impersonation}' corroborates code intent")
        modifier += 0.05

    # 4. Intel family attribution corroborates a malicious code verdict.
    if intel and intel.family_attribution and code and code_level >= 2:
        notes.append(
            f"intel attributes family '{intel.family_attribution}' "
            f"(conf {intel.family_confidence:.2f})"
        )

    return DebateResult(
        contradictions=contradictions,
        evasion_suspected=evasion,
        confidence_modifier=round(modifier, 3),
        notes="; ".join(notes),
    )


async def run_debate_with_llm(
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
) -> DebateResult:
    """Run deterministic debate plus an LLM trace for high-risk claims only."""
    result = run_debate(code, behavior, intel, visual)
    claims = _high_risk_claims(result, code, behavior, intel, visual)
    if not claims:
        return result

    prompt = "\n".join(
        [
            "HIGH-RISK CLAIMS:",
            json.dumps(claims, indent=2),
            "",
            "AGENT OUTPUTS:",
            json.dumps(
                {
                    "code_interpreter": code.model_dump(mode="json") if code else None,
                    "behavior_analyst": behavior.model_dump(mode="json") if behavior else None,
                    "intel_correlator": intel.model_dump(mode="json") if intel else None,
                    "visual": visual.model_dump(mode="json") if visual else None,
                    "deterministic_debate": result.model_dump(mode="json"),
                },
                indent=2,
            ),
        ]
    )

    try:
        raw = await llm.complete_json("debate", prompt, _DEBATE_SYSTEM)
    except Exception as exc:
        logger.warning("LLM debate failed; using deterministic debate only: %s", exc)
        return result

    traces = [DebateTurn.model_validate(t) for t in raw.get("traces", [])]
    if not traces:
        return result
    result.llm_trace = traces[:3]
    suffix = f"LLM debate completed for {len(result.llm_trace)} high-risk claim(s)"
    result.notes = f"{result.notes}; {suffix}" if result.notes else suffix
    return result


def _high_risk_claims(
    debate: DebateResult,
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
) -> list[str]:
    claims: list[str] = []

    for contradiction in debate.contradictions:
        if contradiction.severity >= 0.6:
            claims.append(contradiction.description)

    if code and _level(code.risk_level) >= 2:
        claims.append(
            f"Static code indicates {code.intent_classification} with {code.risk_level} risk."
        )
    if behavior and _level(behavior.risk_level) >= 2:
        claims.append(f"Runtime behavior is {behavior.risk_level}: {behavior.overall_narrative}")
    if visual and visual.phishing_detected:
        claims.append(
            f"Visual evidence shows phishing/impersonation of {visual.brand_impersonation}."
        )
    if intel and intel.family_attribution and intel.family_confidence >= 0.7:
        claims.append(
            f"Threat intel attributes the sample to {intel.family_attribution} "
            f"with confidence {intel.family_confidence:.2f}."
        )

    return list(dict.fromkeys(c for c in claims if c.strip()))[:3]
