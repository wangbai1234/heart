"""
Unit tests for Memory Encoder Worker (SS02 §3.4 阶段 2).

Tests:
- LLM response mocking
- JSON parsing (valid, malformed, missing fields)
- Idempotency (process same event twice → only 1 fact written)
- Retry logic (max 2 retries)
- Fact deduplication (reinforcement)
- Schema validation
- Performance: timeout handling

Author: 心屿团队
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from heart.workers.memory_encoder import (
    MemoryEncoderWorker,
    build_extraction_prompt,
    validate_extraction_output,
    write_facts_to_l3,
)
from heart.ss02_memory.models import FactNode, MemoryEncodingEvent
from heart.prompts.memory_extraction import MEMORY_EXTRACTION_PROMPT


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def character_id():
    """Test character ID."""
    return "rin"


@pytest.fixture
def event_id():
    """Test event UUID."""
    return uuid4()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()

    # Mock execute to return a mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value.all = MagicMock(return_value=[])

    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.add = MagicMock()

    return session


@pytest.fixture
def mock_session_factory(mock_db_session):
    """Mock session factory."""

    # Make session an async context manager
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=None)

    # Return a callable that returns the session (not a coroutine)
    def factory():
        return mock_db_session

    return factory


@pytest.fixture
def valid_extraction_output():
    """Valid LLM extraction output matching schema."""
    return {
        "facts": [
            {
                "predicate": "has_pet",
                "subject": "user",
                "object": "一只叫老铁的黑猫",
                "source_text": "我养了一只叫老铁的黑猫",
                "confidence": 0.95,
                "emotional_charge": 0.4,
                "emotional_label": "fond",
                "sacred_signal": False,
            },
            {
                "predicate": "occupation",
                "subject": "user",
                "object": "程序员",
                "source_text": "我是程序员",
                "confidence": 0.9,
                "emotional_charge": 0.0,
                "emotional_label": "neutral",
                "sacred_signal": True,
            },
        ],
        "emotion_peak": {
            "valence": 0.3,
            "arousal": 0.4,
            "label": "calm",
        },
        "importance_estimate": 0.6,
        "contains_sacred": True,
        "contains_promise": False,
        "contains_first_event": False,
    }


@pytest.fixture
def sample_encoding_event(user_id, character_id, event_id):
    """Sample encoding event."""
    return MemoryEncodingEvent(
        event_id=event_id,
        user_id=user_id,
        character_id=character_id,
        source_turn_id=uuid4(),
        source_user_text="我养了一只叫老铁的黑猫，我是程序员",
        source_assistant_text="你的猫一定很可爱！",
        recent_context={
            "turns": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好呀"},
            ]
        },
        status="llm_pending",
        retry_count=0,
        created_at=datetime.now(timezone.utc),
    )


# ============================================================
# Schema Validation Tests
# ============================================================


class TestSchemaValidation:
    """Tests for extraction output schema validation."""

    def test_valid_schema(self, valid_extraction_output):
        """Should pass validation for valid output."""
        is_valid, error = validate_extraction_output(valid_extraction_output)
        assert is_valid
        assert error is None

    def test_missing_top_level_field(self, valid_extraction_output):
        """Should fail if top-level field missing."""
        data = valid_extraction_output.copy()
        del data["emotion_peak"]

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "emotion_peak" in error

    def test_facts_not_list(self, valid_extraction_output):
        """Should fail if facts is not a list."""
        data = valid_extraction_output.copy()
        data["facts"] = "not a list"

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "must be a list" in error

    def test_fact_missing_field(self, valid_extraction_output):
        """Should fail if fact missing required field."""
        data = valid_extraction_output.copy()
        del data["facts"][0]["predicate"]

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "predicate" in error

    def test_confidence_out_of_range(self, valid_extraction_output):
        """Should fail if confidence not in [0, 1]."""
        data = valid_extraction_output.copy()
        data["facts"][0]["confidence"] = 1.5

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "confidence" in error
        assert "[0, 1]" in error

    def test_importance_out_of_range(self, valid_extraction_output):
        """Should fail if importance_estimate not in [0, 1]."""
        data = valid_extraction_output.copy()
        data["importance_estimate"] = -0.5

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "importance_estimate" in error

    def test_emotion_peak_missing_field(self, valid_extraction_output):
        """Should fail if emotion_peak missing field."""
        data = valid_extraction_output.copy()
        del data["emotion_peak"]["valence"]

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "valence" in error

    def test_boolean_flag_not_bool(self, valid_extraction_output):
        """Should fail if boolean flag is not bool."""
        data = valid_extraction_output.copy()
        data["contains_sacred"] = "yes"

        is_valid, error = validate_extraction_output(data)
        assert not is_valid
        assert "must be a boolean" in error


# ============================================================
# Prompt Builder Tests
# ============================================================


class TestPromptBuilder:
    """Tests for extraction prompt building."""

    def test_build_prompt_with_context(self):
        """Should build prompt with recent context."""
        prompt = build_extraction_prompt(
            user_text="我养了一只猫",
            assistant_text="好可爱",
            character_id="rin",
            recent_context={
                "turns": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "嗨"},
                ]
            },
        )

        assert "我养了一只猫" in prompt
        assert "好可爱" in prompt
        assert "rin" in prompt
        assert "你好" in prompt
        assert "嗨" in prompt

    def test_build_prompt_without_context(self):
        """Should build prompt without context."""
        prompt = build_extraction_prompt(
            user_text="我是程序员",
            assistant_text="很厉害",
            character_id="dorothy",
            recent_context=None,
        )

        assert "我是程序员" in prompt
        assert "很厉害" in prompt
        assert "dorothy" in prompt
        assert "(无)" in prompt

    def test_prompt_matches_template(self):
        """Should match MEMORY_EXTRACTION_PROMPT template."""
        prompt = build_extraction_prompt(
            user_text="test",
            assistant_text="response",
            character_id="rin",
        )

        # Check key sections exist
        assert "你是一个记忆提取系统" in prompt
        assert "对话上下文" in prompt
        assert "提取任务" in prompt
        assert "输出格式" in prompt
        assert "严格规则" in prompt


# ============================================================
# Fact Writing Tests
# ============================================================


class TestFactWriting:
    """Tests for writing facts to L3."""

    @pytest.mark.asyncio
    async def test_write_new_facts(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
        """Should write new facts to database."""
        # Mock no existing facts
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        fact_ids = await write_facts_to_l3(
            mock_db_session, sample_encoding_event, valid_extraction_output
        )

        # Should create 2 facts (from valid_extraction_output)
        assert len(fact_ids) == 2

        # Check session.add was called for each fact
        assert mock_db_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_skip_low_confidence_facts(
        self, mock_db_session, sample_encoding_event
    ):
        """Should skip facts with confidence < 0.7."""
        extraction = {
            "facts": [
                {
                    "predicate": "has_pet",
                    "subject": "user",
                    "object": "猫",
                    "source_text": "我有猫",
                    "confidence": 0.5,  # Too low
                    "emotional_charge": 0.0,
                    "emotional_label": "neutral",
                    "sacred_signal": False,
                }
            ],
            "emotion_peak": {"valence": 0, "arousal": 0, "label": "neutral"},
            "importance_estimate": 0.5,
            "contains_sacred": False,
            "contains_promise": False,
            "contains_first_event": False,
        }

        fact_ids = await write_facts_to_l3(
            mock_db_session, sample_encoding_event, extraction
        )

        # Should skip low-confidence fact
        assert len(fact_ids) == 0
        assert mock_db_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_reinforce_existing_fact(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
        """Should reinforce existing fact instead of creating duplicate."""
        # Mock existing fact for first predicate, none for second
        existing_fact = FactNode(
            id=uuid4(),
            user_id=sample_encoding_event.user_id,
            character_id=sample_encoding_event.character_id,
            predicate="has_pet",
            subject="user",
            object="猫",
            literal_text="user has_pet 猫",
            raw_evidence="之前说的",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.0,
            importance=0.5,
            state="active",
            confirmation_count=1,
            last_confirmed_at=datetime.now(timezone.utc),
        )

        # First call returns existing fact, second returns None
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none = MagicMock(return_value=existing_fact)

        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none = MagicMock(return_value=None)

        mock_db_session.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        fact_ids = await write_facts_to_l3(
            mock_db_session, sample_encoding_event, valid_extraction_output
        )

        # Should return 2 fact IDs (1 reinforced, 1 new)
        assert len(fact_ids) == 2

        # Should increment confirmation_count on existing fact
        assert existing_fact.confirmation_count == 2

        # Should update confidence to max
        assert existing_fact.confidence == 0.95  # from valid_extraction_output

        # Should add turn to source_turn_ids
        assert sample_encoding_event.source_turn_id in existing_fact.source_turn_ids


# ============================================================
# Worker Tests
# ============================================================


class TestMemoryEncoderWorker:
    """Tests for MemoryEncoderWorker."""

    @pytest.mark.asyncio
    async def test_process_event_success(
        self,
        mock_session_factory,
        mock_db_session,
        sample_encoding_event,
        valid_extraction_output,
    ):
        """Should process event successfully."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mock fetch event
        mock_result_reload = MagicMock()
        mock_result_reload.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)

        mock_result_fact_1 = MagicMock()
        mock_result_fact_1.scalar_one_or_none = MagicMock(return_value=None)

        mock_result_fact_2 = MagicMock()
        mock_result_fact_2.scalar_one_or_none = MagicMock(return_value=None)

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_result_reload, mock_result_fact_1, mock_result_fact_2]
        )

        # Mock LLM call
        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = AsyncMock(
                return_value=json.dumps(valid_extraction_output)
            )

            await worker._process_event(sample_encoding_event)

        # Check event status updated
        assert sample_encoding_event.status == "llm_done"
        assert sample_encoding_event.llm_extraction == valid_extraction_output
        assert sample_encoding_event.llm_completed_at is not None

    @pytest.mark.asyncio
    async def test_process_event_idempotency(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should skip already-processed event (idempotency)."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mark event as already done
        sample_encoding_event.status = "llm_done"

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        await worker._process_event(sample_encoding_event)

        # Should not call LLM or update anything
        assert mock_db_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_process_event_retry_on_failure(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should retry on failure (up to max retries)."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock LLM failure
        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = AsyncMock(
                side_effect=Exception("LLM error")
            )

            with pytest.raises(Exception, match="LLM error"):
                await worker._process_event(sample_encoding_event)

        # Check retry count incremented
        assert sample_encoding_event.retry_count == 1

        # Status should still be llm_pending (will retry)
        # (not "failed" until max retries)

    @pytest.mark.asyncio
    async def test_process_event_max_retries_exceeded(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should mark as failed after max retries."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Set retry count to max - 1
        sample_encoding_event.retry_count = 1  # MAX_RETRIES = 2

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock LLM failure
        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = AsyncMock(
                side_effect=Exception("LLM error")
            )

            with pytest.raises(Exception, match="LLM error"):
                await worker._process_event(sample_encoding_event)

        # Check status marked as failed
        assert sample_encoding_event.status == "failed"
        assert sample_encoding_event.failed_at is not None
        assert sample_encoding_event.failure_reason == "LLM error"
        assert sample_encoding_event.retry_count == 2

    @pytest.mark.asyncio
    async def test_malformed_json_handling(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should handle malformed JSON from LLM."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock LLM returning invalid JSON
        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = AsyncMock(
                return_value="not valid json"
            )

            with pytest.raises(ValueError, match="Invalid JSON"):
                await worker._process_event(sample_encoding_event)

        # Should increment retry count
        assert sample_encoding_event.retry_count == 1

    @pytest.mark.asyncio
    async def test_invalid_schema_handling(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should handle invalid schema from LLM."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock LLM returning JSON with invalid schema
        invalid_output = {
            "facts": [],
            # Missing required fields
        }

        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = AsyncMock(
                return_value=json.dumps(invalid_output)
            )

            with pytest.raises(ValueError, match="Invalid extraction schema"):
                await worker._process_event(sample_encoding_event)

    @pytest.mark.asyncio
    async def test_llm_timeout_handling(
        self, mock_session_factory, mock_db_session, sample_encoding_event
    ):
        """Should handle LLM timeout."""
        worker = MemoryEncoderWorker(mock_session_factory)

        # Mock fetch event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_encoding_event)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock LLM timeout
        import asyncio

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(20)  # Longer than timeout

        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            mock_router.return_value.call_cheap = slow_llm

            with pytest.raises(TimeoutError, match="timed out"):
                await worker._process_event(sample_encoding_event)
