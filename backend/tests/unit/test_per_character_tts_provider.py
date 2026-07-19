"""Per-character TTS provider routing (issue 4 语音两档).

A character's ``character_voices.voice_provider`` must drive which TTS engine
synthesizes its speech: a Fish-cloned voice has to be rendered by Fish, not by
the process-default primary (MiMo). These tests cover the two new seams:

- ``voice_resolver.resolve_voice_provider`` — reads the per-character provider.
- ``VoiceService.synthesize_with_fallback(preferred_provider_name=...)`` — selects
  the named provider from the registry, falls back correctly, and keeps
  ``provider_name`` accurate for billing.
"""

from __future__ import annotations

import pytest

from heart.ss08_voice.service import VoiceService
from heart.ss08_voice.types import TTSRequest, TTSResult
from heart.ss08_voice.voice_resolver import resolve_voice_provider


# ── Fakes ──────────────────────────────────────────────────────────────────


class FakeTTSProvider:
    """Minimal TTSProvider: records calls, optionally fails."""

    def __init__(self, name: str, fail: bool = False):
        self._name = name
        self.fail = fail
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def synthesize(self, req: TTSRequest, character_id: str = "rin") -> TTSResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self._name} boom")
        return TTSResult(
            audio=b"audio", format="mp3", duration_ms=1, request_id="rid", provider_name=self._name
        )


class _FakeResult:
    def __init__(self, val):
        self._val = val

    def scalar_one_or_none(self):
        return self._val


class _FakeDB:
    def __init__(self, val):
        self._val = val

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._val)


def _req() -> TTSRequest:
    return TTSRequest(text="你好", voice_id="v1")


# ── resolve_voice_provider ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_voice_provider_returns_db_value():
    provider = await resolve_voice_provider("char-1", _FakeDB("fish"))
    assert provider == "fish"


@pytest.mark.asyncio
async def test_resolve_voice_provider_none_when_no_row():
    assert await resolve_voice_provider("char-1", _FakeDB(None)) is None


@pytest.mark.asyncio
async def test_resolve_voice_provider_empty_string_is_none():
    # A blank column must not be treated as a real provider name.
    assert await resolve_voice_provider("char-1", _FakeDB("")) is None


# ── VoiceService per-character provider selection ──────────────────────────


@pytest.mark.asyncio
async def test_synthesize_prefers_named_provider():
    mimo = FakeTTSProvider("mimo")
    fish = FakeTTSProvider("fish")
    svc = VoiceService(mimo, fallback=None, providers={"mimo": mimo, "fish": fish})

    result = await svc.synthesize_with_fallback(_req(), "char-1", preferred_provider_name="fish")

    assert result.provider_name == "fish"
    assert fish.calls == 1
    assert mimo.calls == 0


@pytest.mark.asyncio
async def test_synthesize_default_uses_primary_when_no_preference():
    mimo = FakeTTSProvider("mimo")
    fish = FakeTTSProvider("fish")
    svc = VoiceService(mimo, fallback=None, providers={"mimo": mimo, "fish": fish})

    result = await svc.synthesize_with_fallback(_req(), "char-1", preferred_provider_name=None)

    assert result.provider_name == "mimo"
    assert mimo.calls == 1
    assert fish.calls == 0


@pytest.mark.asyncio
async def test_synthesize_unknown_preferred_falls_back_to_primary():
    mimo = FakeTTSProvider("mimo")
    svc = VoiceService(mimo, fallback=None, providers={"mimo": mimo})

    result = await svc.synthesize_with_fallback(_req(), "char-1", preferred_provider_name="ghost")

    assert result.provider_name == "mimo"
    assert mimo.calls == 1


@pytest.mark.asyncio
async def test_synthesize_falls_back_when_preferred_provider_fails():
    # Fish is the preferred provider but errors → fall back to the global
    # fallback (minimax), and provider_name reflects who actually served it.
    mimo = FakeTTSProvider("mimo")
    fish = FakeTTSProvider("fish", fail=True)
    minimax = FakeTTSProvider("minimax")
    svc = VoiceService(
        mimo, fallback=minimax, providers={"mimo": mimo, "fish": fish, "minimax": minimax}
    )

    result = await svc.synthesize_with_fallback(_req(), "char-1", preferred_provider_name="fish")

    assert result.provider_name == "minimax"
    assert fish.calls == 1
    assert minimax.calls == 1


def test_registry_defaults_include_primary_and_fallback():
    # Constructing without an explicit registry still lets you address the
    # primary and fallback by name (used by the built-in default path).
    mimo = FakeTTSProvider("mimo")
    fish = FakeTTSProvider("fish")
    svc = VoiceService(mimo, fallback=fish)
    assert svc._providers == {"mimo": mimo, "fish": fish}
