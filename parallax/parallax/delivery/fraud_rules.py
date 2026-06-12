"""Generate deployable fraud / detection rules from a verdict.

Produces a vendor-neutral rule DSL plus Suricata signatures for the network
IOCs, so a bank can import detections directly into its fraud engine / SIEM.
All rules are emitted as suggestions for analyst approval (see approval modes).
"""

from __future__ import annotations

from parallax.ai.schemas import CortexResult


def _suricata_rules(cortex: CortexResult, start_sid: int = 9100000) -> list[str]:
    rules: list[str] = []
    sid = start_sid
    for dom in cortex.iocs.get("domains", []):
        rules.append(
            f'alert dns any any -> any any (msg:"PARALLAX C2 domain {dom}"; '
            f'dns.query; content:"{dom}"; nocase; sid:{sid}; rev:1;)'
        )
        sid += 1
    for ip in cortex.iocs.get("ips", []):
        rules.append(
            f'alert ip any any -> {ip} any (msg:"PARALLAX C2 IP {ip}"; sid:{sid}; rev:1;)'
        )
        sid += 1
    return rules


def generate_fraud_rules(sha256: str, package: str, cortex: CortexResult) -> dict:
    """Return a bundle of fraud/detection rules derived from the analysis."""
    dsl_rules: list[dict] = []

    # Behavioral fraud rules keyed off confirmed capabilities.
    code = cortex.code_interpreter
    intent = code.intent_classification if code else "uncertain"

    if cortex.verdict in ("CRITICAL", "HIGH"):
        dsl_rules.append(
            {
                "id": f"PARALLAX-{sha256[:8]}-INSTALL",
                "when": "app_install",
                "condition": {
                    "requests_permissions_all_of": [
                        "android.permission.BIND_ACCESSIBILITY_SERVICE",
                        "android.permission.RECEIVE_SMS",
                    ]
                },
                "action": "alert_and_hold",
                "approval_mode": "HELD",
                "rationale": f"Matches {intent} install profile (verdict {cortex.verdict}).",
            }
        )

    if any("otp" in f.lower() or "sms" in f.lower() for f in cortex.technical_findings):
        dsl_rules.append(
            {
                "id": f"PARALLAX-{sha256[:8]}-OTP",
                "when": "transaction_auth",
                "condition": {"sms_otp_used": True, "accessibility_service_active": True},
                "action": "step_up_to_push_auth",
                "approval_mode": "HELD",
                "rationale": "SMS-OTP interception capability observed.",
            }
        )

    for dom in cortex.iocs.get("domains", []):
        dsl_rules.append(
            {
                "id": f"PARALLAX-{sha256[:8]}-C2-{dom}",
                "when": "network_egress",
                "condition": {"destination_domain": dom},
                "action": "block",
                "approval_mode": "AUTO_LOW_RISK",
                "rationale": "Confirmed C2 destination.",
            }
        )

    return {
        "dsl": dsl_rules,
        "suricata": _suricata_rules(cortex),
    }
