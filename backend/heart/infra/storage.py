"""S3-compatible object storage client (MinIO / AWS S3)."""

from __future__ import annotations

import asyncio
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
    """Create bucket if it doesn't exist, then set lifecycle rules."""
    global _bucket_checked
    if _bucket_checked:
        return
    from heart.core.config import settings

    client = _get_s3_client()

    def _check_or_create() -> None:
        try:
            client.head_bucket(Bucket=settings.s3_bucket_name)
        except Exception:
            client.create_bucket(Bucket=settings.s3_bucket_name)
            logger.info("s3_bucket_created", bucket=settings.s3_bucket_name)

    await asyncio.to_thread(_check_or_create)
    await _ensure_voice_lifecycle()
    _bucket_checked = True


# Prefixes whose objects expire after AUDIO_EXPIRY_DAYS days.
# voice_messages/ — user ASR recordings
# chat_audio/     — character TTS output
_AUDIO_EXPIRY_PREFIXES: dict[str, str] = {
    "expire-voice-messages": "voice_messages/",
    "expire-chat-audio": "chat_audio/",
}
AUDIO_EXPIRY_DAYS = 20


async def _ensure_voice_lifecycle() -> None:
    """Idempotently set 20-day expiry rules for all audio prefixes.

    Uses get → merge → put so unrelated bucket rules are preserved.
    Works with AWS S3, Cloudflare R2, and local Docker MinIO (latest).
    Failure is non-fatal — logs a warning and lets startup continue.
    """
    from heart.core.config import settings

    client = _get_s3_client()
    bucket = settings.s3_bucket_name

    def _apply() -> None:
        try:
            existing = client.get_bucket_lifecycle_configuration(Bucket=bucket)
            rules: list = [
                r for r in existing.get("Rules", []) if r.get("ID") not in _AUDIO_EXPIRY_PREFIXES
            ]
        except Exception:
            # No lifecycle config yet (S3/R2 raise NoSuchLifecycleConfiguration,
            # MinIO raises a generic ClientError, and some botocore builds don't
            # even define client.exceptions.NoSuchLifecycleConfiguration — so
            # referencing it in an `except` clause here would itself raise
            # AttributeError and abort the whole upload). Treat any read failure
            # as "no existing rules" and continue.
            rules = []

        for rule_id, prefix in _AUDIO_EXPIRY_PREFIXES.items():
            rules.append(
                {
                    "ID": rule_id,
                    "Status": "Enabled",
                    "Filter": {"Prefix": prefix},
                    "Expiration": {"Days": AUDIO_EXPIRY_DAYS},
                }
            )
        try:
            client.put_bucket_lifecycle_configuration(
                Bucket=bucket,
                LifecycleConfiguration={"Rules": rules},
            )
            logger.info(
                "s3_audio_lifecycle_set",
                prefixes=list(_AUDIO_EXPIRY_PREFIXES.values()),
                expiry_days=AUDIO_EXPIRY_DAYS,
            )
        except Exception as exc:
            logger.warning("s3_audio_lifecycle_failed", error=str(exc))

    await asyncio.to_thread(_apply)


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

    await asyncio.to_thread(
        client.put_object,
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    # Use public base URL when configured (e.g. R2 r2.dev subdomain) so that
    # third-party services (MiniMax voice clone) can fetch the object without auth.
    if settings.s3_public_base_url:
        base = settings.s3_public_base_url.rstrip("/")
        url = f"{base}/{key}"
    else:
        endpoint = settings.s3_endpoint_url.rstrip("/")
        url = f"{endpoint}/{settings.s3_bucket_name}/{key}"
    logger.info("file_uploaded", key=key, size=len(data))
    return url


async def upload_avatar(user_id: str, data: bytes, content_type: str) -> str:
    """Upload avatar image and return proxied URL.

    Generates key: avatars/{user_id}/{uuid}.{ext}
    Returns: /api/profile/avatar-file/{user_id}/{filename}
    """
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = ext_map.get(content_type, "jpg")
    filename = f"{uuid.uuid4().hex}.{ext}"
    key = f"avatars/{user_id}/{filename}"
    await _upload_to_s3(key, data, content_type)
    return f"/api/profile/avatar-file/{user_id}/{filename}"


async def _upload_to_s3(key: str, data: bytes, content_type: str) -> None:
    """Upload raw bytes to S3/MinIO (non-blocking via asyncio.to_thread)."""
    client = _get_s3_client()
    await ensure_bucket()
    from heart.core.config import settings

    await asyncio.to_thread(
        client.put_object,
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("file_uploaded", key=key, size=len(data))


async def upload_voice_message(user_id: str, data: bytes, mime: str = "audio/wav") -> str:
    """Upload a user voice recording and return its URL.

    Objects land under voice_messages/<user_id>/<uuid>.<ext> and should be
    covered by an S3/R2 lifecycle rule that auto-deletes this prefix after 20 days.
    """
    ext = "mp3" if mime in ("audio/mpeg", "audio/mp3") else "wav"
    key = f"voice_messages/{user_id}/{uuid.uuid4().hex}.{ext}"
    return await upload_file(data, key, mime)


async def get_s3_object(key: str) -> tuple[bytes, str]:
    """Fetch object from S3/MinIO. Returns (data, content_type)."""
    client = _get_s3_client()
    from heart.core.config import settings

    def _get() -> tuple[bytes, str]:
        resp = client.get_object(Bucket=settings.s3_bucket_name, Key=key)
        return resp["Body"].read(), resp.get("ContentType", "application/octet-stream")

    return await asyncio.to_thread(_get)


def is_s3_configured() -> bool:
    """Check if S3/MinIO is configured (not just defaults)."""
    from heart.core.config import settings

    return bool(settings.s3_endpoint_url and settings.s3_access_key_id)


_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def _host_is_private(host: str) -> bool:
    """True if ``host`` is a loopback / RFC1918 / mDNS name.

    Split from ``is_s3_endpoint_public`` to keep that function under ruff's
    complexity ceiling — the range check for 172.16.0.0/12 dominates the
    branch count, so isolating it here reads more clearly too.
    """
    if not host:
        return True
    if host in _LOOPBACK_HOSTS:
        return True
    if host.startswith(("10.", "192.168.")):
        return True
    if host.endswith(".local"):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
            except ValueError:
                return False
            return 16 <= second <= 31
    return False


def is_s3_endpoint_public() -> bool:
    """Whether the configured S3 endpoint is reachable from third-party servers.

    Voice-clone hands the resulting URL to MiniMax, whose servers must be
    able to fetch it. A localhost / private-IP endpoint (typical dev MinIO)
    silently breaks that: the S3 upload itself succeeds, but MiniMax then
    fails to download the audio and returns a fast 4xx — surfacing to the
    user as "克隆失败" a few seconds after upload with no useful reason.

    Callers should use this to decide between the S3 path and the MiniMax
    ``/files/upload`` fallback.
    """
    from urllib.parse import urlparse

    from heart.core.config import settings

    if not is_s3_configured():
        return False
    endpoint = (settings.s3_endpoint_url or "").strip()
    if not endpoint:
        return False
    try:
        host = (urlparse(endpoint).hostname or "").lower()
    except Exception:
        return False
    return not _host_is_private(host)
