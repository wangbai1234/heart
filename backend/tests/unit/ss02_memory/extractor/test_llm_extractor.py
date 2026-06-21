"""
Unit tests for SS02 Memory LLM Extractor — LLMExtractor.

Tests:
- 6 canonical scenarios from few-shot (positive cases)
- 2 malformed JSON → retry → success
- 1 cost cap exceeded → CostCapExceeded raised
- 1 schema validation failure → marked failed

Uses fake LLM provider that returns canned ExtractionEnvelope JSON.

Author: 心屿团队
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.infra.llm_providers.base import (
    CostEstimate,
    LLMResponse,
    MessageRole,
)
from heart.ss02_memory.extractor.cost_guard import CostCapExceeded, CostGuard
from heart.ss02_memory.extractor.llm_extractor import LLMExtractor
from heart.ss02_memory.extractor.types import QueueItem, TurnInput

# ── Fake LLM Provider ─────────────────────────────────────────


@dataclass
class FakeLLMResponse:
    """Simulates LLMResponse from the provider."""

    content: str = ""
    model: str = "fake-model"
    finish_reason: str = "stop"
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 3000, "completion_tokens": 200})
    provider: str = "fake"
    metadata: dict = field(default_factory=dict)


class FakeProvider:
    """Fake LLM provider that returns canned responses."""

    def __init__(self, response_content: str):
        self._response = response_content
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    async def call(self, request) -> FakeLLMResponse:
        self.call_count += 1
        return FakeLLMResponse(content=self._response)

    def estimate_cost(
        self, prompt_tokens: int, estimated_completion_tokens: int, model: str
    ) -> CostEstimate:
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            input_cost_usd=0.0009,
            output_cost_usd=0.0002,
            total_cost_usd=0.0011,
            model=model,
            provider="fake",
        )

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 2


class FakeProviderSequence:
    """Fake LLM provider that returns responses in sequence."""

    def __init__(self, responses: list[str]):
        self._responses = responses
        self._call_idx = 0
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    async def call(self, request) -> FakeLLMResponse:
        self.call_count += 1
        idx = min(self._call_idx, len(self._responses) - 1)
        self._call_idx += 1
        return FakeLLMResponse(content=self._responses[idx])

    def estimate_cost(
        self, prompt_tokens: int, estimated_completion_tokens: int, model: str
    ) -> CostEstimate:
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            input_cost_usd=0.0009,
            output_cost_usd=0.0002,
            total_cost_usd=0.0011,
            model=model,
            provider="fake",
        )

    def count_tokens(self, text: str, model: str) -> int:
        return len(text) // 2


class FakeRegistry:
    """Fake provider registry."""

    def __init__(self, provider):
        self._provider = provider

    def get_provider_for_model(self, model: str):
        return self._provider


class FakeRouter:
    """Fake ModelRouter for testing."""

    def __init__(self, provider):
        self._registry = FakeRegistry(provider)


# ── Helper: build QueueItem ───────────────────────────────────


def make_queue_item(
    run_id=None,
    window=None,
    l3=None,
    hints=None,
    model="fake-model",
):
    """Build a QueueItem for testing."""
    if window is None:
        window = [
            TurnInput(turn_id=10, speaker="user", ts="2026-06-18T10:00:00Z", text="我家有只猫"),
            TurnInput(turn_id=11, speaker="assistant", ts="2026-06-18T10:00:05Z", text="哦真的？"),
            TurnInput(turn_id=12, speaker="user", ts="2026-06-18T10:00:20Z", text="嗯，她叫妙妙"),
        ]
    return QueueItem(
        extractor_run_id=run_id or uuid4(),
        session_id=uuid4(),
        window=window,
        l3_snapshot=l3 or [],
        hints=hints or [],
        model=model,
        prompt_version="1.0.0",
        schema_version="1.0.0",
    )


def _make_envelope_json(
    run_id: str,
    window_turn_ids: list[int],
    candidates: list[dict] | None = None,
    dropped_signals: list[dict] | None = None,
) -> str:
    """Build a valid envelope JSON string."""
    return json.dumps({
        "extractor_run_id": run_id,
        "model": "fake-model",
        "prompt_version": "1.0.0",
        "schema_version": "1.0.0",
        "window": {"turn_ids": window_turn_ids, "size": len(window_turn_ids)},
        "candidates": candidates or [],
        "dropped_signals": dropped_signals or [],
    })


# ── 6 Canonical Scenarios (from few-shot examples) ────────────


class TestCanonicalScenarios:
    """6 canonical scenarios from few-shot examples — positive cases."""

    @pytest.mark.asyncio
    async def test_fragmentation_coreference(self):
        """Example 1: Fragmentation + Coreference — shared entity_ref, union of source_turns."""
        run_id = uuid4()
        envelope_json = _make_envelope_json(
            str(run_id), [10, 11, 12],
            candidates=[
                {
                    "entity_type": "pet", "attribute": "name", "value": "妙妙",
                    "entity_ref": "cat#1", "source_turns": [10, 12],
                    "confidence": 0.92, "kind": "disclosure", "operation": "create",
                    "reasoning": "T10 引入这只猫，T12 给出名字'妙妙'",
                },
                {
                    "entity_type": "pet", "attribute": "color", "value": "灰白色",
                    "entity_ref": "cat#1", "source_turns": [10, 12],
                    "confidence": 0.85, "kind": "disclosure", "operation": "create",
                    "reasoning": "T12 描述同一只猫是灰白色",
                },
            ],
        )
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert len(results[0].envelope.candidates) == 2
        refs = {c.entity_ref for c in results[0].envelope.candidates}
        assert refs == {"cat#1"}

    @pytest.mark.asyncio
    async def test_rhetoric(self):
        """Example 2: Rhetoric — kept as candidate, not dropped."""
        run_id = uuid4()
        envelope_json = _make_envelope_json(
            str(run_id), [20, 21],
            candidates=[{
                "entity_type": "self", "attribute": "health_condition",
                "value": "我有病了", "source_turns": [21], "confidence": 0.30,
                "kind": "rhetoric", "operation": "create",
                "reasoning": "T21 接'算了不说了'+尾随'哈哈'，自嘲非字面健康陈述",
            }],
        )
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)
        item.window = [
            TurnInput(turn_id=20, speaker="user", ts="2026-06-18T11:00:00Z", text="工作好累"),
            TurnInput(turn_id=21, speaker="user", ts="2026-06-18T11:00:15Z", text="算了不说了，我有病了哈哈"),
        ]

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert len(results[0].envelope.candidates) == 1
        assert results[0].envelope.candidates[0].kind.value == "rhetoric"

    @pytest.mark.asyncio
    async def test_question_only(self):
        """Example 3: Question only — empty candidates, no drops."""
        run_id = uuid4()
        envelope_json = _make_envelope_json(str(run_id), [30, 31, 32])
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)
        item.window = [
            TurnInput(turn_id=30, speaker="user", ts="2026-06-18T12:00:00Z", text="你还记得我叫什么吗？"),
            TurnInput(turn_id=31, speaker="assistant", ts="2026-06-18T12:00:05Z", text="（想了想）"),
            TurnInput(turn_id=32, speaker="user", ts="2026-06-18T12:00:30Z", text="算啦"),
        ]

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert len(results[0].envelope.candidates) == 0
        assert len(results[0].envelope.dropped_signals) == 0

    @pytest.mark.asyncio
    async def test_negation_soft_delete(self):
        """Example 4: Negation → soft_delete with prior_value_id from L3."""
        from heart.ss02_memory.extractor.types import L3FactSnapshot

        run_id = uuid4()
        prior_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        envelope_json = _make_envelope_json(
            str(run_id), [40, 41],
            candidates=[{
                "entity_type": "pet", "attribute": "name", "value": "妙妙",
                "entity_ref": "cat#1", "prior_value_id": prior_id,
                "source_turns": [41], "confidence": 0.88,
                "kind": "negation", "operation": "soft_delete",
                "reasoning": "T41: 用户明确说'现在没有宠物了'，撤回 L3 中的猫 fact",
            }],
        )
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)
        item.window = [
            TurnInput(turn_id=40, speaker="user", ts="2026-06-18T13:00:00Z", text="跟你说个事"),
            TurnInput(turn_id=41, speaker="user", ts="2026-06-18T13:00:10Z", text="我现在没有宠物了，上个月送走了"),
        ]
        item.l3_snapshot = [
            L3FactSnapshot(
                fact_id=prior_id, entity_type="pet", entity_ref="cat#1",
                attribute="name", value="妙妙", confidence=0.92,
                last_seen="2026-05-20",
            ),
        ]

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert results[0].envelope.candidates[0].kind.value == "negation"
        assert results[0].envelope.candidates[0].operation.value == "soft_delete"
        assert str(results[0].envelope.candidates[0].prior_value_id) == prior_id

    @pytest.mark.asyncio
    async def test_supersession(self):
        """Example 5: Supersession with prior_value_id from L3."""
        from heart.ss02_memory.extractor.types import L3FactSnapshot

        run_id = uuid4()
        prior_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        envelope_json = _make_envelope_json(
            str(run_id), [50, 51],
            candidates=[{
                "entity_type": "self", "attribute": "location_residence",
                "value": "上海", "prior_value_id": prior_id,
                "source_turns": [50, 51], "confidence": 0.90,
                "kind": "disclosure", "operation": "supersede",
                "reasoning": "T50 否定旧居住地'北京'，T51 给出新居住地'上海'",
            }],
        )
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)
        item.window = [
            TurnInput(turn_id=50, speaker="user", ts="2026-06-18T14:00:00Z", text="其实我现在不在北京了"),
            TurnInput(turn_id=51, speaker="user", ts="2026-06-18T14:00:10Z", text="上个月搬到了上海"),
        ]
        item.l3_snapshot = [
            L3FactSnapshot(
                fact_id=prior_id, entity_type="self",
                attribute="location_residence", value="北京",
                confidence=0.90, last_seen="2026-03-01",
            ),
        ]

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert results[0].envelope.candidates[0].operation.value == "supersede"
        assert results[0].envelope.candidates[0].value == "上海"

    @pytest.mark.asyncio
    async def test_correct_rejection(self):
        """Example 6: Correct rejection — empty candidates, dropped_signals populated."""
        run_id = uuid4()
        envelope_json = _make_envelope_json(
            str(run_id), [60, 61],
            dropped_signals=[{
                "turn_id": 61, "raw_phrase": "跟我一样",
                "reason": "ambiguous_reference",
            }],
        )
        provider = FakeProvider(envelope_json)
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)
        item.window = [
            TurnInput(turn_id=60, speaker="user", ts="2026-06-18T15:00:00Z", text="我朋友很喜欢猫"),
            TurnInput(turn_id=61, speaker="user", ts="2026-06-18T15:00:15Z", text="跟我一样"),
        ]

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert len(results[0].envelope.candidates) == 0
        assert len(results[0].envelope.dropped_signals) == 1
        assert results[0].envelope.dropped_signals[0].reason.value == "ambiguous_reference"


# ── Malformed JSON → retry → success ──────────────────────────


class TestMalformedJsonRetry:
    """Malformed JSON from LLM → retry with error feedback → success."""

    @pytest.mark.asyncio
    async def test_malformed_then_valid(self):
        """First call returns invalid JSON, second returns valid envelope."""
        run_id = uuid4()
        valid_envelope = _make_envelope_json(str(run_id), [10, 11, 12])

        provider = FakeProviderSequence([
            "I'm not sure what to extract from this conversation...",
            valid_envelope,
        ])
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert results[0].retry_count == 1
        assert provider.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_malformed_twice_fails(self):
        """Both calls return malformed JSON → marked as failed."""
        provider = FakeProviderSequence([
            "not json at all",
            "still not json",
        ])
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=uuid4())

        results = await extractor.run([item])
        assert len(results) == 1
        assert results[0].failed
        assert results[0].retry_count == 1


# ── Cost Cap Exceeded ─────────────────────────────────────────


class TestCostCapExceeded:
    """Cost cap exceeded → CostCapExceeded raised."""

    @pytest.mark.asyncio
    async def test_cost_cap_exceeded_before_call(self):
        """Projected cost exceeds cap → CostCapExceeded raised, extraction skipped."""
        run_id = uuid4()
        valid_envelope = _make_envelope_json(str(run_id), [10])
        provider = FakeProvider(valid_envelope)
        router = FakeRouter(provider)

        # Set very low cost cap
        cost_guard = CostGuard(cost_cap_usd=0.0001)
        extractor = LLMExtractor(router, cost_guard=cost_guard)
        item = make_queue_item(run_id=run_id)
        item.window = [TurnInput(turn_id=10, speaker="user", ts="2026-06-18T10:00:00Z", text="hi")]

        results = await extractor.run([item])
        assert len(results) == 1
        assert results[0].failed
        assert "cost" in results[0].error.lower()
        # Provider should NOT have been called
        assert provider.call_count == 0


# ── Schema Validation Failure ─────────────────────────────────


class TestSchemaValidationFailure:
    """Schema validation failure → marked as failed after retry."""

    @pytest.mark.asyncio
    async def test_window_mismatch(self):
        """Envelope window.turn_ids doesn't match input → validation fails."""
        run_id = uuid4()
        # Envelope has wrong turn_ids (99, 100) but input has (10, 11, 12)
        envelope_json = _make_envelope_json(str(run_id), [99, 100])
        provider = FakeProviderSequence([envelope_json, envelope_json])
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)

        results = await extractor.run([item])
        assert len(results) == 1
        assert results[0].failed
        assert "mismatch" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_source_turns_outside_window(self):
        """Candidate source_turns references turn outside window → validation fails."""
        run_id = uuid4()
        envelope_json = _make_envelope_json(
            str(run_id), [10, 11, 12],
            candidates=[{
                "entity_type": "self", "attribute": "name", "value": "test",
                "source_turns": [10, 99],  # 99 not in window
                "confidence": 0.9, "kind": "disclosure", "operation": "create",
                "reasoning": "T10 says test",
            }],
        )
        provider = FakeProviderSequence([envelope_json, envelope_json])
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)
        item = make_queue_item(run_id=run_id)

        results = await extractor.run([item])
        assert len(results) == 1
        assert results[0].failed
        assert "source_turn" in results[0].error.lower()
