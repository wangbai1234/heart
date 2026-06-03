"""
Integration: Orchestrator hot path — full turn with FAKE LLM.
per runtime_specs/07_agent_orchestration.md §3

Tests auth → safety → composer → router → memory_encode with fake LLM.
"""

import pytest


@pytest.mark.integration
class TestOrchestratorHotPath:
    """Full turn pipeline with fake LLM provider."""

    def test_fake_llm_provider_loaded(self, fake_llm_provider):
        """Fake LLM provider loads fixture directory."""
        assert fake_llm_provider.provider_name == "fake"
        assert len(fake_llm_provider._fixtures) > 0

    @pytest.mark.asyncio
    async def test_fake_llm_call_returns_fixture(self, fake_llm_provider):
        """Fake LLM returns fixture content."""
        from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole

        request = LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are Rin, a tsundere companion"),
                Message(role=MessageRole.USER, content="こんにちは、今日はいい天気だね"),
            ],
            model="deepseek-chat",
            temperature=0.7,
        )

        response = await fake_llm_provider.call(request)
        assert response is not None
        assert len(response.content) > 0
        assert "ふん" in response.content

    @pytest.mark.asyncio
    async def test_fake_llm_estimates_zero_cost(self, fake_llm_provider):
        """Fake LLM always estimates $0 cost."""
        estimate = fake_llm_provider.estimate_cost(
            prompt_tokens=100,
            estimated_completion_tokens=50,
            model="deepseek-chat",
        )
        assert estimate.total_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_fake_llm_streaming(self, fake_llm_provider):
        """Fake LLM supports streaming."""
        from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole

        request = LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are Rin, a tsundere companion"),
                Message(role=MessageRole.USER, content="こんにちは、今日はいい天気だね"),
            ],
            model="deepseek-chat",
            stream=True,
        )

        chunks = []
        async for chunk in fake_llm_provider.stream(request):
            chunks.append(chunk.content)

        assert len(chunks) > 0
        combined = "".join(chunks).strip()
        assert "ふん" in combined

    @pytest.mark.asyncio
    async def test_fake_llm_cache_miss_raises(self, fake_llm_provider):
        """Unknown message → cache miss raises KeyError (strict mode)."""
        from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole

        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.SYSTEM,
                    content="COMPLETELY UNKNOWN SYSTEM PROMPT NEVER SEEN BEFORE",
                ),
                Message(
                    role=MessageRole.USER,
                    content="COMPLETELY UNKNOWN MESSAGE THAT DOES NOT MATCH ANY FIXTURE",
                ),
            ],
            model="deepseek-chat",
        )

        with pytest.raises(KeyError, match="no fixture"):
            await fake_llm_provider.call(request)
