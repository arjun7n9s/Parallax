"""Tests for TAIG graph health and Phase 2.5 hunt templates."""

import pytest

from parallax.api.routes import hunt
from parallax.knowledge import graph_health


@pytest.mark.asyncio
async def test_collect_graph_health_green(monkeypatch):
    async def fake_run_read(cypher, **params):
        if "RETURN coalesce(labels(n)[0]" in cypher:
            return [{"label": "APK", "count": 2}, {"label": "Domain", "count": 1}]
        if "RETURN type(r) AS type" in cypher:
            return [{"type": "COMMUNICATES_WITH", "count": 2}]
        return [{"count": 0}]

    monkeypatch.setattr(graph_health.neo4j_client, "run_read", fake_run_read)

    snapshot = await graph_health.collect_graph_health()

    assert snapshot["status"] == "green"
    assert snapshot["node_counts"]["APK"] == 2
    assert snapshot["edge_counts"]["COMMUNICATES_WITH"] == 2
    assert snapshot["orphan_apks"] == 0
    assert snapshot["broken_relationships"] == 0


@pytest.mark.asyncio
async def test_collect_graph_health_degraded_on_orphans(monkeypatch):
    async def fake_run_read(cypher, **params):
        if "RETURN coalesce(labels(n)[0]" in cypher:
            return [{"label": "APK", "count": 1}]
        if "RETURN type(r) AS type" in cypher:
            return []
        if "MATCH (a:APK)" in cypher and "WHERE NOT (a)--()" in cypher:
            return [{"count": 1}]
        return [{"count": 0}]

    monkeypatch.setattr(graph_health.neo4j_client, "run_read", fake_run_read)

    snapshot = await graph_health.collect_graph_health()

    assert snapshot["status"] == "degraded"
    assert snapshot["orphan_apks"] == 1


@pytest.mark.asyncio
async def test_collect_graph_health_down_on_neo4j_error(monkeypatch):
    async def fake_run_read(cypher, **params):
        raise RuntimeError("neo4j down")

    monkeypatch.setattr(graph_health.neo4j_client, "run_read", fake_run_read)

    snapshot = await graph_health.collect_graph_health()

    assert snapshot["status"] == "down"
    assert snapshot["error"] == "neo4j down"


@pytest.mark.asyncio
async def test_hunt_passes_cross_sample_parameters(monkeypatch):
    calls = []

    async def fake_run_read(cypher, **params):
        calls.append({"cypher": cypher, "params": params})
        return [{"sha256": "b" * 64, "ioc": "evil.example"}]

    monkeypatch.setattr(hunt.neo4j_client, "run_read", fake_run_read)

    result = await hunt.run_hunt(
        hunt.HuntRequest(
            hunt="samples_sharing_c2_with",
            sha256="a" * 64,
            family="Cerberus",
            days=7,
            limit=10,
        )
    )

    assert result["count"] == 1
    assert "target:APK" in calls[0]["cypher"]
    assert calls[0]["params"]["sha256"] == "a" * 64
    assert calls[0]["params"]["family"] == "Cerberus"
    assert calls[0]["params"]["days"] == 7


def test_hunt_templates_include_phase_25_gates():
    assert "samples_sharing_c2_with" in hunt.HUNTS
    assert "family_variants" in hunt.HUNTS
    assert "emerging_campaigns" in hunt.HUNTS
