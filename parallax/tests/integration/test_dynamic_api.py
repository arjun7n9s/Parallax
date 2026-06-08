import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from parallax.api.main import app
from parallax.api.routes.dynamic import get_generator


@pytest.fixture
def mock_generator():
    generator = AsyncMock()
    # Mock generate_hook returns (script, is_unresolved, reason)
    generator.generate_hook.return_value = (
        "<<<HOOK_START>>>\nJava.perform(function() {});\n<<<HOOK_END>>>",
        False,
        None
    )
    generator.parser.api_dictionary = {"mock_api": {}}
    return generator


@pytest.fixture
def override_generator(mock_generator):
    app.dependency_overrides[get_generator] = lambda: mock_generator
    yield mock_generator
    app.dependency_overrides.pop(get_generator, None)


@pytest.mark.asyncio
async def test_dynamic_analyze_endpoint_success(override_generator):
    payload = {
        "submission_id": "sub-123",
        "hypothesis_id": "hyp-456",
        "hypothesis_claim": "The app reads contacts.",
        "package_name": "com.example.malware",
        "permissions": ["android.permission.READ_CONTACTS"]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/dynamic/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["submission_id"] == "sub-123"
    assert data["hypothesis_id"] == "hyp-456"
    assert data["is_unresolved"] is False
    assert "Java.perform" in data["script"]

    # Verify the mock generator was called correctly
    override_generator.generate_hook.assert_called_once_with(
        hypothesis_id="hyp-456",
        hypothesis_claim="The app reads contacts.",
        package_name="com.example.malware",
        permissions=["android.permission.READ_CONTACTS"],
        api_dictionary={"mock_api": {}}
    )


@pytest.mark.asyncio
async def test_dynamic_analyze_endpoint_unresolved(override_generator):
    override_generator.generate_hook.return_value = ("", True, "Native code not supported")

    payload = {
        "submission_id": "sub-123",
        "hypothesis_id": "hyp-456",
        "hypothesis_claim": "The app reads contacts via JNI.",
        "package_name": "com.example.malware",
        "permissions": []
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/dynamic/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_unresolved"] is True
    assert data["script"] == ""
    assert data["unresolved_reason"] == "Native code not supported"


@pytest.mark.asyncio
async def test_dynamic_analyze_endpoint_internal_error(override_generator):
    override_generator.generate_hook.side_effect = Exception("Ollama is down")

    payload = {
        "submission_id": "sub-123",
        "hypothesis_id": "hyp-456",
        "hypothesis_claim": "Test claim",
        "package_name": "com.example.malware",
        "permissions": []
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/dynamic/analyze", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to generate dynamic hook."
