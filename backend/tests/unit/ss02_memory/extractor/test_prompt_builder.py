"""
Unit tests for SS02 Memory LLM Extractor — Prompt Builder.

Tests:
- Renders deterministically given same input
- Includes all 3 input sections (window, L3 snapshot, hints)
- Metadata echoed correctly

Author: 心屿团队
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from heart.ss02_memory.extractor.prompt_builder import (
    MODEL,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    PromptBuilder,
)
from heart.ss02_memory.extractor.types import Hint, L3FactSnapshot, TurnInput


@pytest.fixture
def builder():
    return PromptBuilder()


@pytest.fixture
def sample_window():
    return [
        TurnInput(
            turn_id=10,
            speaker="user",
            ts="2026-06-18T10:00:00Z",
            text="我家有只猫",
        ),
        TurnInput(
            turn_id=11,
            speaker="assistant",
            ts="2026-06-18T10:00:05Z",
            text="哦真的？",
        ),
        TurnInput(
            turn_id=12,
            speaker="user",
            ts="2026-06-18T10:00:20Z",
            text="嗯，她叫妙妙，灰白色的",
        ),
    ]


@pytest.fixture
def sample_l3():
    return [
        L3FactSnapshot(
            fact_id=uuid4(),
            entity_type="self",
            attribute="name",
            value="张三",
            confidence=0.95,
            last_seen="2026-05-01",
        ),
    ]


@pytest.fixture
def sample_hints():
    return [
        Hint(turn_id=12, raw_phrase="她叫妙妙", suspected_attribute="name"),
    ]


class TestPromptBuilderDeterministic:
    """Prompt renders deterministically given same input."""

    def test_same_input_same_output(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        run_id = uuid4()
        out1 = builder.build(sample_window, sample_l3, sample_hints, run_id)
        out2 = builder.build(sample_window, sample_l3, sample_hints, run_id)
        assert out1 == out2

    def test_different_run_id_different_output(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out1 = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        out2 = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        # Different run_id → different output (metadata section differs)
        assert out1 != out2


class TestPromptBuilderSections:
    """Prompt includes all 3 input sections."""

    def test_window_section_present(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "Window (chronological)" in out
        assert "[T10]" in out
        assert "[T11]" in out
        assert "[T12]" in out
        assert "我家有只猫" in out

    def test_l3_snapshot_section_present(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "L3 snapshot" in out
        assert "fact_id=" in out
        assert "self.name" in out

    def test_l3_snapshot_empty(
        self, builder, sample_window, sample_hints
    ):
        out = builder.build(sample_window, [], sample_hints, uuid4())
        assert "(empty)" in out

    def test_hints_section_present(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "Regex hints" in out
        assert "T12" in out
        assert "她叫妙妙" in out

    def test_hints_empty(
        self, builder, sample_window, sample_l3
    ):
        out = builder.build(sample_window, sample_l3, [], uuid4())
        assert "(none)" in out


class TestPromptBuilderMetadata:
    """Metadata echoed correctly."""

    def test_metadata_present(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        run_id = uuid4()
        out = builder.build(sample_window, sample_l3, sample_hints, run_id)
        assert "Run metadata" in out
        assert str(run_id) in out
        assert f"model: {MODEL}" in out
        assert f"prompt_version: {PROMPT_VERSION}" in out
        assert f"schema_version: {SCHEMA_VERSION}" in out
        assert "window.turn_ids: [10, 11, 12]" in out

    def test_prompt_version_and_schema_version(
        self, builder
    ):
        assert PROMPT_VERSION == "1.0.2"
        assert SCHEMA_VERSION == "1.0.0"

    def test_custom_versions(
        self,
        sample_window, sample_l3, sample_hints
    ):
        custom = PromptBuilder(prompt_version="1.1.0", schema_version="1.1.0")
        out = custom.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "prompt_version: 1.1.0" in out
        assert "schema_version: 1.1.0" in out


class TestPromptBuilderFewShot:
    """Few-shot examples are included."""

    def test_few_shot_included(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "Example 1 — Fragmentation + Coreference" in out
        assert "Example 2 — Rhetoric" in out
        assert "Example 3 — Question only" in out
        assert "Example 4 — Negation" in out
        assert "Example 5 — Supersession" in out
        assert "Example 6 — Correct rejection" in out

    def test_system_rules_included(
        self, builder, sample_window, sample_l3, sample_hints
    ):
        out = builder.build(sample_window, sample_l3, sample_hints, uuid4())
        assert "R1" in out
        assert "R2" in out
        assert "R3" in out
        assert "R4" in out
        assert "R5" in out
        assert "R6" in out
        assert "R7" in out
        assert "R8" in out
        assert "R9" in out
