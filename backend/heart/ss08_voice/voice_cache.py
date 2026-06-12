"""Voice Cache — LRU + Redis dual-layer cache for short TTS audio."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class VoiceCache:
    """Dual-layer cache for TTS audio: L1 in-memory LRU + L2 Redis.

    Only caches short text (< 30 chars) to avoid wasting cache space
    on long sentences that are unlikely to be repeated.
    """

    def __init__(self, redis_client: Optional[Any] = None, mem_capacity: int = 100):
        """Initialize voice cache.

        Args:
            redis_client: Optional Redis client for L2 cache.
            mem_capacity: Maximum number of items in L1 LRU cache.
        """
        self._redis = redis_client
        self._capacity = mem_capacity
        self._l1: OrderedDict[str, bytes] = OrderedDict()

    @staticmethod
    def cache_key(voice_id: str, emotion: str, speed: float, pitch: int, text: str) -> str:
        """Compute cache key from TTS request parameters."""
        raw = f"{voice_id}|{emotion}|{speed}|{pitch}|{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, key: str) -> Optional[bytes]:
        """Get audio bytes from cache.

        Returns None if not found.
        """
        # L1: in-memory LRU
        if key in self._l1:
            self._l1.move_to_end(key)
            logger.debug("voice_cache_l1_hit", key=key[:8])
            return self._l1[key]

        # L2: Redis
        if self._redis:
            try:
                data = await self._redis.get(f"tts:{key}")
                if data:
                    # Promote to L1
                    self._l1[key] = data
                    self._l1.move_to_end(key)
                    self._evict_l1()
                    logger.debug("voice_cache_l2_hit", key=key[:8])
                    return data
            except Exception as e:
                logger.warning("voice_cache_l2_get_failed", error=str(e))

        return None

    async def set(self, key: str, audio: bytes, ttl: int = 7 * 86400) -> None:
        """Store audio bytes in cache.

        Args:
            key: Cache key.
            audio: Audio bytes to cache.
            ttl: Time-to-live in seconds (default 7 days).
        """
        # L1: in-memory LRU
        self._l1[key] = audio
        self._l1.move_to_end(key)
        self._evict_l1()

        # L2: Redis
        if self._redis:
            try:
                await self._redis.setex(f"tts:{key}", ttl, audio)
                logger.debug("voice_cache_set", key=key[:8])
            except Exception as e:
                logger.warning("voice_cache_l2_set_failed", error=str(e))

    def _evict_l1(self) -> None:
        """Evict oldest items from L1 if over capacity."""
        while len(self._l1) > self._capacity:
            self._l1.popitem(last=False)


def should_cache(text: str) -> bool:
    """Check if text should be cached (short text only)."""
    return len(text) < 30
