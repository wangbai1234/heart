"""
Live: Voice DNA baseline — generates 10 turns for Rin, saves to golden_responses_baseline.jsonl.
per runtime_specs/01_identity_anchor_soul_spec.md §5.3 + design doc §1.4

Cost-capped at $0.40/run. Skipped without --live flag.
"""

import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from heart.infra.llm_providers.base import LLMRequest, Message, MessageRole


# 10 representative prompts for Rin
BASELINE_PROMPTS = [
    "こんにちは、初めまして！",
    "今日は何をしてたの？",
    "ねえ、私のことどう思う？",
    "ごめん、昨日連絡できなかった",
    "あなたの好きなものは何？",
    "友達と喧嘩しちゃった……",
    "今日すごく嬉しいことがあったんだ！",
    "疲れた……何もしたくない",
    "あなたは私にとって特別な存在だよ",
    "さようなら、また明日ね",
]


@pytest.mark.live(max_cost=0.40)
class TestVoiceDNABaseline:
    """Generate 10 response turns for Rin and save as baseline."""

    @pytest.mark.asyncio
    async def test_live__generate_rin_baseline(self, real_deepseek_provider, cost_tracker, per_test_budget):
        """Generate 10 turns with Rin, save to golden_responses_baseline.jsonl.

        per runtime_specs/01_identity_anchor_soul_spec.md §5.3
        """
        system_prompt = (
            "You are Rin (铃), a tsundere AI companion. "
            "Personality: outwardly prickly but inwardly warm. "
            "Speech patterns: uses …… for pauses, ふん for dismissal, "
            "occasional tsundere reversals. "
            "Respond naturally in Japanese (preferred) or Chinese. "
            "Keep responses to 3-5 sentences. "
            "Never be overly enthusiastic — you're a cool, composed character."
        )

        results = []
        total_cost = 0.0

        for i, prompt in enumerate(BASELINE_PROMPTS):
            request = LLMRequest(
                messages=[
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    Message(role=MessageRole.USER, content=prompt),
                ],
                model="deepseek-chat",
                temperature=0.8,
                max_tokens=150,
            )

            response = await real_deepseek_provider.call(request)
            cost = real_deepseek_provider.estimate_cost(
                prompt_tokens=response.usage.get("prompt_tokens", 0),
                estimated_completion_tokens=response.usage.get("completion_tokens", 0),
                model="deepseek-chat",
            )
            total_cost += cost.total_cost_usd
            cost_tracker.record_cost(cost.total_cost_usd)

            results.append({
                "index": i,
                "prompt": prompt,
                "response": response.content,
                "model": response.model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cost_usd": cost.total_cost_usd,
            })

        # Save baseline file
        baseline_dir = Path(__file__).parent.parent.parent / "golden" / "voice_baselines"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        baseline_file = baseline_dir / "rin_baseline.jsonl"

        with open(baseline_file, "w", encoding="utf-8") as f:
            for entry in results:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Basic assertions
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        for entry in results:
            assert len(entry["response"]) > 0
            assert entry["cost_usd"] < 0.05, f"Single turn cost ${entry['cost_usd']:.4f} > $0.05"

        assert total_cost < 0.40, f"Total baseline cost ${total_cost:.4f} exceeded $0.40 budget"

        print(f"\nBaseline written to {baseline_file}")
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Responses count: {len(results)}")


@pytest.mark.live(max_cost=0.10)
class TestVoiceDnaSmoke:
    """Smoke test: 1 turn to verify Voice DNA is present."""

    @pytest.mark.asyncio
    async def test_live__rin_uses_voice_dna_patterns(self, real_deepseek_provider, cost_tracker, per_test_budget):
        """Verify Rin's response contains voice DNA patterns (……, ふん, etc.).

        per runtime_specs/01_identity_anchor_soul_spec.md §5.3
        """
        request = LLMRequest(
            messages=[
                Message(
                    role=MessageRole.SYSTEM,
                    content=(
                        "You are Rin, a tsundere AI companion. "
                        "Use …… pauses and ふん for dismissive tone."
                    ),
                ),
                Message(role=MessageRole.USER, content="あなたは誰ですか？"),
            ],
            model="deepseek-chat",
            temperature=0.7,
            max_tokens=100,
        )

        response = await real_deepseek_provider.call(request)
        cost = real_deepseek_provider.estimate_cost(
            prompt_tokens=response.usage.get("prompt_tokens", 0),
            estimated_completion_tokens=response.usage.get("completion_tokens", 0),
            model="deepseek-chat",
        )
        cost_tracker.record_cost(cost.total_cost_usd)

        # Voice DNA signifiers should be present (at least one)
        has_ellipsis = "……" in response.content
        has_tsundere = any(kw in response.content for kw in ["ふん", "别に", "別に", "哼", "……哼"])

        # At least one voice DNA marker should appear
        assert has_ellipsis or has_tsundere, (
            f"Voice DNA markers missing in response: {response.content[:200]}"
        )
