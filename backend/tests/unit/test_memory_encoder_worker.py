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
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss02_memory.models import FactNode, MemoryEncodingEvent
from heart.ss02_memory.predicate_vocab import build_embedding_text
from heart.workers.memory_encoder import (
    MemoryEncoderWorker,
    build_extraction_prompt,
    validate_extraction_output,
    write_facts_to_l3,
)

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
    async def test_skip_low_confidence_facts(self, mock_db_session, sample_encoding_event):
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

        fact_ids = await write_facts_to_l3(mock_db_session, sample_encoding_event, extraction)

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


class TestFactEmbeddingOnWrite:
    """New facts must be embedded on write, else they're invisible to recall.

    Regression guard for TEST_BUGS #1/#2: write_facts_to_l3 left semantic_vector
    NULL, so the VectorRetriever (WHERE semantic_vector IS NOT NULL) never returned
    the fact and the model hallucinated on follow-up questions.
    """

    @pytest.mark.asyncio
    async def test_new_fact_gets_semantic_vector(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        fake_embedder = MagicMock()
        fake_embedder.embed_query = AsyncMock(return_value=[0.1] * 1024)

        with patch("heart.api.wiring.get_embedding_service", return_value=fake_embedder):
            await write_facts_to_l3(
                mock_db_session, sample_encoding_event, valid_extraction_output
            )

        added = [c.args[0] for c in mock_db_session.add.call_args_list]
        assert added, "no facts were added"
        assert all(f.semantic_vector == [0.1] * 1024 for f in added)
        # One embed call per created fact (2 in valid_extraction_output).
        assert fake_embedder.embed_query.await_count == 2

    @pytest.mark.asyncio
    async def test_no_embedding_service_leaves_vector_null(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("heart.api.wiring.get_embedding_service", return_value=None):
            await write_facts_to_l3(
                mock_db_session, sample_encoding_event, valid_extraction_output
            )

        added = [c.args[0] for c in mock_db_session.add.call_args_list]
        assert added
        assert all(f.semantic_vector is None for f in added)

    @pytest.mark.asyncio
    async def test_reinforce_backfills_missing_vector(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
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
            semantic_vector=None,  # pre-fix fact with no embedding
        )
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none = MagicMock(return_value=existing_fact)
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        fake_embedder = MagicMock()
        fake_embedder.embed_query = AsyncMock(return_value=[0.2] * 1024)

        with patch("heart.api.wiring.get_embedding_service", return_value=fake_embedder):
            await write_facts_to_l3(
                mock_db_session, sample_encoding_event, valid_extraction_output
            )

        assert existing_fact.semantic_vector == [0.2] * 1024


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
            mock_router.return_value.call_cheap = AsyncMock(side_effect=Exception("LLM error"))

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
            mock_router.return_value.call_cheap = AsyncMock(side_effect=Exception("LLM error"))

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
            mock_router.return_value.call_cheap = AsyncMock(return_value="not valid json")

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
            mock_router.return_value.call_cheap = AsyncMock(return_value=json.dumps(invalid_output))

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


# ============================================================
# Batch Extraction Tests (#102 follow-up)
# ============================================================


def _make_event(user_id, character_id, user_text="我养了一只猫叫年糕"):
    return MemoryEncodingEvent(
        event_id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        source_turn_id=uuid4(),
        source_user_text=user_text,
        source_assistant_text="嗯。",
        recent_context=None,
        status="llm_pending",
        retry_count=0,
        created_at=datetime.now(timezone.utc),
    )


class TestBatchExtraction:
    """Coalescing same-(user,character) turns into one extraction LLM call."""

    def test_group_events_by_user_and_character(self, mock_session_factory, user_id):
        worker = MemoryEncoderWorker(mock_session_factory)
        other_user = uuid4()
        events = [
            _make_event(user_id, "rin"),
            _make_event(user_id, "rin"),
            _make_event(other_user, "rin"),
            _make_event(user_id, "dorothy"),
        ]
        groups = worker._group_events(events)
        # (user_id,rin) x2, (other,rin) x1, (user_id,dorothy) x1
        assert len(groups) == 3
        assert len(groups[0]) == 2
        assert {(e.user_id, e.character_id) for e in groups[0]} == {(user_id, "rin")}

    def test_group_capped_at_batch_turns(self, mock_session_factory, user_id):
        worker = MemoryEncoderWorker(mock_session_factory)
        events = [_make_event(user_id, "rin") for _ in range(10)]
        with patch("heart.workers.memory_encoder.settings") as s:
            s.memory_extractor_batch_turns = 3
            groups = worker._group_events(events)
        assert len(groups) == 1
        assert len(groups[0]) == 3  # capped; overflow handled next cycle

    @pytest.mark.asyncio
    async def test_group_uses_single_llm_call(
        self, mock_session_factory, mock_db_session, user_id, character_id, valid_extraction_output
    ):
        worker = MemoryEncoderWorker(mock_session_factory)
        e1 = _make_event(user_id, character_id, "我养了一只猫叫年糕")
        e2 = _make_event(user_id, character_id, "我在苏州工作")

        reload_result = MagicMock()
        reload_result.scalars.return_value.all = MagicMock(return_value=[e1, e2])
        fact_result = MagicMock()
        fact_result.scalar_one_or_none = MagicMock(return_value=None)
        # reload + one query per extracted fact (2 facts in the fixture)
        mock_db_session.execute = AsyncMock(
            side_effect=[reload_result, fact_result, fact_result]
        )

        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            call_cheap = AsyncMock(return_value=json.dumps(valid_extraction_output))
            mock_router.return_value.call_cheap = call_cheap

            await worker._process_event_group([e1, e2])

        # Two turns → exactly ONE extraction LLM call.
        assert call_cheap.await_count == 1
        assert e1.status == "llm_done"
        assert e2.status == "llm_done"
        assert e1.llm_extraction == valid_extraction_output

    @pytest.mark.asyncio
    async def test_single_event_group_uses_per_event_path(
        self, mock_session_factory, mock_db_session, user_id, character_id, valid_extraction_output
    ):
        worker = MemoryEncoderWorker(mock_session_factory)
        e1 = _make_event(user_id, character_id)

        reload_result = MagicMock()
        reload_result.scalar_one_or_none = MagicMock(return_value=e1)
        fact_result = MagicMock()
        fact_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(
            side_effect=[reload_result, fact_result, fact_result]
        )

        with patch("heart.workers.memory_encoder.get_model_router") as mock_router:
            call_cheap = AsyncMock(return_value=json.dumps(valid_extraction_output))
            mock_router.return_value.call_cheap = call_cheap

            await worker._process_event_group([e1])

        assert call_cheap.await_count == 1
        assert e1.status == "llm_done"


# ============================================================
# Predicate Normalisation Tests (MEM-03)
# ============================================================


class TestPredicateNormalisation:
    """concerned_about must converge to worries_about row (no new row created)."""

    @pytest.mark.asyncio
    async def test_synonym_predicate_reinforces_existing_row(
        self, mock_db_session, sample_encoding_event
    ):
        """Writing concerned_about when worries_about already exists → REINFORCE."""
        existing_fact = FactNode(
            id=uuid4(),
            user_id=sample_encoding_event.user_id,
            character_id=sample_encoding_event.character_id,
            predicate="worries_about",
            subject="user",
            object="面试中的自我介绍",
            literal_text="user worries_about 面试中的自我介绍",
            raw_evidence="之前说的",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.0,
            importance=0.5,
            state="active",
            confirmation_count=1,
            last_confirmed_at=datetime.now(timezone.utc),
            semantic_vector=None,
        )

        extraction = {
            "facts": [
                {
                    "predicate": "concerned_about",  # synonym — should normalise
                    "subject": "user",
                    "object": "面试中的自我介绍",
                    "source_text": "我很担心面试",
                    "confidence": 0.9,
                    "emotional_charge": 0.5,
                    "emotional_label": "anxious",
                    "sacred_signal": False,
                }
            ],
            "emotion_peak": {"valence": -0.3, "arousal": 0.6, "label": "anxious"},
            "importance_estimate": 0.7,
            "contains_sacred": False,
            "contains_promise": False,
            "contains_first_event": False,
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_fact)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("heart.api.wiring.get_embedding_service", return_value=None):
            fact_ids = await write_facts_to_l3(mock_db_session, sample_encoding_event, extraction)

        # Must reinforce the existing row, not create a new one
        assert len(fact_ids) == 1
        assert fact_ids[0] == existing_fact.id
        # No new FactNode should have been added
        assert mock_db_session.add.call_count == 0
        # Confirmation count incremented
        assert existing_fact.confirmation_count == 2

    @pytest.mark.asyncio
    async def test_new_synonym_predicate_stored_as_canonical(
        self, mock_db_session, sample_encoding_event
    ):
        """When no existing row, concerned_about is stored as worries_about."""
        extraction = {
            "facts": [
                {
                    "predicate": "concerned_about",
                    "subject": "user",
                    "object": "明天的考试",
                    "source_text": "我很担心明天的考试",
                    "confidence": 0.85,
                    "emotional_charge": 0.4,
                    "emotional_label": "anxious",
                    "sacred_signal": False,
                }
            ],
            "emotion_peak": {"valence": -0.2, "arousal": 0.5, "label": "anxious"},
            "importance_estimate": 0.6,
            "contains_sacred": False,
            "contains_promise": False,
            "contains_first_event": False,
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("heart.api.wiring.get_embedding_service", return_value=None):
            fact_ids = await write_facts_to_l3(mock_db_session, sample_encoding_event, extraction)

        assert len(fact_ids) == 1
        added = [c.args[0] for c in mock_db_session.add.call_args_list]
        assert len(added) == 1
        assert added[0].predicate == "worries_about"  # canonical, not raw


# ============================================================
# Chinese-Aligned Embedding Text Tests (MEM-01)
# ============================================================


class TestChineseEmbeddingText:
    """CREATE and REINFORCE must embed Chinese-gloss text, not raw literal_text."""

    @pytest.mark.asyncio
    async def test_create_embeds_chinese_text(
        self, mock_db_session, sample_encoding_event
    ):
        """Embedder receives build_embedding_text output (contains Chinese gloss)."""
        extraction = {
            "facts": [
                {
                    "predicate": "has_pet",
                    "subject": "user",
                    "object": "一只叫年糕的猫",
                    "source_text": "我养了一只叫年糕的猫",
                    "confidence": 0.95,
                    "emotional_charge": 0.4,
                    "emotional_label": "fond",
                    "sacred_signal": False,
                }
            ],
            "emotion_peak": {"valence": 0.5, "arousal": 0.3, "label": "happy"},
            "importance_estimate": 0.6,
            "contains_sacred": False,
            "contains_promise": False,
            "contains_first_event": False,
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        embedded_texts: list[str] = []

        async def capture_embed(text: str):
            embedded_texts.append(text)
            return [0.1] * 1024

        fake_embedder = MagicMock()
        fake_embedder.embed_query = AsyncMock(side_effect=capture_embed)

        with patch("heart.api.wiring.get_embedding_service", return_value=fake_embedder):
            await write_facts_to_l3(mock_db_session, sample_encoding_event, extraction)

        assert embedded_texts, "embedder was never called"
        embed_text = embedded_texts[0]
        expected = build_embedding_text("user", "has_pet", "一只叫年糕的猫")
        assert embed_text == expected
        assert "养了宠物" in embed_text
        assert "has_pet" not in embed_text

    @pytest.mark.asyncio
    async def test_reinforce_backfill_embeds_chinese_text(
        self, mock_db_session, sample_encoding_event, valid_extraction_output
    ):
        """REINFORCE path backfills semantic_vector using Chinese-aligned text."""
        existing_fact = FactNode(
            id=uuid4(),
            user_id=sample_encoding_event.user_id,
            character_id=sample_encoding_event.character_id,
            predicate="has_pet",
            subject="user",
            object="一只叫老铁的黑猫",
            literal_text="user has_pet 一只叫老铁的黑猫",
            raw_evidence="之前说的",
            source_turn_ids=[uuid4()],
            confidence=0.8,
            emotional_charge=0.0,
            importance=0.5,
            state="active",
            confirmation_count=1,
            last_confirmed_at=datetime.now(timezone.utc),
            semantic_vector=None,
        )

        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none = MagicMock(return_value=existing_fact)
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        embedded_texts: list[str] = []

        async def capture_embed(text: str):
            embedded_texts.append(text)
            return [0.2] * 1024

        fake_embedder = MagicMock()
        fake_embedder.embed_query = AsyncMock(side_effect=capture_embed)

        with patch("heart.api.wiring.get_embedding_service", return_value=fake_embedder):
            await write_facts_to_l3(mock_db_session, sample_encoding_event, valid_extraction_output)

        assert embedded_texts, "embedder was never called"
        expected = build_embedding_text("user", "has_pet", "一只叫老铁的黑猫")
        assert embedded_texts[0] == expected
        assert "养了宠物" in embedded_texts[0]
        assert existing_fact.semantic_vector == [0.2] * 1024
