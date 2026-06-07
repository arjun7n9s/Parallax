"""
Pytest configuration and shared fixtures for PARALLAX.
"""
import pytest
from fastapi.testclient import TestClient

from parallax.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Returns a TestClient for the FastAPI app."""
    return TestClient(app)
