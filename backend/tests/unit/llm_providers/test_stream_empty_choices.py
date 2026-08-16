"""Provider SSE parsers must survive a trailing empty-``choices`` frame.

Regression for the "only first sentence" bug: the micu relay appends a
usage/fingerprint frame with ``"choices": []`` right before ``[DONE]`` on
Gemini (and sometimes DeepSeek) streams. The parsers did ``data["choices"][0]``
guarded only by ``except json.JSONDecodeError``, so the empty array raised
``IndexError`` and killed the stream mid-flight. With the first sentence already
on the wire the router could not fail over, leaving the user with a truncated
one-sentence reply. The parsers now skip any choiceless frame.
"""

from __future__ import annotations

import pytest

from heart.infra.llm_providers.claude import ClaudeProvider
from heart.infra.llm_providers.deepseek import DeepSeekV4FlashProvider
from heart.infra.llm_providers.deepseek_pro import DeepSeekV4ProProvider
from heart.infra.llm_providers.grok import GrokProvider


class _FakeResp:
    """Minimal stand-in for an httpx streaming response."""

    def __init__(self, lines: list[str]):
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


# Content, then finish_reason, then a micu trailing empty-choices frame, [DONE].
_MICU_LINES = [
    'data: {"choices":[{"delta":{"content":"（抱住你）"}}]}',
    'data: {"choices":[{"delta":{"content":"宝贝我在呢。"}}]}',
    'data: {"choices":[{"delta":{"content":"再多说几句给你听。"}}]}',
    'data: {"choices":[{"finish_reason":"stop"}],"usage":{"total_tokens":10}}',
    'data: {"id":"x","object":"chat.completion.chunk","choices":[]}',
    "data: [DONE]",
]

_EXPECTED = "（抱住你）宝贝我在呢。再多说几句给你听。"


async def _collect_raw(agen) -> str:
    return "".join([c.content async for c in agen if c.content])


@pytest.mark.asyncio
async def test_grok_raw_chunks_survives_empty_choices_frame():
    full = await _collect_raw(GrokProvider._raw_chunks(_FakeResp(_MICU_LINES)))
    assert full == _EXPECTED


@pytest.mark.asyncio
async def test_grok_raw_chunks_only_empty_choices_yields_nothing():
    # A stream that is nothing but the trailing frame must not raise, must yield
    # no content (router then treats it as empty and fails over).
    lines = ['data: {"choices":[]}', "data: [DONE]"]
    full = await _collect_raw(GrokProvider._raw_chunks(_FakeResp(lines)))
    assert full == ""


class _FakeStreamResp(_FakeResp):
    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeClient:
    """httpx.AsyncClient stand-in whose ``.stream`` replays fixed SSE lines."""

    def __init__(self, lines: list[str]):
        self._lines = lines

    def stream(self, *_args, **_kwargs):
        return _FakeStreamResp(self._lines)


class _NoBreaker:
    def is_open(self, *_a, **_k):
        return False

    def record_success(self, *_a, **_k):
        pass

    def record_failure(self, *_a, **_k):
        pass


def _req():
    from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole

    return LLMRequest(
        messages=[Message(role=MessageRole.USER, content="hi")],
        model="test-model",
        stream=True,
    )


async def _collect_provider(provider) -> str:
    provider._client = _FakeClient(_MICU_LINES)  # bypass _get_client network path
    return "".join([c.content async for c in provider.stream(_req()) if c.content])


@pytest.mark.asyncio
async def test_deepseek_pro_stream_survives_empty_choices_frame():
    prov = DeepSeekV4ProProvider(api_key="test", base_url="http://x", circuit_breaker=_NoBreaker())
    assert await _collect_provider(prov) == _EXPECTED


@pytest.mark.asyncio
async def test_deepseek_flash_stream_survives_empty_choices_frame():
    prov = DeepSeekV4FlashProvider(api_key="test", base_url="http://x", circuit_breaker=_NoBreaker())
    assert await _collect_provider(prov) == _EXPECTED


@pytest.mark.asyncio
async def test_claude_openai_compat_stream_survives_empty_choices_frame():
    # The empty-choices frame only occurs on the OpenAI-compatible SSE path
    # (the one that reads data["choices"]); the native Anthropic path uses a
    # different event schema and is not affected.
    prov = ClaudeProvider(
        api_key="test",
        base_url="http://x",
        circuit_breaker=_NoBreaker(),
        api_style="openai-compat",
    )
    assert await _collect_provider(prov) == _EXPECTED
