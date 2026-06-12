"""Integration tests for the TAIG knowledge layer (live Neo4j/Qdrant).

Skipped automatically when the data services are not reachable, so the unit
suite stays runnable in isolation.
"""

import asyncio

import pytest

from parallax.ai.schemas import CortexResult, RiskScore
from parallax.knowledge.campaign_detection import detect_campaigns
from parallax.knowledge.neo4j_client import neo4j_client
from parallax.knowledge.population import populate_graph

_TEST_PREFIX = "pytestapk"


def _neo4j_available() -> bool:
    async def _check() -> bool:
        try:
            return await neo4j_client.ping()
        finally:
            # Reset the cached driver so the test creates a fresh one bound to
            # pytest-asyncio's loop (the ping ran in this throwaway loop).
            await neo4j_client.close()

    try:
        return asyncio.run(_check())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _neo4j_available(), reason="Neo4j not reachable")


def _cortex(sha: str, domains: list[str]) -> CortexResult:
    return CortexResult(
        sha256=sha,
        verdict="HIGH",
        risk=RiskScore(calibrated_score=72.0, verdict="HIGH"),
        attck_techniques=["T1582"],
        iocs={"domains": domains, "ips": [], "urls": []},
    )


@pytest.mark.asyncio
async def test_population_and_campaign_detection():
    sha_a = _TEST_PREFIX + "a" * 56
    sha_b = _TEST_PREFIX + "b" * 56
    shared_domain = "pytest-shared-c2.example"
    try:
        await populate_graph(
            sha256=sha_a,
            package="com.pytest.a",
            app_name="A",
            permissions=["android.permission.RECEIVE_SMS"],
            cortex=_cortex(sha_a, [shared_domain]),
        )
        await populate_graph(
            sha256=sha_b,
            package="com.pytest.b",
            app_name="B",
            permissions=["android.permission.RECEIVE_SMS"],
            cortex=_cortex(sha_b, [shared_domain]),
        )

        clusters = await detect_campaigns(min_size=2)
        members = {m for c in clusters for m in c["members"]}
        assert sha_a in members and sha_b in members

        # The two APKs must share the C2 domain in the graph.
        rows = await neo4j_client.run_read(
            "MATCH (a:APK)-[:COMMUNICATES_WITH]->(d:Domain {fqdn:$d}) RETURN count(a) AS n",
            d=shared_domain,
        )
        assert rows[0]["n"] == 2
    finally:
        await neo4j_client.run_write(
            "MATCH (a:APK) WHERE a.sha256 STARTS WITH $p DETACH DELETE a", p=_TEST_PREFIX
        )
        await neo4j_client.run_write("MATCH (d:Domain {fqdn:$d}) DETACH DELETE d", d=shared_domain)
        await neo4j_client.run_write(
            "MATCH (c:Campaign) WHERE c.name STARTS WITH 'CAMPAIGN-' + $p DETACH DELETE c",
            p=_TEST_PREFIX,
        )
