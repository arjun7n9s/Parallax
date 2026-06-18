"""Tests for Phase 3.3 security controls: data-residency lock, admin-key
separation, secret redaction, and per-key rate limiting."""

import pytest

from parallax.core.config import settings


class TestLocalOnly:
    def test_local_only_forces_ollama_even_with_cloud_key(self, monkeypatch):
        from parallax.ai.llm import llm

        monkeypatch.setattr(settings, "LLM_MODE", "auto")
        monkeypatch.setattr(settings, "CLOUD_PROVIDER", "aiml")
        monkeypatch.setattr(settings, "AIML_API", "a-real-key")
        monkeypatch.setattr(settings, "LOCAL_ONLY", True)
        # synthesis is cloud-capable; LOCAL_ONLY must still pin it local.
        assert llm.provider_for("synthesis") == "ollama"

    def test_cloud_routes_when_not_local_only(self, monkeypatch):
        from parallax.ai.llm import llm

        monkeypatch.setattr(settings, "LLM_MODE", "auto")
        monkeypatch.setattr(settings, "CLOUD_PROVIDER", "aiml")
        monkeypatch.setattr(settings, "AIML_API", "a-real-key")
        monkeypatch.setattr(settings, "LOCAL_ONLY", False)
        assert llm.provider_for("synthesis") == "aiml"


class TestAdminKey:
    @pytest.mark.asyncio
    async def test_open_dev_mode_allows(self, monkeypatch):
        from parallax.api.security import require_admin_key

        monkeypatch.setattr(settings, "API_KEY", "")
        monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
        assert await require_admin_key(None) is None

    @pytest.mark.asyncio
    async def test_fails_closed_when_api_key_set_but_admin_unset(self, monkeypatch):
        from fastapi import HTTPException

        from parallax.api.security import require_admin_key

        monkeypatch.setattr(settings, "API_KEY", "analyst")
        monkeypatch.setattr(settings, "ADMIN_API_KEY", "")
        with pytest.raises(HTTPException) as exc:
            await require_admin_key("analyst")  # analyst key must not escalate
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_accepts_correct_admin_key(self, monkeypatch):
        from parallax.api.security import require_admin_key

        monkeypatch.setattr(settings, "ADMIN_API_KEY", "s3cret-admin")
        assert await require_admin_key("s3cret-admin") is None

    @pytest.mark.asyncio
    async def test_rejects_wrong_admin_key(self, monkeypatch):
        from fastapi import HTTPException

        from parallax.api.security import require_admin_key

        monkeypatch.setattr(settings, "ADMIN_API_KEY", "s3cret-admin")
        with pytest.raises(HTTPException):
            await require_admin_key("wrong")


class TestRedactSecrets:
    def test_scrubs_configured_secret_values(self, monkeypatch):
        from parallax.api.security import redact_secrets

        monkeypatch.setattr(settings, "AIML_API", "sk-supersecret-123456")
        text = "gateway call failed with key sk-supersecret-123456 in url"
        out = redact_secrets(text)
        assert "sk-supersecret-123456" not in out
        assert "***REDACTED***" in out

    def test_ignores_short_or_empty_secrets(self, monkeypatch):
        from parallax.api.security import redact_secrets

        monkeypatch.setattr(settings, "API_KEY", "")
        monkeypatch.setattr(settings, "AIML_API", "abc")  # too short to redact
        assert redact_secrets("nothing abc here") == "nothing abc here"


class TestRateLimit:
    def test_allows_up_to_limit_then_blocks(self):
        from parallax.api.rate_limit import check_and_increment

        class FakeRedis:
            def __init__(self):
                self.store: dict[str, int] = {}

            def incr(self, k):
                self.store[k] = self.store.get(k, 0) + 1
                return self.store[k]

            def expire(self, k, ttl):
                pass

        client = FakeRedis()
        now = 1_700_000_000.0
        results = [check_and_increment(client, "key:abc", 3, now) for _ in range(4)]
        assert [allowed for allowed, _ in results] == [True, True, True, False]
        assert results[-1][1] == 4

    def test_window_rolls_over_each_hour(self):
        from parallax.api.rate_limit import check_and_increment

        class FakeRedis:
            def __init__(self):
                self.store: dict[str, int] = {}

            def incr(self, k):
                self.store[k] = self.store.get(k, 0) + 1
                return self.store[k]

            def expire(self, k, ttl):
                pass

        client = FakeRedis()
        a, _ = check_and_increment(client, "key:abc", 1, 1_700_000_000.0)
        # Next hour -> different window key -> fresh budget.
        b, _ = check_and_increment(client, "key:abc", 1, 1_700_000_000.0 + 3600)
        assert a is True and b is True
