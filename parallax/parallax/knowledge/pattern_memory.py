"""Malware Pattern Memory — the named, self-enriching pattern subsystem.

Eight explicit pattern categories (vision §Pillar 2). Each completed analysis
extracts patterns and appends them to the store (Neo4j ``Pattern`` nodes), and
each APK is linked to the patterns it matches. The store is queryable and grows
with every sample — the compounding-intelligence loop.
"""

from __future__ import annotations

import hashlib
import logging

from parallax.ai.schemas import CortexResult
from parallax.knowledge.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

CATEGORIES = [
    "fraud_flow",
    "permission_api_chain",
    "code_idiom",
    "ui_phishing_template",
    "c2_pattern",
    "certificate_reuse",
    "packer_fingerprint",
    "behavioral_timing",
]

_MERGE_PATTERN = """
MATCH (a:APK {sha256: $sha256})
UNWIND $patterns AS pat
MERGE (p:Pattern {pattern_id: pat.pattern_id})
ON CREATE SET p.category = pat.category, p.signature = pat.signature,
              p.signature_type = pat.signature_type, p.first_seen = datetime(),
              p.hit_count = 0
SET p.hit_count = coalesce(p.hit_count, 0) + 1, p.last_seen = datetime()
MERGE (a)-[r:MATCHES_PATTERN]->(p)
SET r.confidence = pat.confidence, r.matched_at = datetime()
"""


def _pid(category: str, signature: str) -> str:
    digest = hashlib.sha256(f"{category}:{signature}".encode()).hexdigest()[:16]
    return f"PAT-{category}-{digest}"


def _signature(text: str) -> str:
    """Canonical signature used for both storage and stable pattern IDs."""
    return " ".join(str(text or "").split())[:300]


def extract_patterns(
    cortex: CortexResult, permissions: list[str], apkid: dict | None
) -> list[dict]:
    """Derive patterns from a completed analysis."""
    patterns: list[dict] = []
    seen: set[str] = set()

    def add(category: str, signature: str, sig_type: str, confidence: float):
        signature = _signature(signature)
        pattern_id = _pid(category, signature)
        if signature and pattern_id not in seen:
            seen.add(pattern_id)
            patterns.append(
                {
                    "pattern_id": pattern_id,
                    "category": category,
                    "signature": signature,
                    "signature_type": sig_type,
                    "confidence": round(max(0.0, min(1.0, confidence)), 3),
                }
            )

    # Fraud flow: the ordered attack flow from the code interpreter.
    code = cortex.code_interpreter
    if code and code.attack_flow:
        add("fraud_flow", " -> ".join(code.attack_flow), "sequence", code.confidence)

    behavior = cortex.behavior_analyst
    phases = cortex.kill_chain or (behavior.kill_chain if behavior else [])
    if phases:
        flow_steps = []
        timing_steps = []
        for phase in phases:
            actions = ", ".join(dict.fromkeys(phase.actions[:4]))
            if actions:
                flow_steps.append(f"{phase.phase}:{actions}")
            if phase.duration_ms > 0:
                timing_steps.append(f"{phase.phase}:{_duration_bucket(phase.duration_ms)}")
        if flow_steps:
            add(
                "fraud_flow",
                " -> ".join(flow_steps),
                "runtime_sequence",
                behavior.confidence if behavior else 0.7,
            )
        if timing_steps:
            add("behavioral_timing", " -> ".join(timing_steps), "duration_bucket", 0.6)

    # Permission/API chain: the high-risk permission set.
    risky = sorted(
        p for p in permissions if "SMS" in p or "ACCESSIBILITY" in p or "ALERT_WINDOW" in p
    )
    if len(risky) >= 2:
        add("permission_api_chain", "+".join(risky), "permission_set", 0.8)

    # C2 pattern: each C2 destination.
    for dom in cortex.iocs.get("domains", []):
        add("c2_pattern", dom, "domain", 0.7)
    for ip in cortex.iocs.get("ips", []):
        add("c2_pattern", ip, "ip", 0.7)

    # UI phishing template: impersonated brand.
    if cortex.visual and cortex.visual.phishing_detected and cortex.visual.brand_impersonation:
        add(
            "ui_phishing_template",
            f"overlay:{cortex.visual.brand_impersonation}",
            "brand",
            cortex.visual.brand_impersonation_score,
        )

    # Packer fingerprint: APKiD packer/protector signals.
    if apkid:
        text = str(apkid.get("matches") or apkid.get("files") or "").lower()
        for marker in ("dexguard", "packer", "protector", "obfuscator"):
            if marker in text:
                add("packer_fingerprint", marker, "apkid", 0.6)
                break

    # Code idiom: distinctive class roles and source->sink method behavior.
    if code:
        for cr in code.class_roles[:5]:
            if cr.role and cr.confidence >= 0.65:
                evidence = " | ".join(sorted(cr.evidence[:3]))
                add("code_idiom", f"{cr.role}:{evidence or 'role-only'}", "role", cr.confidence)
        for mi in code.method_intents[:8]:
            if mi.intent and (mi.sources or mi.sinks):
                sources = ",".join(sorted(dict.fromkeys(mi.sources)))
                sinks = ",".join(sorted(dict.fromkeys(mi.sinks)))
                add("code_idiom", f"{mi.intent}|src:{sources}|sink:{sinks}", "source_sink", 0.75)

    return patterns


def _duration_bucket(duration_ms: int) -> str:
    if duration_ms < 1_000:
        return "<1s"
    if duration_ms < 10_000:
        return "1-10s"
    if duration_ms < 60_000:
        return "10-60s"
    return ">=60s"


async def enrich_pattern_memory(
    sha256: str, cortex: CortexResult, permissions: list[str], apkid: dict | None
) -> int:
    """Extract and persist patterns for a sample. Returns count stored."""
    patterns = extract_patterns(cortex, permissions, apkid)
    if not patterns:
        return 0
    try:
        await neo4j_client.run_write(_MERGE_PATTERN, sha256=sha256, patterns=patterns)
    except Exception as exc:
        logger.warning("Pattern memory enrichment failed for %s: %s", sha256, exc)
        return 0
    return len(patterns)


async def query_patterns(category: str | None = None, limit: int = 50) -> list[dict]:
    """Return stored patterns, optionally filtered by category, by frequency."""
    if category:
        cypher = (
            "MATCH (p:Pattern {category:$category}) "
            "RETURN p.pattern_id AS id, p.category AS category, p.signature AS signature, "
            "p.hit_count AS hits ORDER BY p.hit_count DESC LIMIT $limit"
        )
        return await neo4j_client.run_read(cypher, category=category, limit=limit)
    cypher = (
        "MATCH (p:Pattern) RETURN p.pattern_id AS id, p.category AS category, "
        "p.signature AS signature, p.hit_count AS hits ORDER BY p.hit_count DESC LIMIT $limit"
    )
    return await neo4j_client.run_read(cypher, limit=limit)
