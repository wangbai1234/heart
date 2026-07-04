"""S3-compatible object storage client (MinIO / AWS S3)."""

from __future__ import annotations

import uuid
from io import BytesIO

import structlog

logger = structlog.get_logger(__name__)

_client = None
_bucket_checked = False


def _get_s3_client():
    """Lazy-create boto3 S3 client."""
    global _client
    if _client is None:
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            ) from None
        from heart.core.config import settings

        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )
    return _client


async def ensure_bucket() -> None:
    """Create bucket if it doesn't exist."""
    global _bucket_checked
    if _bucket_checked:
        return
    from heart.core.config import settings

    client = _get_s3_client()
    try:
        from botocore.exceptions import ClientError

        client.head_bucket(Bucket=settings.s3_bucket_name)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket_name)
        logger.info("s3_bucket_created", bucket=settings.s3_bucket_name)
    _bucket_checked = True


async def upload_file(
    data: bytes,
    key: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload file to S3/MinIO and return the URL.

    Args:
        data: File content bytes
        key: Object key (e.g. "avatars/{user_id}/{uuid}.webp")
        content_type: MIME type

    Returns:
        URL to the uploaded object
    """
    from heart.core.config import settings

    client = _get_s3_client()
    await ensure_bucket()

    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    # Construct URL
    endpoint = settings.s3_endpoint_url.rstrip("/")
    url = f"{endpoint}/{settings.s3_bucket_name}/{key}"
    logger.info("file_uploaded", key=key, size=len(data))
    return url


async def upload_avatar(user_id: str, data: bytes, content_type: str) -> str:
    """Upload avatar image and return URL.

    Generates key: avatars/{user_id}/{uuid}.{ext}
    """
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = ext_map.get(content_type, "jpg")
    key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
    return await upload_file(data, key, content_type)


def is_s3_configured() -> bool:
    """Check if S3/MinIO is configured (not just defaults)."""
    from heart.core.config import settings

    return bool(settings.s3_endpoint_url and settings.s3_access_key_id)
