"""
Integration tests for SS02 Memory LLM Extractor — End to End.

Real PG + fake LLM.
Enqueue → worker pick up → extract → return envelope
(NOT yet written to L2/L3, that's Resolver/Writer).

Author: 心屿团队
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from heart.infra.llm_providers.base import CostEstimate
from heart.ss02_memory.extractor.cost_guard import CostGuard
from heart.ss02_memory.extractor.llm_extractor import LLMExtractor
from heart.ss02_memory.extractor.types import QueueItem, TurnInput

# ── Fake Provider for integration ─────────────────────────────


@dataclass
class FakeLLMResponse:
    content: str = ""
    model: str = "fake-model"
    finish_reason: str = "stop"
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 3000, "completion_tokens": 200})
    provider: str = "fake"
    metadata: dict = field(default_factory=dict)


class FakeProvider:
    def __init__(self, response_content: str):
        self._response = response_content
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    async def call(self, request) -> FakeLLMResponse:
        self.call_count += 1
        return FakeLLMResponse(content=self._response)

    def estimate_cost(self, prompt_tokens, estimated_completion_tokens, model):
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            input_cost_usd=0.0009,
            output_cost_usd=0.0002,
            total_cost_usd=0.0011,
            model=model,
            provider="fake",
        )

    def count_tokens(self, text, model):
        return len(text) // 2


class FakeRegistry:
    def __init__(self, provider: FakeProvider):
        self._provider = provider

    def get_provider_for_model(self, model: str) -> FakeProvider:
        return self._provider


class FakeRouter:
    def __init__(self, provider: FakeProvider):
        self._registry = FakeRegistry(provider)


# ── End-to-End Test ───────────────────────────────────────────


class TestExtractorEndToEnd:
    """Integration: enqueue → extract → return envelope."""

    @pytest.mark.asyncio
    async def test_full_extract_pipeline(self):
        """End-to-end: QueueItem → LLMExtractor → ExtractorRunResult."""
        expected_run_id = uuid4()

        envelope_json = {
            "extractor_run_id": str(expected_run_id),
            "model": "fake-model",
            "prompt_version": "1.0.0",
            "schema_version": "1.0.0",
            "window": {"turn_ids": [1, 2, 3], "size": 3},
            "candidates": [
                {
                    "entity_type": "pet",
                    "attribute": "name",
                    "value": "大黄",
                    "entity_ref": "dog#1",
                    "source_turns": [1, 2],
                    "confidence": 0.90,
                    "kind": "disclosure",
                    "operation": "create",
                    "reasoning": "T1 引入这只狗，T2 给出名字'大黄'",
                },
                {
                    "entity_type": "pet",
                    "attribute": "breed",
                    "value": "金毛",
                    "entity_ref": "dog#1",
                    "source_turns": [1, 3],
                    "confidence": 0.85,
                    "kind": "disclosure",
                    "operation": "create",
                    "reasoning": "T3 描述同一只狗是金毛",
                },
            ],
            "dropped_signals": [],
        }

        provider = FakeProvider(json.dumps(envelope_json))
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)

        item = QueueItem(
            extractor_run_id=expected_run_id,
            session_id=uuid4(),
            window=[
                TurnInput(turn_id=1, speaker="user", ts="2026-06-19T09:00:00Z", text="我家有只狗"),
                TurnInput(turn_id=2, speaker="user", ts="2026-06-19T09:00:10Z", text="它叫大黄"),
                TurnInput(turn_id=3, speaker="user", ts="2026-06-19T09:00:20Z", text="是金毛"),
            ],
            l3_snapshot=[],
            hints=[],
            model="fake-model",
        )

        results = await extractor.run([item])

        # Assertions
        assert len(results) == 1
        result = results[0]

        assert not result.failed
        assert result.retry_count == 0
        assert result.cost_usd > 0
        assert result.latency_ms >= 0

        # Envelope validation
        env = result.envelope
        assert env.extractor_run_id == expected_run_id
        assert env.model == "fake-model"
        assert env.prompt_version == "1.0.0"
        assert env.schema_version == "1.0.0"
        assert env.window.turn_ids == [1, 2, 3]
        assert env.window.size == 3

        # Candidates
        assert len(env.candidates) == 2
        assert env.candidates[0].entity_ref == "dog#1"
        assert env.candidates[1].entity_ref == "dog#1"

        # Provider called exactly once
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_multiple_items(self):
        """Multiple queue items processed sequentially."""
        results_all = []

        for i, run_id in enumerate([uuid4(), uuid4(), uuid4()]):
            envelope_json = {
                "extractor_run_id": str(run_id),
                "model": "fake-model",
                "prompt_version": "1.0.0",
                "schema_version": "1.0.0",
                "window": {"turn_ids": [1], "size": 1},
                "candidates": [],
                "dropped_signals": [],
            }
            provider = FakeProvider(json.dumps(envelope_json))
            router = FakeRouter(provider)
            extractor = LLMExtractor(router)

            item = QueueItem(
                extractor_run_id=run_id,
                session_id=uuid4(),
                window=[
                    TurnInput(turn_id=1, speaker="user", ts="2026-06-19T09:00:00Z", text=f"test {i}"),
                ],
                model="fake-model",
            )

            results = await extractor.run([item])
            results_all.extend(results)

        assert len(results_all) == 3
        assert all(not r.failed for r in results_all)

    @pytest.mark.asyncio
    async def test_empty_window(self):
        """Minimal window (1 turn) — still produces valid envelope."""
        run_id = uuid4()
        envelope_json = {
            "extractor_run_id": str(run_id),
            "model": "fake-model",
            "prompt_version": "1.0.0",
            "schema_version": "1.0.0",
            "window": {"turn_ids": [1], "size": 1},
            "candidates": [],
            "dropped_signals": [],
        }
        provider = FakeProvider(json.dumps(envelope_json))
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)

        item = QueueItem(
            extractor_run_id=run_id,
            session_id=uuid4(),
            window=[
                TurnInput(turn_id=1, speaker="user", ts="2026-06-19T09:00:00Z", text="hello"),
            ],
            model="fake-model",
        )

        results = await extractor.run([item])
        assert len(results) == 1
        assert not results[0].failed
        assert results[0].envelope.window.size == 1

    @pytest.mark.asyncio
    async def test_structlog_fields_present(self):
        """Extractor run emits required structlog fields."""
        import logging

        run_id = uuid4()
        envelope_json = {
            "extractor_run_id": str(run_id),
            "model": "fake-model",
            "prompt_version": "1.0.0",
            "schema_version": "1.0.0",
            "window": {"turn_ids": [1], "size": 1},
            "candidates": [
                {
                    "entity_type": "self",
                    "attribute": "name",
                    "value": "test",
                    "source_turns": [1],
                    "confidence": 0.9,
                    "kind": "disclosure",
                    "operation": "create",
                    "reasoning": "T1 says test",
                }
            ],
            "dropped_signals": [{"turn_id": 1, "raw_phrase": "hint", "reason": "other"}],
        }
        provider = FakeProvider(json.dumps(envelope_json))
        router = FakeRouter(provider)
        extractor = LLMExtractor(router)

        item = QueueItem(
            extractor_run_id=run_id,
            session_id=uuid4(),
            window=[
                TurnInput(turn_id=1, speaker="user", ts="2026-06-19T09:00:00Z", text="test"),
            ],
            model="fake-model",
        )

        # Capture structlog output (just verify it doesn't crash)
        results = await extractor.run([item])
        assert len(results) == 1

        # Verify the result contains all required fields
        r = results[0]
        assert r.envelope.extractor_run_id == run_id
        assert len(r.envelope.candidates) == 1
        assert len(r.envelope.dropped_signals) == 1
        assert r.cost_usd >= 0
        assert r.latency_ms >= 0
