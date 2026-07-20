"""Unit tests for B3: multi-model router (stream_for / call_for) with failover.

Fake providers are used — no real HTTP calls. Tests verify:
- call_for returns (content, served_model) when first model succeeds
- call_for degrades to next model when first raises ProviderError
- call_for propagates exhaustion when all fail
- stream_for yields chunks and sets meta["served_model"] / meta["degraded_to"]
- stream_for degrades on ProviderError raised before first chunk
- _get_failover_chain deduplicates properly
- GrokProvider and ClaudeProvider have expected properties (no actual HTTP)
- Config fields for grok/claude are present with correct defaults
"""

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.infra.llm_providers.base import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ProviderError,
    StreamChunk,
)
from heart.infra.llm_providers.registry import ProviderRegistry
from heart.infra.llm_providers.router import DEFAULT_FAILOVER, ModelRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(*providers: tuple[str, "FakeProvider", list[str]]) -> ProviderRegistry:
    """Build a ProviderRegistry from (name, instance, models) tuples."""
    reg = ProviderRegistry(circuit_breaker=None)
    for name, instance, models in providers:
        reg.register_provider_instance(provider_name=name, provider=instance, models=models)
    return reg


def _messages() -> list[dict]:
    return [{"role": "user", "content": "hi"}]


class FakeProvider:
    """Synchronous-call fake that returns a fixed response or raises."""

    def __init__(self, content: str = "ok", raises: Exception | None = None):
        self._content = content
        self._raises = raises
        self.calls: int = 0

    async def call(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self._raises:
            raise self._raises
        return LLMResponse(
            content=self._content,
            model=request.model or "fake",
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            provider="fake",
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        self.calls += 1
        if self._raises:
            raise self._raises
        for word in self._content.split():
            yield StreamChunk(content=word + " ")


def _router(registry: ProviderRegistry) -> ModelRouter:
    return ModelRouter(registry=registry, main_model="deepseek", cheap_model="deepseek")


# ---------------------------------------------------------------------------
# call_for — success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_for_returns_content_and_served_model_when_first_succeeds():
    fake = FakeProvider(content="hello world")
    reg = _make_registry(("deepseek", fake, ["deepseek"]))
    router = _router(reg)

    content, served = await router.call_for("deepseek", _messages(), failover=[])
    assert content == "hello world"
    assert served == "deepseek"
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_call_for_served_model_matches_fallback_when_degraded():
    claude_fake = FakeProvider(
        raises=ProviderError("timeout", provider="claude", model="claude", retriable=True)
    )
    grok_fake = FakeProvider(content="grok answer")
    reg = _make_registry(
        ("claude", claude_fake, ["claude"]),
        ("grok", grok_fake, ["grok"]),
    )
    router = _router(reg)

    content, served = await router.call_for("claude", _messages(), failover=["grok"])
    assert content == "grok answer"
    assert served == "grok"
    assert claude_fake.calls == 1
    assert grok_fake.calls == 1


@pytest.mark.asyncio
async def test_call_for_full_failover_chain_claude_grok_deepseek():
    """Claude fails → Grok fails → DeepSeek succeeds."""
    claude_fake = FakeProvider(
        raises=ProviderError("500", provider="claude", model="claude", retriable=True)
    )
    grok_fake = FakeProvider(
        raises=ProviderError("429", provider="grok", model="grok", retriable=True)
    )
    deepseek_fake = FakeProvider(content="deepseek fallback")
    reg = _make_registry(
        ("claude", claude_fake, ["claude"]),
        ("grok", grok_fake, ["grok"]),
        ("deepseek", deepseek_fake, ["deepseek", "deepseek-chat"]),
    )
    router = _router(reg)

    content, served = await router.call_for("claude", _messages(), failover=["grok", "deepseek"])
    assert content == "deepseek fallback"
    assert served == "deepseek"


@pytest.mark.asyncio
async def test_call_for_exhaustion_raises_provider_error():
    err = ProviderError("down", provider="grok", model="grok", retriable=True)
    grok_fake = FakeProvider(raises=err)
    reg = _make_registry(("grok", grok_fake, ["grok"]))
    router = _router(reg)

    with pytest.raises(ProviderError) as exc_info:
        await router.call_for("grok", _messages(), failover=[])
    assert "exhausted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_call_for_skips_unregistered_model_silently():
    deepseek_fake = FakeProvider(content="ds ok")
    reg = _make_registry(("deepseek", deepseek_fake, ["deepseek"]))
    router = _router(reg)

    # "claude" not registered — should skip to "deepseek"
    content, served = await router.call_for("claude", _messages(), failover=["deepseek"])
    assert served == "deepseek"
    assert content == "ds ok"


# ---------------------------------------------------------------------------
# call_for — meta / logging (served_model is the non-degraded model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_for_no_degradation_when_first_succeeds():
    fake = FakeProvider(content="fine")
    reg = _make_registry(("grok", fake, ["grok"]))
    router = _router(reg)

    _, served = await router.call_for("grok", _messages(), failover=[])
    assert served == "grok"


# ---------------------------------------------------------------------------
# stream_for — success and meta population
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_for_yields_chunks_and_sets_served_model():
    fake = FakeProvider(content="hello there world")
    reg = _make_registry(("grok", fake, ["grok"]))
    router = _router(reg)

    meta: dict = {}
    chunks = []
    async for chunk in router.stream_for("grok", _messages(), failover=[], meta=meta):
        chunks.append(chunk)

    assert chunks  # at least one chunk
    assert "".join(chunks).strip() == "hello there world"
    assert meta["served_model"] == "grok"
    assert meta["degraded_to"] is None  # no degradation


@pytest.mark.asyncio
async def test_stream_for_sets_degraded_to_when_failover_occurs():
    claude_fake = FakeProvider(
        raises=ProviderError("503", provider="claude", model="claude", retriable=True)
    )
    grok_fake = FakeProvider(content="grok stream")
    reg = _make_registry(
        ("claude", claude_fake, ["claude"]),
        ("grok", grok_fake, ["grok"]),
    )
    router = _router(reg)

    meta: dict = {}
    chunks = []
    async for chunk in router.stream_for("claude", _messages(), failover=["grok"], meta=meta):
        chunks.append(chunk)

    assert meta["served_model"] == "grok"
    assert meta["degraded_to"] == "grok"
    assert "grok stream" in "".join(chunks)


@pytest.mark.asyncio
async def test_stream_for_exhaustion_raises():
    err = ProviderError("all down", provider="claude", model="claude", retriable=False)
    fake = FakeProvider(raises=err)
    reg = _make_registry(("claude", fake, ["claude"]))
    router = _router(reg)

    with pytest.raises(ProviderError) as exc_info:
        async for _ in router.stream_for("claude", _messages(), failover=[]):
            pass
    assert "exhausted" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Empty-response failover — the "deepseek 兜底" (bug: claude/grok returned an
# error-free but empty stream; the turn "completed" empty and the user saw
# "生成失败，请重试" instead of a deepseek fallback answer).
# ---------------------------------------------------------------------------


class EmptyFinishProvider:
    """Streams a single content-less finish frame (no text_delta) then stops.

    Mimics a provider that connects and completes cleanly but yields no content
    (e.g. an api_style/proxy mismatch where the parser matches no text). Must be
    treated as empty and fail over — first_chunk alone is not a reliable signal.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        self.calls += 1
        yield StreamChunk(content="", finish_reason="stop")


@pytest.mark.asyncio
async def test_stream_for_empty_response_fails_over_to_deepseek():
    """Claude yields an empty stream (no error) → must fall through to deepseek."""
    claude_empty = FakeProvider(content="")  # split() -> [] -> zero chunks
    deepseek_fake = FakeProvider(content="deepseek saved the turn")
    reg = _make_registry(
        ("claude", claude_empty, ["claude"]),
        ("deepseek", deepseek_fake, ["deepseek", "deepseek-chat"]),
    )
    router = _router(reg)

    meta: dict = {}
    chunks = []
    async for chunk in router.stream_for("claude", _messages(), failover=["deepseek"], meta=meta):
        chunks.append(chunk)

    assert "deepseek saved the turn" in "".join(chunks)
    assert meta["served_model"] == "deepseek"
    assert meta["degraded_to"] == "deepseek"
    assert claude_empty.calls == 1
    assert deepseek_fake.calls == 1


@pytest.mark.asyncio
async def test_stream_for_finish_only_frame_counts_as_empty_and_fails_over():
    claude_empty = EmptyFinishProvider()
    deepseek_fake = FakeProvider(content="fallback text")
    reg = _make_registry(
        ("claude", claude_empty, ["claude"]),
        ("deepseek", deepseek_fake, ["deepseek"]),
    )
    router = _router(reg)

    chunks = []
    async for chunk in router.stream_for("claude", _messages(), failover=["deepseek"]):
        chunks.append(chunk)

    assert "fallback text" in "".join(chunks)
    assert claude_empty.calls == 1


@pytest.mark.asyncio
async def test_stream_for_last_candidate_empty_returns_empty_gracefully():
    """When even the terminal provider is empty, stream_for returns empty (no
    raise) so the WS layer emits the clean "生成失败，请重试" instead of a stuck
    bubble."""
    deepseek_empty = FakeProvider(content="")
    reg = _make_registry(("deepseek", deepseek_empty, ["deepseek"]))
    router = _router(reg)

    meta: dict = {}
    chunks = []
    async for chunk in router.stream_for("deepseek", _messages(), failover=[], meta=meta):
        chunks.append(chunk)

    assert chunks == []
    assert meta["served_model"] == "deepseek"


@pytest.mark.asyncio
async def test_call_for_empty_response_fails_over_to_deepseek():
    claude_empty = FakeProvider(content="   ")  # whitespace-only == empty
    deepseek_fake = FakeProvider(content="real answer")
    reg = _make_registry(
        ("claude", claude_empty, ["claude"]),
        ("deepseek", deepseek_fake, ["deepseek"]),
    )
    router = _router(reg)

    content, served = await router.call_for("claude", _messages(), failover=["deepseek"])
    assert content == "real answer"
    assert served == "deepseek"
    assert claude_empty.calls == 1
    assert deepseek_fake.calls == 1


@pytest.mark.asyncio
async def test_call_for_last_candidate_empty_returns_empty():
    deepseek_empty = FakeProvider(content="")
    reg = _make_registry(("deepseek", deepseek_empty, ["deepseek"]))
    router = _router(reg)

    content, served = await router.call_for("deepseek", _messages(), failover=[])
    assert content == ""
    assert served == "deepseek"


@pytest.mark.asyncio
async def test_stream_for_meta_not_required():
    fake = FakeProvider(content="ok")
    reg = _make_registry(("deepseek", fake, ["deepseek"]))
    router = _router(reg)

    chunks = []
    async for chunk in router.stream_for("deepseek", _messages()):
        chunks.append(chunk)
    assert chunks


# ---------------------------------------------------------------------------
# _get_failover_chain — deduplication
# ---------------------------------------------------------------------------


def test_failover_chain_no_duplicates():
    router = _router(ProviderRegistry())
    chain = router._get_failover_chain("grok", ["claude", "grok", "deepseek"])
    # grok appears first (requested); subsequent grok in failover is dropped
    assert chain == ["grok", "claude", "deepseek"]
    # No duplicates
    assert len(chain) == len(set(chain))


def test_failover_chain_requested_model_not_in_failover():
    router = _router(ProviderRegistry())
    chain = router._get_failover_chain("claude", ["grok", "deepseek"])
    assert chain == ["claude", "grok", "deepseek"]


def test_failover_chain_empty_failover():
    router = _router(ProviderRegistry())
    chain = router._get_failover_chain("deepseek", [])
    assert chain == ["deepseek"]


# ---------------------------------------------------------------------------
# DEFAULT_FAILOVER constant
# ---------------------------------------------------------------------------


def test_default_failover_order():
    assert DEFAULT_FAILOVER == ["claude", "grok", "deepseek"]


# ---------------------------------------------------------------------------
# GrokProvider — properties (no HTTP)
# ---------------------------------------------------------------------------


def test_grok_provider_name_and_defaults():
    from heart.infra.llm_providers.grok import GrokProvider

    p = GrokProvider(api_key="fake-key")
    assert p.provider_name == "grok"
    assert p.DEFAULT_BASE_URL == "https://api.x.ai"
    assert p.DEFAULT_MODEL == "grok-3-mini-fast"


def test_grok_estimate_cost():
    from heart.infra.llm_providers.grok import GrokProvider

    p = GrokProvider(api_key="fake-key")
    est = p.estimate_cost(1000, 500, "grok-3-mini-fast")
    assert est.total_cost_usd > 0
    assert est.provider == "grok"


# ---------------------------------------------------------------------------
# ClaudeProvider — properties (no HTTP)
# ---------------------------------------------------------------------------


def test_claude_provider_name_and_defaults():
    from heart.infra.llm_providers.claude import ClaudeProvider

    p = ClaudeProvider(api_key="fake-key")
    assert p.provider_name == "claude"
    assert p.DEFAULT_BASE_URL == "https://api.anthropic.com"
    assert p.ANTHROPIC_VERSION == "2023-06-01"


def test_claude_estimate_cost():
    from heart.infra.llm_providers.claude import ClaudeProvider

    p = ClaudeProvider(api_key="fake-key")
    est = p.estimate_cost(1000, 500, "claude-sonnet-4-5")
    assert est.total_cost_usd > 0
    assert est.provider == "claude"


def test_claude_split_messages_extracts_system():
    from heart.infra.llm_providers.claude import ClaudeProvider

    p = ClaudeProvider(api_key="fake-key")
    msgs = [
        Message(role=MessageRole.SYSTEM, content="You are helpful."),
        Message(role=MessageRole.USER, content="Hello"),
    ]
    system_text, chat = p._split_messages(msgs)
    assert system_text == "You are helpful."
    assert len(chat) == 1
    assert chat[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Config fields — Grok and Claude keys present with correct defaults
# ---------------------------------------------------------------------------


def test_config_has_grok_fields():
    from heart.core.config import Settings

    # Only assert on the values that were explicitly supplied (base_url may be
    # overridden by the local .env, so we do not assert its exact default here).
    s = Settings(
        grok_api_key="test-grok",
        grok_model="grok-3-mini-fast",  # explicit to be env-independent
        jwt_algorithm="HS256",
        jwt_secret_key="a" * 32,
        deepseek_api_key="fake",
    )
    assert s.grok_api_key == "test-grok"
    assert s.grok_model == "grok-3-mini-fast"
    assert s.grok_cost_credits == 3


def test_config_has_claude_fields():
    from heart.core.config import Settings

    s = Settings(
        claude_api_key="test-claude",
        claude_model="claude-sonnet-4-5",  # explicit to be env-independent
        claude_api_style="anthropic",  # explicit to be env-independent
        jwt_algorithm="HS256",
        jwt_secret_key="a" * 32,
        deepseek_api_key="fake",
    )
    assert s.claude_api_key == "test-claude"
    assert s.claude_model == "claude-sonnet-4-5"
    assert s.claude_api_style == "anthropic"
    assert s.claude_cost_credits == 12


def test_config_membership_pricing_defaults():
    from heart.core.config import Settings

    s = Settings(
        jwt_algorithm="HS256",
        jwt_secret_key="a" * 32,
        deepseek_api_key="fake",
    )
    assert s.mimo_tts_cost_credits == 5
    assert s.fish_tts_cost_credits == 8
    assert s.clone_mimo_cost_credits == 50
    assert s.clone_fish_cost_credits == 100


def test_initialize_registry_registers_bare_deepseek_slug(monkeypatch):
    """Regression (showstopper B): the whole stack defaults to the bare slug
    model="deepseek" (ss07_orchestration/models.py) and it is the last link in the
    failover chain [claude, grok, deepseek]. initialize_registry must register that
    exact slug, otherwise free-tier turns raise KeyError (chat dead) or silently
    route to a paid model. Uses a dummy key — no network at construction time.
    """
    from heart.infra.llm_providers import registry as registry_mod

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-dummy")
    monkeypatch.delenv("DEEPSEEK_API_KEYS", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)

    reg = registry_mod.initialize_registry(circuit_breaker=None)

    # Must resolve without raising KeyError.
    assert reg.get_provider_for_model("deepseek") is not None


# ---------------------------------------------------------------------------
# Canonical model translation — the slug must NOT reach the vendor API
# ---------------------------------------------------------------------------


class RecordingProvider(FakeProvider):
    """Fake that records the request.model it was asked to serve."""

    def __init__(self, content: str = "ok"):
        super().__init__(content=content)
        self.seen_models: list[str] = []

    async def call(self, request: LLMRequest) -> LLMResponse:
        self.seen_models.append(request.model)
        return await super().call(request)

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        self.seen_models.append(request.model)
        async for chunk in super().stream(request):
            yield chunk


def test_registry_canonical_model_resolves_slug_to_first_model():
    reg = ProviderRegistry()
    reg.register_provider_instance(
        "deepseek-v4-flash", FakeProvider(), models=["deepseek-chat", "deepseek"]
    )
    # Bare slug and alias both resolve to the canonical (first) model name.
    assert reg.get_canonical_model("deepseek") == "deepseek-chat"
    assert reg.get_canonical_model("deepseek-chat") == "deepseek-chat"
    # Unknown model falls through unchanged.
    assert reg.get_canonical_model("mystery") == "mystery"


@pytest.mark.asyncio
async def test_call_for_sends_canonical_model_not_slug():
    """Regression (showstopper): DeepSeek API rejects the bare slug 'deepseek';
    it only accepts 'deepseek-chat'/'deepseek-reasoner'. The router must translate
    the routing slug to the canonical model before building the request body, while
    still reporting the slug as served_model for billing/labels."""
    rec = RecordingProvider(content="hi")
    reg = ProviderRegistry()
    reg.register_provider_instance("deepseek-v4-flash", rec, models=["deepseek-chat", "deepseek"])
    router = _router(reg)

    content, served = await router.call_for("deepseek", _messages(), failover=[])
    assert content == "hi"
    assert served == "deepseek"  # slug preserved for billing
    assert rec.seen_models == ["deepseek-chat"]  # canonical reached the provider


@pytest.mark.asyncio
async def test_stream_for_sends_canonical_model_not_slug():
    rec = RecordingProvider(content="hello world")
    reg = ProviderRegistry()
    reg.register_provider_instance("deepseek-v4-flash", rec, models=["deepseek-chat", "deepseek"])
    router = _router(reg)

    meta: dict = {}
    chunks = []
    async for chunk in router.stream_for("deepseek", _messages(), failover=[], meta=meta):
        chunks.append(chunk)

    assert "".join(chunks).strip() == "hello world"
    assert meta["served_model"] == "deepseek"  # slug preserved
    assert rec.seen_models == ["deepseek-chat"]  # canonical reached the provider
