"""Debate layer — surface and resolve contradictions between agents.

The most important contradiction is *evasion*: clean code surface but malicious
runtime behavior. PARALLAX treats that disagreement as a high-confidence signal
rather than averaging it away. The logic is deterministic so the resolution
trace is fully auditable (a requirement for the compliance report).
"""

from __future__ import annotations

from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    Contradiction,
    DebateResult,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


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
