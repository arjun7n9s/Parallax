"""
MinIO object storage integration.
"""

from minio import Minio

from parallax.core.config import settings

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_SERVER,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_SECURE,
)

# Bucket name for storing raw APKs
APK_BUCKET = "parallax-apks"


def init_buckets() -> None:
    """Ensure required buckets exist. Should be called on application startup."""
    if not minio_client.bucket_exists(APK_BUCKET):
        minio_client.make_bucket(APK_BUCKET)
