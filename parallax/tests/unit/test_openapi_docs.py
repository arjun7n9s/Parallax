"""Tests for Phase 3.2d OpenAPI publication and SDK tooling inputs."""

import json

from parallax.api.main import app
from scripts.export_openapi import export_openapi


def test_openapi_contains_batch_contract_examples():
    schema = app.openapi()
    batch_post = schema["paths"]["/api/v1/analyze/batch"]["post"]
    batch_get = schema["paths"]["/api/v1/analyze/batch/{batch_id}"]["get"]

    assert batch_post["summary"] == "Submit a batch of APKs"
    assert batch_get["summary"] == "Get batch analysis status"
    assert "BatchSubmissionResponse" in schema["components"]["schemas"]
    assert "BatchStatusResponse" in schema["components"]["schemas"]
    assert (
        schema["components"]["schemas"]["BatchSubmissionResponse"]["example"]["results"][0][
            "submission_id"
        ]
        == "6f1b8c6a-7c33-4b71-b1f9-1867c56f7f54"
    )


def test_openapi_export_writes_schema(tmp_path):
    out = tmp_path / "openapi.json"
    export_openapi(out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["info"]["title"] == "PARALLAX"
    assert "/api/v1/analyze" in data["paths"]
    assert "/api/v1/analyze/batch" in data["paths"]


def test_committed_openapi_schema_is_present():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "parallax" / "api" / "openapi.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")
    assert "/api/v1/analyze/batch" in data["paths"]
