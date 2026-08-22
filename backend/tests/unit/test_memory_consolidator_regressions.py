"""Regression coverage for production consolidation pipeline interfaces."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss02_memory.models import IdentityMemory
from heart.workers.memory_consolidator import ConsolidationWorker, L4Promoter


@pytest.mark.asyncio
async def test_l4_promoter_builds_current_identity_memory_schema() -> None:
    user_id = uuid4()
    fact_id = uuid4()
    source_turn_id = uuid4()
    fact = SimpleNamespace(
        id=fact_id,
        user_id=user_id,
        character_id="rin",
        predicate="favorite_food",
        object="hotpot",
        literal_text="I love hotpot",
        raw_evidence="Hotpot is my favorite food.",
        source_turn_ids=[source_turn_id],
        confidence=0.95,
        emotional_charge=0.4,
        importance=0.9,
        is_identity_level=True,
        confirmation_count=1,
        promoted_to_l4_at=None,
        promotion_reason=None,
    )

    candidates = MagicMock()
    candidates.scalars.return_value.all.return_value = [fact]
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[candidates, no_existing])
    session.commit = AsyncMock()

    promoted = await L4Promoter.check_promotions(session, user_id, "rin")

    assert promoted == [fact_id]
    identity = session.add.call_args.args[0]
    assert isinstance(identity, IdentityMemory)
    assert identity.promoted_from_fact_id == fact_id
    assert identity.source_turn_ids == [source_turn_id]
    assert identity.disclosure_context == fact.raw_evidence
    assert identity.significance_score == 0.9
    assert identity.promotion_trigger == "explicit_emphasis"
    assert fact.promoted_to_l4_at is not None
    assert fact.promotion_reason == "explicit_emphasis"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_consolidator_delegates_batch_decay_to_decay_engine() -> None:
    session = MagicMock()
    user_id = uuid4()
    worker = ConsolidationWorker(lambda: session)
    worker.decay_engine.apply_decay_batch = AsyncMock(
        return_value={"l2_processed": 2, "l3_processed": 3}
    )

    await worker._apply_batch_decay(session, user_id, "rin")

    worker.decay_engine.apply_decay_batch.assert_awaited_once_with(session, user_id, "rin")
