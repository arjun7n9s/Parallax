"""
MinIO object storage integration.

Uses lazy initialization to avoid hard failures if MinIO is unreachable
at import time (e.g. during tests or partial infra bring-up).
"""

from functools import lru_cache

from minio import Minio

from parallax.core.config import settings

# Bucket names — single source of truth
APK_BUCKET = "parallax-apks"
DECOMPILED_BUCKET = "parallax-decompiled"
SCREENSHOTS_BUCKET = "parallax-screenshots"

_ALL_BUCKETS = [APK_BUCKET, DECOMPILED_BUCKET, SCREENSHOTS_BUCKET]


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
minio_client: Minio = property(lambda self: _get_client())  # type: ignore[assignment]


def get_minio_client() -> Minio:
    """Get the shared MinIO client instance."""
    return _get_client()


def init_buckets() -> None:
    """Ensure all required buckets exist. Should be called on application startup."""
    client = _get_client()
    for bucket in _ALL_BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
