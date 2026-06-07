"""
Unit tests for basic API endpoints.

The readiness test mocks all backing-service clients so it is deterministic
regardless of whether Postgres/Redis/etc. are running on the test machine.
"""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the /health liveness probe — always returns 200 if process is alive."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PARALLAX"
    assert "version" in data


def test_readiness_all_services_down(client: TestClient) -> None:
    """
    When every backing service is unreachable, /ready should return 503 degraded
    with an error entry for each service.
    """
    with (
        patch("parallax.api.main.asyncpg") as mock_asyncpg,
        patch("parallax.api.main.redis_lib") as mock_redis,
        patch("parallax.api.main.GraphDatabase") as mock_neo4j,
        patch("parallax.api.main.QdrantClient") as mock_qdrant,
        patch("parallax.api.main.Minio") as mock_minio,
        patch("parallax.api.main.httpx") as mock_httpx,
    ):
        # Make every client raise on connect
        mock_asyncpg.connect = AsyncMock(side_effect=ConnectionRefusedError("postgres down"))
        mock_redis.Redis.return_value.ping.side_effect = ConnectionRefusedError("redis down")
        mock_neo4j.driver.return_value.verify_connectivity.side_effect = Exception("neo4j down")
        mock_qdrant.return_value.get_collections.side_effect = Exception("qdrant down")
        mock_minio.return_value.list_buckets.side_effect = Exception("minio down")
        mock_httpx.get.side_effect = Exception("ollama down")

        response = client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    expected_checks = ["postgres", "redis", "neo4j", "qdrant", "minio", "ollama"]
    for check in expected_checks:
        assert check in data["checks"]
        assert data["checks"][check].startswith("error:")


def test_readiness_all_services_up(client: TestClient) -> None:
    """
    When every backing service is reachable, /ready should return 200 ready.
    """
    with (
        patch("parallax.api.main.asyncpg") as mock_asyncpg,
        patch("parallax.api.main.redis_lib") as mock_redis,
        patch("parallax.api.main.GraphDatabase") as mock_neo4j,
        patch("parallax.api.main.QdrantClient") as mock_qdrant,
        patch("parallax.api.main.Minio") as mock_minio,
        patch("parallax.api.main.httpx") as mock_httpx,
    ):
        # Make all checks succeed
        mock_conn = AsyncMock()
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
        mock_redis.Redis.return_value.ping.return_value = True
        mock_neo4j.driver.return_value.verify_connectivity.return_value = None
        mock_neo4j.driver.return_value.close.return_value = None
        mock_qdrant.return_value.get_collections.return_value = []
        mock_minio.return_value.list_buckets.return_value = []
        mock_httpx.get.return_value = MagicMock(status_code=200)
        mock_httpx.get.return_value.raise_for_status.return_value = None

        response = client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    for v in data["checks"].values():
        assert v == "ok"
