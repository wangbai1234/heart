"""
Unit: MemoryService.promote_to_l4 — L3 fact promotion to L4 Identity Memory.

Verifies T2-01: promote_to_l4 creates IdentityMemory from high-importance FactNode.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss02_memory.models import FactNode, IdentityMemory
from heart.ss02_memory.service import MemoryService


class TestPromoteToL4:
    """Verify L3 → L4 promotion logic."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock DB session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create MemoryService with mock DB."""
        return MemoryService(db_session=mock_db_session)

    @pytest.mark.asyncio
    async def test_promote_creates_identity_memory(self, service, mock_db_session):
        """promote_to_l4 should create IdentityMemory from high-importance fact."""
        fact_id = uuid4()
        user_id = uuid4()

        # Create a mock fact with high importance
        mock_fact = MagicMock(spec=FactNode)
        mock_fact.id = fact_id
        mock_fact.user_id = user_id
        mock_fact.character_id = "rin"
        mock_fact.predicate = "妈妈"
        mock_fact.object = "王梅"
        mock_fact.literal_text = "妈妈 王梅"
        mock_fact.raw_evidence = "我妈妈叫王梅"
        mock_fact.source_turn_ids = [uuid4()]
        mock_fact.confidence = 0.9
        mock_fact.importance = 0.9
        mock_fact.emotional_charge = 0.5

        # Mock DB execute to return fact
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_fact)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock the "already promoted" check to return None
        def side_effect(stmt):
            # First call returns fact, second call returns None (not already promoted)
            result = MagicMock()
            if mock_db_session.execute.call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=mock_fact)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        mock_db_session.execute = AsyncMock(side_effect=side_effect)

        # Promote
        identity = await service.promote_to_l4(fact_id, "explicit_emphasis")

        # Verify
        assert mock_db_session.add.called
        assert mock_db_session.flush.called
        added_identity = mock_db_session.add.call_args[0][0]
        assert isinstance(added_identity, IdentityMemory)
        assert added_identity.user_id == user_id
        assert added_identity.character_id == "rin"
        assert added_identity.key == "妈妈"
        assert added_identity.value == "王梅"
        assert added_identity.sacred_reason == "explicit_emphasis"
        assert added_identity.significance_score == 0.9

    @pytest.mark.asyncio
    async def test_promote_rejects_low_importance(self, service, mock_db_session):
        """promote_to_l4 should reject facts with importance < 0.85."""
        fact_id = uuid4()

        mock_fact = MagicMock(spec=FactNode)
        mock_fact.id = fact_id
        mock_fact.importance = 0.5  # Below threshold

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_fact)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="importance.*< 0.85"):
            await service.promote_to_l4(fact_id, "test_reason")

    @pytest.mark.asyncio
    async def test_promote_rejects_missing_fact(self, service, mock_db_session):
        """promote_to_l4 should reject non-existent facts."""
        fact_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await service.promote_to_l4(fact_id, "test_reason")

    @pytest.mark.asyncio
    async def test_promote_requires_db_session(self):
        """promote_to_l4 should require db_session."""
        service = MemoryService(db_session=None)

        with pytest.raises(RuntimeError, match="requires db_session"):
            await service.promote_to_l4(uuid4(), "test_reason")

    def test_derive_l4_category_family(self, service):
        """Should derive 'family' category for family-related predicates."""
        assert service._derive_l4_category("妈妈") == "family"
        assert service._derive_l4_category("爸爸") == "family"

    def test_derive_l4_category_default(self, service):
        """Should derive 'user_identity' for unknown predicates."""
        assert service._derive_l4_category("unknown_predicate") == "user_identity"
