"""
Unit tests for basic API endpoints.
"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the /health liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PARALLAX"


def test_readiness_check_fails_without_backing_services(client: TestClient) -> None:
    """
    Test the /ready probe.
    If backing services aren't running during tests, it should return 503 degraded.
    """
    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "checks" in data
    # Verify all checks ran, even if they failed
    expected_checks = ["postgres", "redis", "neo4j", "qdrant", "minio", "ollama"]
    for check in expected_checks:
        assert check in data["checks"]
