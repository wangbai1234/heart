"""
Live: Real turn smoke test — exactly 1 turn with real DeepSeek.
per runtime_specs/07_agent_orchestration.md §3

Cost-capped at $0.10/run. Skipped without --live flag.
"""

import os
import pytest
from uuid import uuid4

from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole


@pytest.mark.live(max_cost=0.10)
class TestRealTurnSmoke:
    """1 real DeepSeek call — the simplest hot path smoke test."""

    @pytest.mark.asyncio
    async def test_live__deepseek_responds_to_basic_greeting(self, real_deepseek_provider, cost_tracker, per_test_budget):
        """Real DeepSeek responds to a simple greeting — the most basic health check.

        per runtime_specs/07_agent_orchestration.md §3
        """
        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.SYSTEM,
                    content="You are Rin, a tsundere AI companion. Respond naturally in Japanese or Chinese.",
                ),
                Message(
                    role=MessageRole.USER,
                    content="こんにちは、今日はいい天気ですね",
                ),
            ],
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=100,
        )

        response = await real_deepseek_provider.call(request)

        # Record cost
        usage = response.usage
        cost = real_deepseek_provider.estimate_cost(
            prompt_tokens=usage.get("prompt_tokens", 0),
            estimated_completion_tokens=usage.get("completion_tokens", 0),
            model="deepseek-chat",
        )
        cost_tracker.record_cost(cost.total_cost_usd)

        # Basic assertions
        assert response.content is not None
        assert len(response.content) > 0
        assert response.finish_reason in ["stop", "length"]

        # Should be under budget
        assert cost.total_cost_usd < 0.10, f"Cost ${cost.total_cost_usd:.4f} exceeded $0.10 budget"


@pytest.mark.live(max_cost=0.05)
class TestRealTurnMinimalLatency:
    """Minimal latency check — ensure API is responsive."""

    @pytest.mark.asyncio
    async def test_live__deepseek_responds_under_30_seconds(self, real_deepseek_provider, cost_tracker, per_test_budget):
        """Real DeepSeek should respond within 30 seconds.

        per runtime_specs/08_engineering_architecture.md §3
        """
        import time

        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hi",
                ),
            ],
            model="deepseek-chat",
            temperature=0.1,
            max_tokens=10,
        )

        start = time.monotonic()
        response = await real_deepseek_provider.call(request)
        elapsed = time.monotonic() - start

        cost = real_deepseek_provider.estimate_cost(
            prompt_tokens=response.usage.get("prompt_tokens", 0),
            estimated_completion_tokens=response.usage.get("completion_tokens", 0),
            model="deepseek-chat",
        )
        cost_tracker.record_cost(cost.total_cost_usd)

        assert elapsed < 30.0, f"Response took {elapsed:.1f}s, exceeding 30s limit"
        assert len(response.content) > 0
