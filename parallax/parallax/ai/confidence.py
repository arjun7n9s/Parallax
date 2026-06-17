"""Overall-confidence scoring for a cortex result.

Per-agent ``confidence`` answers "how sure is this analyst?"; this module
answers the question a bank fraud manager actually cares about: "how much should
a human trust the whole verdict?" It is deterministic and auditable, like
``risk.py`` — ``drivers`` records every factor that moved the score, and
``needs_human_review`` gates the report banner.

Inputs that raise confidence: broad evidence coverage (multiple analysts produced
signal), runtime observation captured, a confirmed external family attribution,
and high self-confidence from the agents that ran. Inputs that lower it:
static-only analysis (no dynamic evidence), unresolved cross-agent
contradictions, and missing analyst signal.
"""

from __future__ import annotations

from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    DebateResult,
    IntelCorrelatorOutput,
    OverallConfidence,
    RiskScore,
    VisualIntelOutput,
)

_HIGH_BAND = 0.75
_MODERATE_BAND = 0.50


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_overall_confidence(
    *,
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    debate: DebateResult | None,
    risk: RiskScore,
    dynamic_observed: bool,
    known_family: dict | None = None,
) -> OverallConfidence:
    drivers: list[str] = []

    # 1. Coverage: how many independent analysts produced a usable signal.
    produced = {
        "code_interpreter": bool(code and code.intent_classification != "uncertain"),
        "behavior_analyst": bool(behavior and (behavior.kill_chain or behavior.observed_behaviors)),
        "intel_correlator": bool(intel and (intel.family_attribution or intel.attck_techniques)),
        "visual": bool(visual and visual.findings),
    }
    n_signal = sum(produced.values())
    coverage = n_signal / len(produced)
    drivers.append(f"{n_signal}/{len(produced)} analysts produced signal")

    # 2. Mean self-confidence of the analysts that actually produced signal.
    self_confidences = [
        c
        for name, c in (
            ("code_interpreter", code.confidence if code else 0.0),
            ("behavior_analyst", behavior.confidence if behavior else 0.0),
            ("intel_correlator", intel.confidence if intel else 0.0),
            ("visual", visual.confidence if visual else 0.0),
        )
        if produced.get(name) and c > 0.0
    ]
    agent_conf = _mean(self_confidences) if self_confidences else coverage

    # Base blends coverage with the agents' own stated confidence.
    score = 0.5 * coverage + 0.5 * agent_conf

    # 3. Runtime evidence: the single biggest trust factor. Static-only mirrors
    # the widened risk confidence_interval.
    if dynamic_observed:
        score += 0.10
        drivers.append("runtime evidence captured")
    else:
        score -= 0.20
        drivers.append("static-only: no runtime evidence (confidence reduced)")

    # 4. Confirmed external family attribution is ground truth.
    if known_family and known_family.get("family") and known_family.get("confidence", 0.0) >= 0.8:
        score += 0.15
        drivers.append(f"known-family attribution: {known_family['family']}")

    # 5. Unresolved contradictions reduce trust in any single reading.
    evasion = bool(debate and debate.evasion_suspected)
    unresolved = [c for c in (debate.contradictions if debate else []) if not c.resolution]
    if unresolved:
        score -= 0.10
        drivers.append(f"{len(unresolved)} unresolved contradiction(s)")

    score = max(0.0, min(1.0, score))

    if score >= _HIGH_BAND:
        band: str = "high"
    elif score >= _MODERATE_BAND:
        band = "moderate"
    else:
        band = "low"

    # Human review when trust is low, when a high-stakes verdict rests on less
    # than high confidence, or whenever evasion is suspected (always worth a look).
    needs_review = (
        band == "low" or (risk.verdict in ("HIGH", "CRITICAL") and band != "high") or evasion
    )
    if evasion:
        drivers.append("evasion suspected — flagged for human review")

    return OverallConfidence(
        score=round(score, 3),
        band=band,  # type: ignore[arg-type]
        needs_human_review=needs_review,
        drivers=drivers,
    )
