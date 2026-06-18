"""
MinIO object storage integration.

Uses lazy initialization to avoid hard failures if MinIO is unreachable
at import time (e.g. during tests or partial infra bring-up).
"""

from datetime import timedelta
from functools import lru_cache
from typing import cast

from minio import Minio

from parallax.core.config import settings

# Bucket names — single source of truth
APK_BUCKET = "parallax-apks"
QUARANTINE_BUCKET = "parallax-quarantine"
DECOMPILED_BUCKET = "parallax-decompiled"
SCREENSHOTS_BUCKET = "parallax-screenshots"
REPORTS_BUCKET = "parallax-reports"

_ALL_BUCKETS = [
    APK_BUCKET,
    QUARANTINE_BUCKET,
    DECOMPILED_BUCKET,
    SCREENSHOTS_BUCKET,
    REPORTS_BUCKET,
]


@lru_cache(maxsize=1)
def _get_client() -> Minio:
    """Lazily create and cache the MinIO client."""
    return Minio(
        settings.MINIO_SERVER,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        secure=settings.MINIO_SECURE,
    )


# Public accessor — modules import this instead of instantiating Minio directly


def get_minio_client() -> Minio:
    """Get the shared MinIO client instance."""
    return _get_client()


def init_buckets() -> None:
    """Ensure all required buckets exist. Should be called on application startup."""
    client = _get_client()
    for bucket in _ALL_BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def signed_get_url(bucket: str, object_name: str) -> str:
    """Create a short-lived URL for an object without exposing storage secrets."""
    ttl = max(1, min(settings.SIGNED_URL_TTL_SECONDS, 7 * 24 * 60 * 60))
    return cast(
        str,
        get_minio_client().presigned_get_object(
            bucket,
            object_name,
            expires=timedelta(seconds=ttl),
        ),
    )
