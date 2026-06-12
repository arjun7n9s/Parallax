"""Populate the TAIG graph from a completed analysis.

Every analyzed APK becomes a subgraph: the APK node plus its permissions,
network destinations, ATT&CK techniques, impersonated bank, family and campaign
links. All writes use MERGE so re-running an analysis updates rather than
duplicates. Node keys match ``scripts/init_neo4j.py`` / ``06_TAIG_SCHEMA.md``.
"""

from __future__ import annotations

import logging

from parallax.ai.schemas import CortexResult
from parallax.knowledge.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

_APK_MERGE = """
MERGE (a:APK {sha256: $sha256})
ON CREATE SET a.first_seen = datetime(), a.created_at = datetime()
SET a.package = $package,
    a.app_name = $app_name,
    a.risk_score = $risk_score,
    a.verdict = $verdict,
    a.analyzed_at = datetime()
"""

_PERMS = """
MATCH (a:APK {sha256: $sha256})
UNWIND $permissions AS perm
MERGE (p:Permission {name: perm})
MERGE (a)-[:REQUESTS]->(p)
"""

_DOMAINS = """
MATCH (a:APK {sha256: $sha256})
UNWIND $domains AS d
MERGE (dom:Domain {fqdn: d})
ON CREATE SET dom.first_seen = datetime()
MERGE (a)-[:COMMUNICATES_WITH]->(dom)
"""

_IPS = """
MATCH (a:APK {sha256: $sha256})
UNWIND $ips AS ip
MERGE (i:IPAddress {value: ip})
ON CREATE SET i.first_seen = datetime()
MERGE (a)-[:COMMUNICATES_WITH]->(i)
"""

_TECHNIQUES = """
MATCH (a:APK {sha256: $sha256})
UNWIND $techniques AS tid
MERGE (t:ATTCKTechnique {technique_id: tid})
MERGE (a)-[:USES_TECHNIQUE]->(t)
"""

_IMPERSONATES = """
MATCH (a:APK {sha256: $sha256})
MERGE (b:BankApp {package: $bank_key})
ON CREATE SET b.name = $bank_name
MERGE (a)-[r:IMPERSONATES]->(b)
SET r.confidence = $confidence
"""

_FAMILY = """
MATCH (a:APK {sha256: $sha256})
MERGE (f:Family {name: $family})
MERGE (a)-[r:ATTRIBUTED_TO_FAMILY]->(f)
SET r.confidence = $confidence
"""


async def populate_graph(
    *,
    sha256: str,
    package: str,
    app_name: str,
    permissions: list[str],
    cortex: CortexResult,
) -> dict:
    """Write the APK subgraph. Returns a summary of nodes/edges written."""
    summary = {"permissions": 0, "domains": 0, "ips": 0, "techniques": 0}
    try:
        await neo4j_client.run_write(
            _APK_MERGE,
            sha256=sha256,
            package=package or "unknown",
            app_name=app_name or "",
            risk_score=cortex.risk.calibrated_score,
            verdict=cortex.verdict,
        )

        if permissions:
            await neo4j_client.run_write(_PERMS, sha256=sha256, permissions=permissions)
            summary["permissions"] = len(permissions)

        domains = cortex.iocs.get("domains", [])
        if domains:
            await neo4j_client.run_write(_DOMAINS, sha256=sha256, domains=domains)
            summary["domains"] = len(domains)

        ips = cortex.iocs.get("ips", [])
        if ips:
            await neo4j_client.run_write(_IPS, sha256=sha256, ips=ips)
            summary["ips"] = len(ips)

        if cortex.attck_techniques:
            await neo4j_client.run_write(
                _TECHNIQUES, sha256=sha256, techniques=cortex.attck_techniques
            )
            summary["techniques"] = len(cortex.attck_techniques)

        visual = cortex.visual
        if visual and visual.phishing_detected and visual.brand_impersonation:
            await neo4j_client.run_write(
                _IMPERSONATES,
                sha256=sha256,
                bank_key=visual.brand_impersonation.lower().replace(" ", "_"),
                bank_name=visual.brand_impersonation,
                confidence=visual.brand_impersonation_score,
            )

        intel = cortex.intel_correlator
        if intel and intel.family_attribution:
            await neo4j_client.run_write(
                _FAMILY,
                sha256=sha256,
                family=intel.family_attribution,
                confidence=intel.family_confidence,
            )

        logger.info("TAIG populated for %s: %s", sha256, summary)
    except Exception as exc:
        logger.warning("Graph population failed for %s: %s", sha256, exc)
    return summary
