"""
Tests for the analyze and status API endpoints.
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from parallax.api.main import app
from parallax.core.database import get_session


@patch("parallax.api.routes.analyze.get_minio_client")
def test_submit_apk_success(mock_get_minio, client: TestClient):
    """Test successful APK submission with valid APK magic bytes."""
    from datetime import datetime, timezone

    mock_minio = MagicMock()
    mock_get_minio.return_value = mock_minio

    # Mock database session with sync add and async commit/refresh
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()

    def mock_add(obj):
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_session.add.side_effect = mock_add

    # Mock that the file does not already exist
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Create a fake APK file — must start with PK magic bytes
    fake_apk_content = b"PK\x03\x04 fake apk content for testing"
    files = {
        "file": (
            "test_malware.apk",
            BytesIO(fake_apk_content),
            "application/vnd.android.package-archive",
        )
    }

    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.post("/api/v1/analyze", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "test_malware.apk"
    assert data["status"] == "queued"
    assert "sha256" in data
    assert "md5" in data
    assert "id" in data

    # Verify minio was called
    mock_minio.fput_object.assert_called_once()

    app.dependency_overrides.clear()


def test_submit_non_apk(client: TestClient):
    """Test submitting a file that is not an APK."""
    fake_txt_content = b"just some text"
    files = {"file": ("test.txt", BytesIO(fake_txt_content), "text/plain")}

    response = client.post("/api/v1/analyze", files=files)
    assert response.status_code == 400
    assert "Only .apk files are supported" in response.json()["detail"]


def test_submit_apk_invalid_magic_bytes(client: TestClient):
    """Test submitting a .apk file that has wrong magic bytes."""
    fake_content = b"\x00\x00\x00\x00 this is not really an APK"
    files = {
        "file": (
            "fake.apk",
            BytesIO(fake_content),
            "application/vnd.android.package-archive",
        )
    }

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()

    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.post("/api/v1/analyze", files=files)
    assert response.status_code == 400
    assert "invalid magic bytes" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_get_status_not_found(client: TestClient):
    """Test getting status for a non-existent UUID."""
    mock_session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_session] = lambda: mock_session

    response = client.get("/api/v1/analysis/12345678-1234-5678-1234-567812345678")
    assert response.status_code == 404

    app.dependency_overrides.clear()
