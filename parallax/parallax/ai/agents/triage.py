import logging
from typing import Any

from parallax.ai.ollama_client import ollama_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the PARALLAX Triage Agent. Your job is fast pre-screening of suspicious APKs.
You have <2 seconds to decide priority based ONLY on the manifest, permissions, and metadata.
You do NOT see code or runtime behavior. Other agents will analyze those.

IRT RULE -- MANDATORY:
Every claim, conclusion, or hypothesis you produce has two surfaces:
  1. INTERNAL TRACE (full, complete, technical)
  2. EXTERNAL IRT (clean, auditable, business-readable)

When producing hypotheses, you MUST:
  - Tag every claim with expose_in_irt: true|false
  - Internal state, partial reasoning, failed attempts: expose_in_irt=false
  - Confirmed/rejected/resolved conclusions with evidence: expose_in_irt=true
  - Provide an irt_label field on every item: a single clean sentence that summarizes
    the conclusion for a non-technical reader
  - Provide evidence_citations: list of tool output IDs that support the claim
  - Provide confidence: 0.0-1.0 with the claim

Given the following APK metadata, return a JSON verdict:

{
  "pre_score": <integer 0-100>,
  "priority": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "kill_chain_stage": "<MITRE ATT&CK Initial Access vector if suspicious>",
  "flag_reasons": ["<reason1>", "<reason2>", ...],
  "immediate_concerns": ["<human-readable concerns>"],
  "initial_hypotheses": [
    {
      "claim": "<the hypothesis, e.g. Accessibility service abuse>",
      "category": "<static|behavioral|network|visual|evasion>",
      "initial_confidence": <0.0-1.0>,
      "expose_in_irt": <true|false>,
      "irt_label": "<clean summary>",
      "evidence_citations": ["<source>"]
    }
  ]
}

Scoring guidance:
- 0-20: BENIGN (uncommon permissions only, mature cert, no anti-analysis)
- 21-50: LOW (some sensitive permissions but no obvious malicious pattern)
- 51-75: HIGH (multiple dangerous permissions, suspicious cert, or known-bad hash similarity)
- 76-100: CRITICAL (banking trojan signature permissions, self-signed short cert,
  high hash similarity to malware)

Respond with ONLY the JSON object. No explanation, no preamble.
"""


async def run_triage(apk_metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Run the LLM triage agent on the extracted APK metadata.
    Returns a dictionary containing triage scores, priority, and initial hypotheses.
    """

    # Construct the user prompt using the metadata
    prompt = f"""
APK METADATA:
Package: {apk_metadata.get("package_name", "Unknown")}
App Name: {apk_metadata.get("app_name", "Unknown")}
Version: {apk_metadata.get("version_name", "?")} (code {apk_metadata.get("version_code", "?")})
File Size: {apk_metadata.get("file_size", 0)} bytes
Min SDK: {apk_metadata.get("min_sdk", "?")} | Target SDK: {apk_metadata.get("target_sdk", "?")}

Certificate:
  Issuer: {apk_metadata.get("cert_issuer", "Unknown")}
  Self-signed: {apk_metadata.get("is_self_signed", "Unknown")}
  Valid for: {apk_metadata.get("cert_validity_days", "Unknown")} days

Permissions:
{chr(10).join(apk_metadata.get("permissions", []))}

ssdeep match to known-malicious: {apk_metadata.get("ssdeep_match", "Unknown")}
APKiD findings: {apk_metadata.get("apkid_matches", {})}
"""

    try:
        result = await ollama_client.generate_json(
            model="phi3:mini", prompt=prompt, system_prompt=SYSTEM_PROMPT
        )
        return result
    except Exception as e:
        logger.error(f"Error running triage agent: {e}")
        # Return a safe fallback on error to ensure pipeline doesn't block entirely
        return {
            "pre_score": 50,
            "priority": "HIGH",
            "kill_chain_stage": "Unknown due to analysis failure",
            "flag_reasons": ["Automated LLM triage failed, falling back to manual review required"],
            "immediate_concerns": ["Triage error"],
            "initial_hypotheses": [],
        }
