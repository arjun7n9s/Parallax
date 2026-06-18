# Sales Collateral Checklist

Use this checklist to prepare buyer-facing material without overclaiming validation status.

## One-Page Summary

- Product: PARALLAX, an evidence-first APK malware and banking-fraud analysis platform.
- Buyer: bank SOC, fraud, malware reverse-engineering, and platform security teams.
- Problem: Android banking malware triage is slow, noisy, and hard to audit.
- Differentiator: deterministic analysis, dynamic instrumentation, agentic synthesis, structured reports, and graph-backed memory.
- Proof status: architecture and workflow are implemented; corpus accuracy and calibrated-risk claims require the Phase 2 validation run.

## Demo Script

1. Submit an APK through the analyst console.
2. Watch status progress through queued, static, dynamic, reasoning, delivery, and complete.
3. Open the analysis detail page.
4. Review verdict, confidence, ATT&CK mapping, IOCs, and recommendations.
5. Download PDF, HTML, STIX, and YARA artifacts.
6. Open graph health and hunt queries.
7. Show Prometheus/Grafana cost and reliability panels.

## Case Study Template

Create one case study per validated sample family after the corpus run:

- Sample family and SHA256
- Ground-truth source and collection date
- PARALLAX verdict and score
- Key static evidence
- Key dynamic evidence
- Family attribution rationale
- Analyst action taken
- False-positive or uncertainty notes

## Do Not Claim Yet

- Any percentage accuracy without the validation CSV and report.
- Calibrated risk without a trained `parallax/ai/calibration/model.json`.
- Cost per sample without a measured pilot or corpus run.
- Production DR readiness without a managed restore proof.
- Live HTTPS exfiltration capture without an end-to-end mitmproxy run.
