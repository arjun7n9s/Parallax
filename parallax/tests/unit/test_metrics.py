"""Tests for the Prometheus metrics core and the /metrics endpoint.

These assert the recording helpers move the right series in the default
registry and that the endpoint serves the exposition format. They never touch
backing services.
"""

import pytest

prometheus_client = pytest.importorskip("prometheus_client")
from prometheus_client import REGISTRY  # noqa: E402

from parallax.core import metrics  # noqa: E402
from parallax.core.errors import InfraError  # noqa: E402


class TestRecordHelpers:
    def test_record_stage_failure_increments_by_error_class(self):
        before = (
            REGISTRY.get_sample_value(
                "parallax_stage_failure_total",
                {"stage": "dynamic", "error_class": "InfraError"},
            )
            or 0.0
        )
        metrics.record_stage_failure("dynamic", InfraError("emulator down"))
        after = REGISTRY.get_sample_value(
            "parallax_stage_failure_total",
            {"stage": "dynamic", "error_class": "InfraError"},
        )
        assert after == before + 1.0

    def test_record_verdict_increments(self):
        before = (
            REGISTRY.get_sample_value("parallax_analysis_verdict_total", {"verdict": "HIGH"}) or 0.0
        )
        metrics.record_verdict("HIGH")
        after = REGISTRY.get_sample_value("parallax_analysis_verdict_total", {"verdict": "HIGH"})
        assert after == before + 1.0

    def test_record_llm_call_observes_duration_and_tokens(self):
        tokens_before = (
            REGISTRY.get_sample_value(
                "parallax_llm_tokens_total", {"role": "premium", "direction": "input"}
            )
            or 0.0
        )
        count_before = (
            REGISTRY.get_sample_value(
                "parallax_llm_call_duration_seconds_count",
                {"role": "premium", "provider": "aiml"},
            )
            or 0.0
        )
        metrics.record_llm_call("premium", "aiml", 1.5, tokens_in=100, tokens_out=20)
        tokens_after = REGISTRY.get_sample_value(
            "parallax_llm_tokens_total", {"role": "premium", "direction": "input"}
        )
        count_after = REGISTRY.get_sample_value(
            "parallax_llm_call_duration_seconds_count",
            {"role": "premium", "provider": "aiml"},
        )
        assert tokens_after == tokens_before + 100
        assert count_after == count_before + 1.0

    def test_helpers_never_raise(self):
        # Defensive: bad inputs degrade silently, never break a pipeline stage.
        metrics.record_stage_failure("x", RuntimeError("boom"))
        metrics.record_verdict("CLEAN")
        metrics.record_llm_call("economy", "ollama", 0.0)

    def test_metrics_text_is_exposition_format(self):
        metrics.record_verdict("CRITICAL")
        body, content_type = metrics.metrics_text()
        assert b"parallax_analysis_verdict_total" in body
        assert "text/plain" in content_type


class TestMetricsEndpoint:
    def test_endpoint_serves_metrics(self, monkeypatch):
        from fastapi.testclient import TestClient

        # Import the app lazily; force auth off so unrelated routes don't matter.
        from parallax.api import main as api_main

        client = TestClient(api_main.app)
        metrics.record_verdict("MEDIUM")
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "parallax_analysis_verdict_total" in resp.text
