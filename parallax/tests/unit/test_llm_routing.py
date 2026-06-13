"""Unit tests for LLM provider routing — the aimlapi gateway tier strategy.

These tests pin the cost-efficiency contract: economy models for
high-frequency structured roles, exactly two premium roles, embeddings
always local, and graceful local fallback when no cloud key is present.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from parallax.ai.llm import _ECONOMY, _PREMIUM, ROSTER, LLMProvider, _extract_json
from parallax.core.config import settings


@pytest.fixture
def provider():
    return LLMProvider()


@pytest.fixture
def aiml_cloud(monkeypatch):
    """Configure settings for gateway routing."""
    monkeypatch.setattr(settings, "LLM_MODE", "auto")
    monkeypatch.setattr(settings, "CLOUD_PROVIDER", "aiml")
    monkeypatch.setattr(settings, "AIML_API", "test-key")


# ----------------------------------------------------------------- roster shape
class TestRoster:
    def test_cloud_capable_derived_from_cloud_model(self):
        assert ROSTER["synthesis"].cloud_capable is True
        assert ROSTER["embedding"].cloud_capable is False

    def test_embedding_never_cloud(self):
        assert ROSTER["embedding"].cloud_model == ""

    def test_exactly_two_premium_role_groups(self):
        # code_interpreter/re_workbench (same crown jewel) + synthesis.
        premium = {role for role, spec in ROSTER.items() if spec.cloud_model == _PREMIUM}
        assert premium == {"re_workbench", "code_interpreter", "synthesis"}

    def test_no_opus_class_models_anywhere(self):
        for role, spec in ROSTER.items():
            assert "opus" not in spec.cloud_model.lower(), f"{role} uses an Opus-class model"

    def test_high_frequency_roles_are_economy(self):
        for role in ("triage", "hypothesis", "hook_planner", "intel_correlator", "debate"):
            assert ROSTER[role].cloud_model == _ECONOMY

    def test_vision_roles_have_vision_capable_assignment(self):
        for role in ("visual", "dynamic_explorer"):
            assert ROSTER[role].supports_vision is True
            # Vision volume is high → must not be on the premium tier.
            assert ROSTER[role].cloud_model != _PREMIUM


# ----------------------------------------------------------------- routing
class TestRouting:
    def test_aiml_selected_when_key_present(self, provider, aiml_cloud):
        assert provider.provider_for("synthesis") == "aiml"
        assert provider.provider_for("triage") == "aiml"

    def test_embedding_stays_local_in_cloud_mode(self, provider, aiml_cloud):
        assert provider.provider_for("embedding") == "ollama"

    def test_local_fallback_when_key_missing(self, provider, monkeypatch):
        monkeypatch.setattr(settings, "LLM_MODE", "auto")
        monkeypatch.setattr(settings, "CLOUD_PROVIDER", "aiml")
        monkeypatch.setattr(settings, "AIML_API", "")
        assert provider.provider_for("synthesis") == "ollama"

    def test_local_mode_ignores_key(self, provider, monkeypatch):
        monkeypatch.setattr(settings, "LLM_MODE", "local")
        monkeypatch.setattr(settings, "AIML_API", "test-key")
        assert provider.provider_for("synthesis") == "ollama"

    def test_native_anthropic_still_routable(self, provider, monkeypatch):
        monkeypatch.setattr(settings, "LLM_MODE", "cloud")
        monkeypatch.setattr(settings, "CLOUD_PROVIDER", "anthropic")
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
        assert provider.provider_for("synthesis") == "anthropic"

    def test_unknown_role_uses_default_spec(self, provider, aiml_cloud):
        assert provider.provider_for("never-heard-of-it") == "aiml"


# ----------------------------------------------------------------- gateway call
class TestAimlGenerate:
    @pytest.mark.asyncio
    async def test_call_shape(self, provider, aiml_cloud):
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
            )

        provider._aiml = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)),
            close=AsyncMock(),
        )

        result = await provider.complete_json("synthesis", "verdict?", system="be precise")

        assert result == {"ok": True}
        assert captured["model"] == _PREMIUM
        assert captured["max_tokens"] == 8192
        # response_format must NOT be sent — unsupported on many gateway models.
        assert "response_format" not in captured
        # JSON enforced by instruction instead.
        user_msg = captured["messages"][-1]
        assert "single valid JSON object" in user_msg["content"][0]["text"]
        assert captured["messages"][0] == {"role": "system", "content": "be precise"}

    @pytest.mark.asyncio
    async def test_images_passed_as_data_uris(self, provider, aiml_cloud):
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="a phishing screen"))]
            )

        provider._aiml = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)),
            close=AsyncMock(),
        )

        out = await provider.complete_text("visual", "describe", images=["aGVsbG8="])

        assert out == "a phishing screen"
        content = captured["messages"][-1]["content"]
        image_parts = [c for c in content if c["type"] == "image_url"]
        assert image_parts == [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,aGVsbG8="}}
        ]


# ----------------------------------------------------------------- json parsing
class TestExtractJson:
    def test_plain(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_fenced(self):
        assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_prose_wrapped(self):
        assert _extract_json('Sure! Here it is: {"a": 1} Hope that helps.') == {"a": 1}
