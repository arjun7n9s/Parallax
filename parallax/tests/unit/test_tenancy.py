"""Tests for Phase 3.3 tenant context and query scoping."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from parallax.api.main import app
from parallax.core.config import settings
from parallax.core.database import get_session


def _enable_tenant_auth(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "fallback")
    monkeypatch.setattr(settings, "TENANT_ID", "default")
    monkeypatch.setattr(settings, "API_KEY_TENANT_MAP", "bank-a-key:bank-a,bank-b-key:bank-b")


def test_status_query_is_tenant_scoped(client: TestClient, monkeypatch):
    _enable_tenant_auth(monkeypatch)

    mock_session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=result)
    app.dependency_overrides[get_session] = lambda: mock_session

    resp = client.get(
        "/api/v1/analysis/6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54",
        headers={"X-API-Key": "bank-a-key"},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    stmt = mock_session.execute.call_args.args[0]
    assert "tenant_id" in str(stmt)


def test_history_query_is_tenant_scoped(client: TestClient, monkeypatch):
    _enable_tenant_auth(monkeypatch)

    mock_session = MagicMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(side_effect=[count_result, items_result])
    app.dependency_overrides[get_session] = lambda: mock_session

    resp = client.get("/api/v1/history", headers={"X-API-Key": "bank-b-key"})
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    first_stmt = mock_session.execute.call_args_list[0].args[0]
    assert "tenant_id" in str(first_stmt)


def test_wrong_tenant_key_is_rejected(client: TestClient, monkeypatch):
    _enable_tenant_auth(monkeypatch)
    resp = client.get(
        "/api/v1/history",
        headers={"X-API-Key": "unknown-key"},
    )
    assert resp.status_code == 401


def test_quarantine_url_is_tenant_scoped_and_audited(client: TestClient, monkeypatch):
    _enable_tenant_auth(monkeypatch)
    monkeypatch.setattr("parallax.api.routes.results.signed_get_url", lambda *_: "https://signed")

    sub = MagicMock()
    sub.id = uuid.UUID("6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54")
    sub.sha256 = "a" * 64
    sub.created_at = datetime.now(timezone.utc)
    sub.updated_at = datetime.now(timezone.utc)

    result = MagicMock()
    result.scalar_one_or_none.return_value = sub
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=result)
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    resp = client.get(
        f"/api/v1/analysis/{sub.id}/quarantine-url",
        headers={"X-API-Key": "bank-a-key"},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["url"] == "https://signed"
    stmt = mock_session.execute.call_args.args[0]
    assert "tenant_id" in str(stmt)
    audit_entry = mock_session.add.call_args.args[0]
    assert audit_entry.tenant_id == "bank-a"
    assert audit_entry.action == "artifact.signed_url_issued"
