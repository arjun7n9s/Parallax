"""Synthetic Band demo case loader. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

from datetime import datetime, timezone


def synthetic_fraud_case() -> dict:
    """Return deterministic synthetic data for the Band demo transcript."""
    return {
        "case_id": "CASE-FR-2026-00421",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "customer_report": (
            "INR 3.4L lost after installing 'SBI YONO KYC Update' APK from a WhatsApp link."
        ),
        "transactions": [
            {"amount_inr": 52000, "beneficiary": "upi-mule-001", "minute": 0},
            {"amount_inr": 48000, "beneficiary": "upi-mule-002", "minute": 2},
            {"amount_inr": 75000, "beneficiary": "upi-mule-003", "minute": 4},
            {"amount_inr": 65000, "beneficiary": "upi-mule-001", "minute": 7},
            {"amount_inr": 100000, "beneficiary": "upi-mule-002", "minute": 11},
        ],
        "policy_context": {
            "reported_after_minutes": 41,
            "credential_shared": False,
            "synthetic": True,
        },
    }
