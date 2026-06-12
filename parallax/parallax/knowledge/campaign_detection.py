"""Campaign detection via community detection over shared infrastructure.

Two APKs that talk to the same C2 domains/IPs are likely the same campaign.
We build a weighted APK-APK graph (edge weight = count of shared indicators),
run Louvain community detection, and write a Campaign node with PART_OF edges
for each non-trivial community.
"""

from __future__ import annotations

import logging

from parallax.knowledge.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

# APK pairs that share at least one Domain or IPAddress, with the shared count.
_SHARED_EDGES = """
MATCH (a:APK)-[:COMMUNICATES_WITH]->(n)<-[:COMMUNICATES_WITH]-(b:APK)
WHERE a.sha256 < b.sha256
RETURN a.sha256 AS src, b.sha256 AS dst, count(DISTINCT n) AS weight
"""

_WRITE_CAMPAIGN = """
MERGE (c:Campaign {name: $name})
ON CREATE SET c.start_date = datetime(), c.status = 'active'
SET c.size = $size, c.detected_at = datetime()
WITH c
UNWIND $members AS sha
MATCH (a:APK {sha256: sha})
MERGE (a)-[:PART_OF]->(c)
"""


async def detect_campaigns(min_size: int = 2) -> list[dict]:
    """Cluster APKs into campaigns by shared infrastructure. Returns clusters."""
    try:
        import networkx as nx
    except ImportError:
        logger.warning("networkx not installed; campaign detection unavailable.")
        return []

    edges = await neo4j_client.run_read(_SHARED_EDGES)
    if not edges:
        return []

    graph = nx.Graph()
    for e in edges:
        graph.add_edge(e["src"], e["dst"], weight=e["weight"])

    try:
        communities = nx.community.louvain_communities(graph, weight="weight", seed=42)
    except Exception:
        # Fallback to connected components if Louvain is unavailable.
        communities = list(nx.connected_components(graph))

    clusters: list[dict] = []
    for idx, members in enumerate(sorted(communities, key=len, reverse=True)):
        members = sorted(members)
        if len(members) < min_size:
            continue
        # Deterministic campaign name from the smallest member hash.
        name = f"CAMPAIGN-{members[0][:12]}"
        await neo4j_client.run_write(_WRITE_CAMPAIGN, name=name, members=members, size=len(members))
        clusters.append({"campaign": name, "size": len(members), "members": members})

    logger.info("Detected %d campaigns", len(clusters))
    return clusters
