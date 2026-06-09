"""
Pytest configuration and shared fixtures for PARALLAX.
"""

import sys
from unittest.mock import MagicMock

# Monkey-patch passlib to prevent ValueError from bcrypt>=4.0.0 at import time
sys.modules["passlib"] = MagicMock()
sys.modules["passlib.utils"] = MagicMock()
sys.modules["passlib.utils.compat"] = MagicMock()
sys.modules["passlib.registry"] = MagicMock()
sys.modules["passlib.apache"] = MagicMock()

import pytest
from fastapi.testclient import TestClient

from parallax.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Returns a TestClient for the FastAPI app."""
    return TestClient(app)
