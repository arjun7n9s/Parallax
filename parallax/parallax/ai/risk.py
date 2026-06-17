"""Two-layer risk scoring.

Layer A (evidence score) is a deterministic, auditable weighted sum of evidence
components derived from real agent outputs and static facts — it is fully
explainable and reproducible. Layer B (calibration) maps the evidence score to a
calibrated severity. Until labeled corpora (VirusShare/MalwareBazaar/AndroZoo)
are available, calibration is the identity with a fixed confidence band; the
plumbing is in place to swap in a trained calibrator without touching callers.
"""

from __future__ import annotations

from parallax.ai.calibration import calibrate_score
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    DebateResult,
    IntelCorrelatorOutput,
    RiskComponents,
    RiskScore,
    Verdict,
    VisualIntelOutput,
)

# Layer A weights (sum to 1.0). Exposed in the report for auditability.
WEIGHTS: dict[str, float] = {
    "permission_abuse": 0.12,
    "behavioral_indicators": 0.20,
    "code_intent_risk": 0.18,
    "network_exfiltration": 0.15,
    "code_obfuscation": 0.05,
    "brand_impersonation": 0.15,
    "campaign_association": 0.10,
    "attribution_confidence": 0.05,
}

_RISK_SCALAR = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.5, "LOW": 0.2}

# Permissions that meaningfully raise banking-fraud risk, weighted.
_DANGEROUS_PERMS = {
    "android.permission.BIND_ACCESSIBILITY_SERVICE": 1.0,
    "android.permission.SYSTEM_ALERT_WINDOW": 0.9,
    "android.permission.RECEIVE_SMS": 0.8,
    "android.permission.READ_SMS": 0.8,
    "android.permission.SEND_SMS": 0.7,
    "android.permission.BIND_DEVICE_ADMIN": 0.8,
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": 0.7,
    "android.permission.READ_CONTACTS": 0.4,
    "android.permission.REQUEST_INSTALL_PACKAGES": 0.6,
    "android.permission.CALL_PHONE": 0.3,
    "android.permission.READ_PHONE_STATE": 0.3,
    "android.permission.RECORD_AUDIO": 0.4,
    "android.permission.ACCESS_FINE_LOCATION": 0.3,
}


def _permission_abuse(permissions: list[str]) -> float:
    if not permissions:
        return 0.0
    score = sum(_DANGEROUS_PERMS.get(p, 0.0) for p in permissions)
    # Normalize against a "fully loaded" trojan (~4 high-risk perms).
    return min(1.0, score / 3.5)


def _network_exfil(
    behavior: BehaviorAnalystOutput | None, taint_flows: list[dict] | None = None
) -> float:
    val = 0.0
    if behavior:
        if behavior.network_iocs:
            val = 0.5 + min(0.4, 0.1 * len(behavior.network_iocs))
        if any(p.phase == "exfiltration" for p in behavior.kill_chain):
            val = max(val, 0.85)
        if any(p.phase == "command_control" for p in behavior.kill_chain):
            val = max(val, 0.7)
    # Static taint evidence: a proven sensitive-source -> sink path means the
    # app CAN exfiltrate even if the short dynamic run never triggered it
    # (logic bombs, time-delayed payloads).
    if taint_flows:
        risks = {t.get("risk") for t in taint_flows}
        if "CRITICAL" in risks:
            val = max(val, 0.75)
        else:
            val = max(val, 0.4)
    return min(1.0, val)


def _obfuscation(apkid: dict | None, yara_matches: list[dict] | None) -> float:
    val = 0.0
    if apkid:
        matches = apkid.get("matches") or apkid.get("files") or {}
        text = str(matches).lower()
        if any(k in text for k in ("packer", "protector", "obfuscat", "dexguard")):
            val = 0.8
        elif matches:
            val = 0.3
    if yara_matches:
        val = max(val, 0.5)
    return val


def compute_risk(
    *,
    permissions: list[str],
    code: CodeInterpreterOutput | None,
    behavior: BehaviorAnalystOutput | None,
    intel: IntelCorrelatorOutput | None,
    visual: VisualIntelOutput | None,
    debate: DebateResult | None,
    apkid: dict | None = None,
    yara_matches: list[dict] | None = None,
    taint_flows: list[dict] | None = None,
    known_family: dict | None = None,
    dynamic_observed: bool = True,
) -> RiskScore:
    comp = RiskComponents(
        permission_abuse=_permission_abuse(permissions),
        behavioral_indicators=_RISK_SCALAR.get(behavior.risk_level, 0.0) if behavior else 0.0,
        code_intent_risk=_RISK_SCALAR.get(code.risk_level, 0.0) if code else 0.0,
        network_exfiltration=_network_exfil(behavior, taint_flows),
        code_obfuscation=_obfuscation(apkid, yara_matches),
        brand_impersonation=visual.brand_impersonation_score if visual else 0.0,
        campaign_association=(
            max((c.similarity for c in intel.campaign_links), default=0.0) if intel else 0.0
        ),
        attribution_confidence=intel.family_confidence if intel else 0.0,
    )

    evidence = (
        comp.permission_abuse * WEIGHTS["permission_abuse"]
        + comp.behavioral_indicators * WEIGHTS["behavioral_indicators"]
        + comp.code_intent_risk * WEIGHTS["code_intent_risk"]
        + comp.network_exfiltration * WEIGHTS["network_exfiltration"]
        + comp.code_obfuscation * WEIGHTS["code_obfuscation"]
        + comp.brand_impersonation * WEIGHTS["brand_impersonation"]
        + comp.campaign_association * WEIGHTS["campaign_association"]
        + comp.attribution_confidence * WEIGHTS["attribution_confidence"]
    ) * 100.0

    notes: list[str] = []

    # Debate layer: contradictions (clean static, dirty dynamic) signal evasion.
    if debate and debate.evasion_suspected:
        evidence = min(100.0, evidence + 10.0)
        notes.append("Evasion contradiction (clean static / dirty dynamic): +10")

    # External threat-intel ground truth. A confirmed known-malware family from a
    # reputable feed (e.g. a MalwareBazaar signature) is dispositive that the
    # sample is malicious. It sets a verdict floor that the absence of a live
    # dynamic run cannot pull below — otherwise a known trojan analysed
    # statically would score LOW purely because 60% of the weight is dynamic.
    if known_family and known_family.get("family") and known_family.get("confidence", 0.0) >= 0.8:
        floor = 65.0  # solidly HIGH; dynamic confirmation can push it higher
        if evidence < floor:
            srcs = ", ".join(s.get("source", "?") for s in known_family.get("sources", []))
            notes.append(
                f"Known-malware family '{known_family['family']}' confirmed by "
                f"{srcs or 'threat intel'} (conf {known_family['confidence']}): "
                f"evidence floored {round(evidence, 1)} -> {floor}"
            )
            evidence = floor

    # Graceful degradation: when no runtime evidence was captured (dynamic stage
    # skipped, emulator unavailable, or frida instrumentation failed), the verdict
    # rests on static signals alone. Widen the confidence band and say so, rather
    # than presenting a static-only result as if it were fully verified.
    confidence_interval = 5.0
    if not dynamic_observed:
        confidence_interval = 12.0
        notes.append(
            "Static-only analysis: no runtime observations were captured; "
            "verdict rests on static evidence and confidence is reduced."
        )

    calibrated = _calibrate(evidence)
    return RiskScore(
        evidence_score=round(evidence, 1),
        components=comp,
        weights=dict(WEIGHTS),
        calibrated_score=round(calibrated, 1),
        confidence_interval=confidence_interval,
        verdict=_verdict(calibrated),
        notes=notes,
    )


def _calibrate(evidence_score: float) -> float:
    """Layer B. Uses a trained model when present, otherwise identity."""
    return calibrate_score(evidence_score)


def _verdict(score: float) -> Verdict:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    if score >= 15:
        return "LOW"
    return "CLEAN"
