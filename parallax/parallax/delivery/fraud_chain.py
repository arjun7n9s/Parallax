"""Fraud Attack Chain builder — the bank-specific output (not just ATT&CK).

Maps a CortexResult onto the 10-stage fraud narrative banks actually use, with
per-stage evidence and a recommended fraud control. Each stage is only emitted
when the analysis produced evidence for it, so the chain reflects this APK
rather than a generic template.
"""

from __future__ import annotations

from parallax.ai.schemas import CortexResult

# Ordered fraud-chain stages.
STAGES = [
    "distribution",
    "brand_impersonation",
    "permission_acquisition",
    "credential_capture",
    "otp_interception",
    "device_fingerprinting",
    "transaction_enablement",
    "persistence_evasion",
    "exfiltration",
]

_SMS_PERMS = {"android.permission.RECEIVE_SMS", "android.permission.READ_SMS"}
_FINGERPRINT_PERMS = {
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_CONTACTS",
    "android.permission.ACCESS_FINE_LOCATION",
}


def _evidence_has(cortex: CortexResult, *needles: str) -> list[str]:
    hits: list[str] = []
    code = cortex.code_interpreter
    pools: list[str] = []
    if code:
        pools += code.evidence + code.attack_flow
    if cortex.behavior_analyst:
        pools += cortex.behavior_analyst.observed_behaviors
    for item in pools:
        low = item.lower()
        if any(n in low for n in needles):
            hits.append(item)
    return hits


def build_fraud_chain(cortex: CortexResult, permissions: list[str]) -> list[dict]:
    """Return the ordered fraud-chain stages with evidence + recommended control."""
    perms = set(permissions)
    stages: list[dict] = []

    def add(stage: str, description: str, evidence: list[str], control: str):
        if evidence:
            stages.append(
                {
                    "stage": stage,
                    "order": STAGES.index(stage) if stage in STAGES else 99,
                    "description": description,
                    "evidence": evidence[:5],
                    "recommended_control": control,
                }
            )

    # Brand impersonation (visual).
    if cortex.visual and cortex.visual.phishing_detected:
        add(
            "brand_impersonation",
            f"Impersonates {cortex.visual.brand_impersonation} "
            f"(visual similarity {cortex.visual.brand_impersonation_score:.0%}).",
            [f"phishing UI for {cortex.visual.brand_impersonation}"],
            "Issue customer advisory naming the impersonated brand; takedown request.",
        )

    # Permission acquisition.
    risky = [p for p in perms if "ACCESSIBILITY" in p or "SMS" in p or "ALERT_WINDOW" in p]
    add(
        "permission_acquisition",
        "Requests high-risk permissions enabling overlay, SMS and input control.",
        risky,
        "Flag installs requesting accessibility + SMS + overlay together.",
    )

    # Credential capture (overlay / accessibility / webview).
    add(
        "credential_capture",
        "Captures credentials via overlay / accessibility / fake form.",
        _evidence_has(cortex, "accessibility", "overlay", "webview", "credential", "edittext"),
        "Detect accessibility-service activation while a banking app is foregrounded.",
    )

    # OTP interception.
    otp_ev = _evidence_has(cortex, "sms", "otp", "smsmessage", "getmessagebody")
    if _SMS_PERMS & perms:
        otp_ev = otp_ev or ["SMS read/receive permissions requested"]
    add(
        "otp_interception",
        "Intercepts SMS to capture one-time passwords.",
        otp_ev,
        "Step-up to app-less OTP (push) and block SMS-OTP for flagged devices.",
    )

    # Device fingerprinting.
    fp_ev = _evidence_has(cortex, "getdeviceid", "imei", "subscriberid", "getinstalledapplications")
    if _FINGERPRINT_PERMS & perms:
        fp_ev = fp_ev or ["device/contact/location permissions requested"]
    add(
        "device_fingerprinting",
        "Collects device identifiers and installed-app inventory.",
        fp_ev,
        "Correlate device fingerprint reuse across fraud reports.",
    )

    # Transaction enablement.
    add(
        "transaction_enablement",
        "Automates in-app actions to enable fraudulent transactions.",
        _evidence_has(cortex, "input injection", "autofill", "performaction", "gesture"),
        "Require human-present challenge for high-value transfers.",
    )

    # Persistence / evasion.
    add(
        "persistence_evasion",
        "Resists removal and evades analysis.",
        _evidence_has(cortex, "device admin", "boot_completed", "anti", "obfuscat", "packed"),
        "Block device-admin escalation by untrusted apps.",
    )

    # Exfiltration (network IOCs).
    exfil_ev = list(cortex.iocs.get("domains", [])) + list(cortex.iocs.get("ips", []))
    add(
        "exfiltration",
        "Exfiltrates captured data to attacker C2 infrastructure.",
        exfil_ev,
        "Blocklist C2 indicators at DNS/perimeter; share via MISP.",
    )

    stages.sort(key=lambda s: s["order"])
    return stages
