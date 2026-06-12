"""Tests for VoiceCache."""

import pytest

from heart.ss08_voice.voice_cache import VoiceCache, should_cache


def test_should_cache_short_text():
    """Test short text should be cached."""
    assert should_cache("Hello") is True
    assert should_cache("Hi there") is True


def test_should_not_cache_long_text():
    """Test long text should not be cached."""
    long_text = "This is a very long sentence that exceeds the threshold"
    assert should_cache(long_text) is False


def test_cache_key_deterministic():
    """Test cache key is deterministic."""
    key1 = VoiceCache.cache_key("voice1", "happy", 1.0, 0, "Hello")
    key2 = VoiceCache.cache_key("voice1", "happy", 1.0, 0, "Hello")
    assert key1 == key2


def test_cache_key_different_params():
    """Test cache key differs for different params."""
    key1 = VoiceCache.cache_key("voice1", "happy", 1.0, 0, "Hello")
    key2 = VoiceCache.cache_key("voice1", "sad", 1.0, 0, "Hello")
    assert key1 != key2


@pytest.mark.asyncio
async def test_l1_cache_hit():
    """Test L1 cache hit."""
    cache = VoiceCache()
    key = "test_key"
    audio = b"audio_data"

    await cache.set(key, audio)
    result = await cache.get(key)
    assert result == audio


@pytest.mark.asyncio
async def test_l1_cache_miss():
    """Test L1 cache miss."""
    cache = VoiceCache()
    result = await cache.get("nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_l1_lru_eviction():
    """Test L1 LRU eviction."""
    cache = VoiceCache(mem_capacity=2)

    await cache.set("key1", b"audio1")
    await cache.set("key2", b"audio2")
    await cache.set("key3", b"audio3")  # Should evict key1

    assert await cache.get("key1") is None
    assert await cache.get("key2") == b"audio2"
    assert await cache.get("key3") == b"audio3"


@pytest.mark.asyncio
async def test_l1_lru_access_moves_to_end():
    """Test accessing item moves it to end (not evicted)."""
    cache = VoiceCache(mem_capacity=2)

    await cache.set("key1", b"audio1")
    await cache.set("key2", b"audio2")
    await cache.get("key1")  # Access key1, moves to end
    await cache.set("key3", b"audio3")  # Should evict key2

    assert await cache.get("key1") == b"audio1"
    assert await cache.get("key2") is None
    assert await cache.get("key3") == b"audio3"
