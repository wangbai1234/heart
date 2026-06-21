"""Unit tests for MemoryService.retrieve() ScoredMemory → RetrievedMemory conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss02_memory.retriever.base import ScoredMemory
from heart.ss02_memory.service import (
    ForgettingHint,
    MemoryRetrievalResult,
    MemoryService,
    QueryContext,
    RetrievedMemory,
    _fallback_text,
    _state_to_uncertainty,
)


@pytest.fixture
def memory_service():
    """Create a MemoryService with mock DB."""
    svc = MemoryService(db_session=MagicMock())
    return svc


def _make_scored_memory(memory_type="L2", state="vivid", summary="用户叫李明"):
    """Create a mock ScoredMemory."""
    mock_memory = MagicMock()
    mock_memory.state = state
    mock_memory.episode_summary = summary
    mock_memory.summary = summary
    mock_memory.literal_text = summary
    return ScoredMemory(
        memory=mock_memory,
        memory_id=uuid4(),
        memory_type=memory_type,
        score=0.8,
        score_breakdown={"semantic": 0.7, "recency": 0.9},
    )


def _make_query_context():
    return QueryContext(
        current_message="你好",
        recent_turns=[],
        session_id=uuid4(),
        user_id=uuid4(),
        character_id="rin",
    )


class TestFallbackText:
    """Tests for _fallback_text helper."""

    def test_episodic_memory(self):
        mem = MagicMock()
        mem.episode_summary = "用户叫李明"
        mem.summary = None
        mem.literal_text = None
        assert _fallback_text(mem) == "用户叫李明"

    def test_fact_node(self):
        mem = MagicMock()
        mem.episode_summary = None
        mem.summary = None
        mem.literal_text = "李明在上海工作"
        assert _fallback_text(mem) == "李明在上海工作"

    def test_non_empty_fallback(self):
        mem = MagicMock()
        mem.episode_summary = None
        mem.summary = None
        mem.literal_text = None
        mem.key = "名字"
        mem.value = "李明"
        result = _fallback_text(mem)
        assert result  # non-empty

    def test_str_fallback(self):
        mem = "some memory string"
        assert _fallback_text(mem) == "some memory string"


class TestStateToUncertainty:
    """Tests for _state_to_uncertainty helper."""

    def test_vivid(self):
        assert _state_to_uncertainty("vivid") == 0.0

    def test_fading(self):
        assert _state_to_uncertainty("fading") == 0.3

    def test_faint(self):
        assert _state_to_uncertainty("faint") == 0.6

    def test_dormant(self):
        assert _state_to_uncertainty("dormant") == 0.8

    def test_archived(self):
        assert _state_to_uncertainty("archived") == 0.95

    def test_unknown(self):
        assert _state_to_uncertainty("unknown") == 0.5

    def test_none(self):
        assert _state_to_uncertainty(None) == 0.5


class TestRetrieveConversion:
    """Tests for MemoryService.retrieve() conversion layer."""

    @pytest.mark.asyncio
    async def test_returns_retrieved_memory_with_reconstructed_text(self, memory_service):
        """retrieve() should return RetrievedMemory with reconstructed_text."""
        sm = _make_scored_memory()

        mock_orch_result = MagicMock()
        mock_orch_result.memories = [sm]
        mock_orch_result.total_candidates = 1
        mock_orch_result.strategies_used = ["recency"]
        mock_orch_result.retrieval_time_ms = 10.0
        mock_orch_result.l4_included = 0
        mock_orch_result.recently_forgotten_hints = []

        mock_recon = MagicMock()
        mock_recon.reconstruct.return_value = "你好像说过你叫李明"
        mock_recon.voice_dna = ["v1", "v2"]
        memory_service._get_reconstructor = MagicMock(return_value=mock_recon)

        with patch("heart.ss02_memory.retriever.orchestrator.RetrievalOrchestrator") as MockOrch:
            mock_orch_instance = MagicMock()
            mock_orch_instance.retrieve = AsyncMock(return_value=mock_orch_result)
            MockOrch.return_value = mock_orch_instance

            qc = _make_query_context()
            result = await memory_service.retrieve(
                user_id=qc.user_id,
                character_id="rin",
                query_context=qc,
            )

        assert isinstance(result, MemoryRetrievalResult)
        assert len(result.memories) == 1
        rm = result.memories[0]
        assert isinstance(rm, RetrievedMemory)
        assert rm.reconstructed_text == "你好像说过你叫李明"
        assert rm.uncertainty_level == 0.0  # vivid
        assert rm.voice_dna_applied == ["v1", "v2"]
        assert rm.score == 0.8

    @pytest.mark.asyncio
    async def test_reconstruct_failure_falls_back(self, memory_service):
        """If Reconstructor raises, retrieve() should fall back to raw text."""
        sm = _make_scored_memory(summary="用户在上海工作")

        mock_orch_result = MagicMock()
        mock_orch_result.memories = [sm]
        mock_orch_result.total_candidates = 1
        mock_orch_result.strategies_used = ["vector"]
        mock_orch_result.retrieval_time_ms = 5.0
        mock_orch_result.l4_included = 0
        mock_orch_result.recently_forgotten_hints = []

        mock_recon = MagicMock()
        mock_recon.reconstruct.side_effect = ValueError("anti-pattern violation")
        memory_service._get_reconstructor = MagicMock(return_value=mock_recon)

        with patch("heart.ss02_memory.retriever.orchestrator.RetrievalOrchestrator") as MockOrch:
            mock_orch_instance = MagicMock()
            mock_orch_instance.retrieve = AsyncMock(return_value=mock_orch_result)
            MockOrch.return_value = mock_orch_instance

            qc = _make_query_context()
            result = await memory_service.retrieve(
                user_id=qc.user_id,
                character_id="rin",
                query_context=qc,
            )

        assert len(result.memories) == 1
        rm = result.memories[0]
        assert rm.reconstructed_text == "用户在上海工作"  # fallback
        assert rm.voice_dna_applied == []  # empty on failure

    @pytest.mark.asyncio
    async def test_empty_orchestrator_result(self, memory_service):
        """Empty orchestrator result should return empty RetrievedMemory list."""
        mock_orch_result = MagicMock()
        mock_orch_result.memories = []
        mock_orch_result.total_candidates = 0
        mock_orch_result.strategies_used = []
        mock_orch_result.retrieval_time_ms = 0.0
        mock_orch_result.l4_included = 0
        mock_orch_result.recently_forgotten_hints = []

        memory_service._get_reconstructor = MagicMock(return_value=MagicMock())

        with patch("heart.ss02_memory.retriever.orchestrator.RetrievalOrchestrator") as MockOrch:
            mock_orch_instance = MagicMock()
            mock_orch_instance.retrieve = AsyncMock(return_value=mock_orch_result)
            MockOrch.return_value = mock_orch_instance

            qc = _make_query_context()
            result = await memory_service.retrieve(
                user_id=qc.user_id,
                character_id="rin",
                query_context=qc,
            )

        assert len(result.memories) == 0
        assert result.total_candidates == 0

    @pytest.mark.asyncio
    async def test_no_db_returns_empty(self, memory_service):
        """If no DB, retrieve() should return empty result."""
        memory_service._db = None
        qc = _make_query_context()
        result = await memory_service.retrieve(
            user_id=qc.user_id,
            character_id="rin",
            query_context=qc,
        )
        assert len(result.memories) == 0
        assert result.total_candidates == 0
