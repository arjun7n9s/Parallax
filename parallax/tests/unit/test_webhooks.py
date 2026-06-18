"""Tests for the webhook dispatcher: signing, retries, and per-submission delivery."""

import json
from unittest.mock import AsyncMock

import pytest

from parallax.core.config import settings
from parallax.delivery import webhook_dispatcher as wd


class TestBuildRequest:
    def test_signs_when_secret_set(self, monkeypatch):
        monkeypatch.setattr(settings, "WEBHOOK_SECRET", "topsecret")
        body, headers = wd._build_request("analysis.completed", {"verdict": "HIGH"})
        assert json.loads(body) == {"event": "analysis.completed", "data": {"verdict": "HIGH"}}
        assert headers["X-Parallax-Signature"].startswith("sha256=")

    def test_unsigned_when_no_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "WEBHOOK_SECRET", "")
        _, headers = wd._build_request("analysis.completed", {})
        assert "X-Parallax-Signature" not in headers


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.request = None


class TestPostWithRetries:
    @pytest.mark.asyncio
    async def test_success_posts_once(self):
        client = AsyncMock()
        client.post = AsyncMock(return_value=_Resp(200))
        ok = await wd._post_with_retries(client, "http://x", b"{}", {}, max_retries=4)
        assert ok is True
        assert client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_then_gives_up(self, monkeypatch):
        monkeypatch.setattr(wd.asyncio, "sleep", AsyncMock())  # no real backoff wait
        client = AsyncMock()
        client.post = AsyncMock(return_value=_Resp(500))
        ok = await wd._post_with_retries(client, "http://x", b"{}", {}, max_retries=3)
        assert ok is False
        assert client.post.await_count == 3


class TestDispatchToUrl:
    @pytest.mark.asyncio
    async def test_empty_url_is_noop(self):
        result = await wd.dispatch_to_url("", "analysis.completed", {})
        assert result == {"delivered": 0, "targets": 0}

    @pytest.mark.asyncio
    async def test_delivers_to_single_url(self, monkeypatch):
        posted = {}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, content=None, headers=None):
                posted["url"] = url
                posted["body"] = content
                return _Resp(200)

        monkeypatch.setattr(wd.httpx, "AsyncClient", lambda *a, **k: FakeClient())
        result = await wd.dispatch_to_url("http://hook.example/cb", "analysis.completed", {"v": 1})
        assert result == {"delivered": 1, "targets": 1}
        assert posted["url"] == "http://hook.example/cb"
        assert json.loads(posted["body"])["data"] == {"v": 1}
