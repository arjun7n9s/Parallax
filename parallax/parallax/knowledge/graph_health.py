"""TAIG graph health checks for Phase 2.5 validation.

The checks are intentionally small and deterministic so they can run from an
API endpoint, a scheduled daily job, or a corpus-validation script.
"""

from __future__ import annotations

import logging

from parallax.core.metrics import record_graph_health
from parallax.knowledge.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

_NODE_COUNTS = """
MATCH (n)
RETURN coalesce(labels(n)[0], 'Unlabeled') AS label, count(n) AS count
ORDER BY label
"""

_EDGE_COUNTS = """
MATCH ()-[r]->()
RETURN type(r) AS type, count(r) AS count
ORDER BY type
"""

_ORPHAN_APKS = """
MATCH (a:APK)
WHERE NOT (a)--()
RETURN count(a) AS count
"""

_ORPHAN_IOCS = """
MATCH (n)
WHERE (n:Domain OR n:IPAddress) AND NOT ()-[:COMMUNICATES_WITH]->(n)
RETURN count(n) AS count
"""

_MISSING_KEY_NODES = """
MATCH (n)
WHERE (n:APK AND (n.sha256 IS NULL OR n.sha256 = ''))
   OR (n:Domain AND (n.fqdn IS NULL OR n.fqdn = ''))
   OR (n:IPAddress AND (n.value IS NULL OR n.value = ''))
   OR (n:Family AND (n.name IS NULL OR n.name = ''))
   OR (n:ATTCKTechnique AND (n.technique_id IS NULL OR n.technique_id = ''))
RETURN count(n) AS count
"""

_BROKEN_RELATIONSHIPS = """
MATCH (a:APK)-[r]->(n)
WHERE (type(r) = 'COMMUNICATES_WITH' AND n:Domain AND (n.fqdn IS NULL OR n.fqdn = ''))
   OR (type(r) = 'COMMUNICATES_WITH' AND n:IPAddress AND (n.value IS NULL OR n.value = ''))
   OR (type(r) = 'ATTRIBUTED_TO_FAMILY' AND n:Family AND (n.name IS NULL OR n.name = ''))
   OR (type(r) = 'USES_TECHNIQUE' AND n:ATTCKTechnique AND (n.technique_id IS NULL OR n.technique_id = ''))
RETURN count(r) AS count
"""


def _count(rows: list[dict]) -> int:
    return int(rows[0].get("count", 0)) if rows else 0


async def collect_graph_health() -> dict:
    """Return graph health snapshot and update Prometheus gauges.

    ``status`` is ``green`` when the graph has no orphan APKs, missing key
    nodes, or broken domain-specific relationships. A Neo4j failure returns a
    ``down`` snapshot instead of raising so health endpoints remain readable.
    """
    try:
        node_rows = await neo4j_client.run_read(_NODE_COUNTS)
        edge_rows = await neo4j_client.run_read(_EDGE_COUNTS)
        orphan_apks = _count(await neo4j_client.run_read(_ORPHAN_APKS))
        orphan_iocs = _count(await neo4j_client.run_read(_ORPHAN_IOCS))
        missing_key_nodes = _count(await neo4j_client.run_read(_MISSING_KEY_NODES))
        broken_relationships = _count(await neo4j_client.run_read(_BROKEN_RELATIONSHIPS))
    except Exception as exc:
        logger.warning("TAIG health check failed: %s", exc)
        snapshot = {
            "status": "down",
            "node_counts": {},
            "edge_counts": {},
            "orphan_apks": 0,
            "orphan_iocs": 0,
            "missing_key_nodes": 0,
            "broken_relationships": 0,
            "error": str(exc),
        }
        record_graph_health(snapshot)
        return snapshot

    snapshot = {
        "status": (
            "green"
            if orphan_apks == 0 and missing_key_nodes == 0 and broken_relationships == 0
            else "degraded"
        ),
        "node_counts": {str(r.get("label", "unknown")): int(r.get("count", 0)) for r in node_rows},
        "edge_counts": {str(r.get("type", "unknown")): int(r.get("count", 0)) for r in edge_rows},
        "orphan_apks": orphan_apks,
        "orphan_iocs": orphan_iocs,
        "missing_key_nodes": missing_key_nodes,
        "broken_relationships": broken_relationships,
    }
    record_graph_health(snapshot)
    return snapshot
