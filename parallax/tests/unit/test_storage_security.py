"""Tests for object-storage security helpers."""

from unittest.mock import MagicMock


def test_signed_get_url_uses_configured_ttl(monkeypatch):
    from parallax.core import storage
    from parallax.core.config import settings

    client = MagicMock()
    client.presigned_get_object.return_value = "https://signed"
    monkeypatch.setattr(storage, "get_minio_client", lambda: client)
    monkeypatch.setattr(settings, "SIGNED_URL_TTL_SECONDS", 123)

    assert storage.signed_get_url("bucket", "obj.apk") == "https://signed"
    kwargs = client.presigned_get_object.call_args.kwargs
    assert int(kwargs["expires"].total_seconds()) == 123


def test_signed_get_url_clamps_to_minio_max_ttl(monkeypatch):
    from parallax.core import storage
    from parallax.core.config import settings

    client = MagicMock()
    client.presigned_get_object.return_value = "https://signed"
    monkeypatch.setattr(storage, "get_minio_client", lambda: client)
    monkeypatch.setattr(settings, "SIGNED_URL_TTL_SECONDS", 999999999)

    storage.signed_get_url("bucket", "obj.apk")
    kwargs = client.presigned_get_object.call_args.kwargs
    assert int(kwargs["expires"].total_seconds()) == 7 * 24 * 60 * 60
