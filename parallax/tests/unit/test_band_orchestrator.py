"""Tests for Band SDK remote-agent orchestration."""

from __future__ import annotations

import builtins

import pytest

from parallax.agents.band.agents import agent_by_role
from parallax.agents.band.band_orchestrator import (
    BandSDKUnavailable,
    RemoteAgentSpec,
    create_band_agent,
    missing_credentials,
    remote_agent_specs,
)
from parallax.core.config import settings


def test_remote_agent_specs_cover_roster():
    specs = remote_agent_specs()

    assert len(specs) == 8
    assert {spec.descriptor.role for spec in specs} == {
        "intake",
        "device_compromise",
        "transaction_trace",
        "mule_graph",
        "evidence_validator",
        "liability",
        "legal_evidence",
        "decision_convenor",
    }
    assert all(spec.system_prompt for spec in specs)


def test_missing_credentials_reports_roles(monkeypatch):
    monkeypatch.setattr(settings, "BAND_AGENT_INTAKE_ID", "")
    monkeypatch.setattr(settings, "BAND_AGENT_INTAKE_API_KEY", "")

    missing = missing_credentials(remote_agent_specs(["intake"]))

    assert missing == ["intake"]


def test_llm_routes_through_aiml_gateway_when_key_set(monkeypatch):
    from parallax.agents.band.band_orchestrator import _llm_kwargs

    monkeypatch.setattr(settings, "AIML_API", "aiml-key")
    monkeypatch.setattr(settings, "AIML_BASE_URL", "https://api.aimlapi.com/v1")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    kwargs = _llm_kwargs("intake")
    assert kwargs["base_url"] == "https://api.aimlapi.com/v1"
    assert kwargs["api_key"] == "aiml-key"
    assert kwargs["model"] == "gpt-4o-mini"  # economy role


def test_llm_uses_premium_model_for_reasoning_roles(monkeypatch):
    from parallax.agents.band.band_orchestrator import _llm_kwargs

    monkeypatch.setattr(settings, "AIML_API", "aiml-key")
    for role in ("device_compromise", "evidence_validator", "decision_convenor"):
        assert _llm_kwargs(role)["model"] == "anthropic/claude-sonnet-4.6"


def test_llm_falls_back_to_openai_key(monkeypatch):
    from parallax.agents.band.band_orchestrator import _llm_kwargs

    monkeypatch.setattr(settings, "AIML_API", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-openai")
    kwargs = _llm_kwargs("intake")
    assert kwargs["api_key"] == "sk-openai"
    assert "base_url" not in kwargs  # direct OpenAI


def test_llm_raises_when_no_provider_configured(monkeypatch):
    from parallax.agents.band.band_orchestrator import _llm_kwargs

    monkeypatch.setattr(settings, "AIML_API", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(ValueError, match="No LLM provider configured"):
        _llm_kwargs("intake")


def test_create_band_agent_imports_sdk_lazily(monkeypatch):
    descriptor = agent_by_role("intake")
    spec = RemoteAgentSpec(descriptor, "system")
    monkeypatch.setattr(settings, descriptor.env_id_key, "agent-id")
    monkeypatch.setattr(settings, descriptor.env_api_key, "agent-key")
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "band":
            raise ImportError("band unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(BandSDKUnavailable):
        create_band_agent(spec)
