"""
Tests for the analyze and status API endpoints.
"""
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from parallax.api.main import app
from parallax.core.database import get_session


@pytest.fixture
def client():
    return TestClient(app)


@patch("parallax.api.routes.analyze.minio_client")
def test_submit_apk_success(mock_minio, client):
    """Test successful APK submission."""
    from datetime import datetime, timezone
    
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

    # Create a fake APK file
    fake_apk_content = b"PK\x03\x04 fake apk content for testing"
    files = {
        "file": ("test_malware.apk", BytesIO(fake_apk_content), "application/vnd.android.package-archive")
    }

    # Since we use dependency override in FastAPI for DB:
    app.dependency_overrides[get_session] = lambda: mock_session
    
    response = client.post("/api/v1/analyze", files=files)
    
    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "test_malware.apk"
    assert data["status"] == "queued"
    assert "sha256" in data
    assert "md5" in data
    assert "id" in data
    
    # Verify minio was called
    mock_minio.fput_object.assert_called_once()
    
    # Clean up override
    app.dependency_overrides.clear()


def test_submit_non_apk(client):
    """Test submitting a file that is not an APK."""
    fake_txt_content = b"just some text"
    files = {
        "file": ("test.txt", BytesIO(fake_txt_content), "text/plain")
    }
    
    response = client.post("/api/v1/analyze", files=files)
    assert response.status_code == 400
    assert "Only .apk files are supported" in response.json()["detail"]


def test_get_status_not_found(client):
    """Test getting status for a non-existent UUID."""
    mock_session = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_session] = lambda: mock_session
    
    response = client.get("/api/v1/analysis/12345678-1234-5678-1234-567812345678")
    assert response.status_code == 404
    
    app.dependency_overrides.clear()
