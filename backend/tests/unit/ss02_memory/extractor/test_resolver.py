"""
Unit tests for SS02 Memory LLM Extractor — Resolver.

Covers every row of the decision table:
  - rhetoric/question/hypothetical → REJECT
  - negation + match → SOFT_DELETE
  - negation + no match → REJECT
  - disclosure + no match → CREATE
  - disclosure + match + same value → REINFORCE
  - disclosure + match + different value + conf >= 0.7 → SUPERSEDE
  - disclosure + match + different value + conf < 0.7 → CONFLICT_DEFER

Also covers confidence_ewma update math.

Author: 心屿团队
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss02_memory.extractor.resolver import (
    DecisionType,
    Resolver,
    _compute_ewma,
    _values_match,
    is_implausible_identity_value,
)
from heart.ss02_memory.extractor.types import (
    Attribute,
    EntityType,
    ExtractionCandidate,
    ExtractionEnvelope,
    Kind,
    Operation,
    Window,
)
from heart.ss02_memory.models import FactNode

# ── Helpers ────────────────────────────────────────────────────


def _make_candidate(
    entity_type: EntityType = EntityType.SELF,
    attribute: Attribute = Attribute.NAME,
    value: str = "张三",
    entity_ref: str | None = None,
    source_turns: list[int] | None = None,
    confidence: float = 0.9,
    kind: Kind = Kind.DISCLOSURE,
    operation: Operation = Operation.CREATE,
    reasoning: str = "T0: user said their name",
) -> ExtractionCandidate:
    return ExtractionCandidate(
        entity_type=entity_type,
        attribute=attribute,
        value=value,
        entity_ref=entity_ref,
        source_turns=source_turns or [0],
        confidence=confidence,
        kind=kind,
        operation=operation,
        reasoning=reasoning,
    )


def _make_envelope(
    candidates: list[ExtractionCandidate] | None = None,
) -> ExtractionEnvelope:
    return ExtractionEnvelope(
        extractor_run_id=uuid4(),
        model="test-model",
        prompt_version="1.0.0",
        schema_version="1.0.0",
        window=Window(turn_ids=[0, 1, 2], size=3),
        candidates=candidates or [],
        dropped_signals=[],
    )


def _make_fact_node(
    user_id=None,
    subject="self",
    predicate="name",
    object_val="张三",
    confidence_ewma=0.85,
    is_active=True,
    do_not_recall=False,
) -> FactNode:
    fact = MagicMock(spec=FactNode)
    fact.id = uuid4()
    fact.user_id = user_id or uuid4()
    fact.subject = subject
    fact.predicate = predicate
    fact.object = object_val
    fact.confidence = 0.8
    fact.confidence_ewma = confidence_ewma
    fact.mention_count = 2
    fact.is_active = is_active
    fact.do_not_recall = do_not_recall
    fact.source_turns = [0]
    return fact


def _mock_session_with_fact(fact: FactNode | None) -> AsyncMock:
    """Create a mock session that returns the given fact from scalar_one_or_none."""
    session = AsyncMock()
    # Use MagicMock (not AsyncMock) for the result — scalar_one_or_none is sync
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fact
    session.execute.return_value = mock_result
    return session


# ── Decision table tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_rhetoric():
    """kind=rhetoric → REJECT."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(kind=Kind.RHETORIC, reasoning="T0: metaphor, not literal")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.REJECT
    assert "rhetoric" in decisions[0].reason


@pytest.mark.asyncio
async def test_reject_question():
    """kind=question → REJECT."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(kind=Kind.QUESTION, reasoning="T0: asking a question")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.REJECT
    assert "question" in decisions[0].reason


@pytest.mark.asyncio
async def test_reject_hypothetical():
    """kind=hypothetical → REJECT."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(kind=Kind.HYPOTHETICAL, reasoning="T0: hypothetical scenario")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.REJECT
    assert "hypothetical" in decisions[0].reason


@pytest.mark.asyncio
async def test_soft_delete_negation_with_match():
    """kind=negation + matching L3 exists → SOFT_DELETE."""
    fact = _make_fact_node()
    session = _mock_session_with_fact(fact)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        kind=Kind.NEGATION,
        operation=Operation.SOFT_DELETE,
        reasoning="T0: user denied having a pet",
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.SOFT_DELETE
    assert decisions[0].matched_fact is fact


@pytest.mark.asyncio
async def test_reject_negation_no_match():
    """kind=negation + no matching L3 → REJECT."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        kind=Kind.NEGATION,
        operation=Operation.SOFT_DELETE,
        reasoning="T0: user denied but no prior fact",
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.REJECT
    assert "no matching" in decisions[0].reason


@pytest.mark.asyncio
async def test_create_disclosure_no_match():
    """kind=disclosure + no matching L3 → CREATE."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(reasoning="T0: user disclosed their name")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.CREATE
    assert decisions[0].matched_fact is None


@pytest.mark.asyncio
async def test_reinforce_disclosure_same_value():
    """kind=disclosure + match + same value → REINFORCE."""
    fact = _make_fact_node(object_val="张三")
    session = _mock_session_with_fact(fact)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(value="张三", confidence=0.9, reasoning="T1: confirmed name")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.REINFORCE
    assert decisions[0].matched_fact is fact
    assert decisions[0].new_confidence_ewma is not None


@pytest.mark.asyncio
async def test_supersede_disclosure_different_value_high_confidence():
    """kind=disclosure + match + different value + conf >= 0.7 → SUPERSEDE."""
    fact = _make_fact_node(object_val="北京")
    session = _mock_session_with_fact(fact)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        attribute=Attribute.LOCATION_RESIDENCE,
        value="上海",
        confidence=0.85,
        reasoning="T2: user moved to Shanghai",
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.SUPERSEDE
    assert decisions[0].matched_fact is fact


@pytest.mark.asyncio
async def test_conflict_defer_different_value_low_confidence():
    """kind=disclosure + match + different value + conf < 0.7 → CONFLICT_DEFER."""
    fact = _make_fact_node(object_val="北京")
    session = _mock_session_with_fact(fact)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        attribute=Attribute.LOCATION_RESIDENCE,
        value="上海",
        confidence=0.5,
        reasoning="T2: maybe moved, uncertain",
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.CONFLICT_DEFER
    assert "0.50" in decisions[0].reason


# ── Multiple candidates ───────────────────────────────────────


@pytest.mark.asyncio
async def test_mixed_candidates():
    """Envelope with multiple candidates produces correct decisions."""
    fact_pet = _make_fact_node(subject="cat#1", predicate="name", object_val="妙妙")

    # Always return the pet fact for any DB lookup
    session = _mock_session_with_fact(fact_pet)

    resolver = Resolver(session, uuid4())
    candidates = [
        _make_candidate(kind=Kind.RHETORIC, reasoning="T0: joke"),
        _make_candidate(
            entity_type=EntityType.PET,
            attribute=Attribute.NAME,
            value="妙妙",
            entity_ref="cat#1",
            reasoning="T1: confirmed cat name",
        ),
    ]
    envelope = _make_envelope(candidates)
    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 2
    assert decisions[0].decision == DecisionType.REJECT
    assert decisions[1].decision == DecisionType.REINFORCE


# ── EWMA math ─────────────────────────────────────────────────


def test_compute_ewma_basic():
    """EWMA update: 0.7 * old + 0.3 * new."""
    result = _compute_ewma(0.8, 0.9)
    expected = 0.7 * 0.8 + 0.3 * 0.9
    assert abs(result - expected) < 1e-10


def test_compute_ewma_from_low():
    """EWMA from low old value."""
    result = _compute_ewma(0.3, 0.9)
    expected = 0.7 * 0.3 + 0.3 * 0.9
    assert abs(result - expected) < 1e-10


def test_compute_ewma_from_high():
    """EWMA from high old value."""
    result = _compute_ewma(0.95, 0.5)
    expected = 0.7 * 0.95 + 0.3 * 0.5
    assert abs(result - expected) < 1e-10


def test_compute_ewma_identity():
    """EWMA with same old and new stays the same."""
    result = _compute_ewma(0.7, 0.7)
    assert abs(result - 0.7) < 1e-10


def test_compute_ewma_extremes():
    """EWMA with extreme values."""
    assert abs(_compute_ewma(0.0, 1.0) - 0.3) < 1e-10
    assert abs(_compute_ewma(1.0, 0.0) - 0.7) < 1e-10


# ── Value matching ────────────────────────────────────────────


def test_values_match_exact():
    assert _values_match("张三", "张三") is True


def test_values_match_case_insensitive():
    assert _values_match("Hello", "hello") is True


def test_values_match_trimmed():
    assert _values_match(" 张三 ", "张三") is True


def test_values_no_match():
    assert _values_match("张三", "李四") is False


# ── Edge cases ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_candidates():
    """Empty candidates list returns empty decisions."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    envelope = _make_envelope([])

    decisions = await resolver.resolve(envelope)

    assert len(decisions) == 0


@pytest.mark.asyncio
async def test_reinforce_updates_ewma_correctly():
    """REINFORCE decision includes correctly computed EWMA."""
    fact = _make_fact_node(confidence_ewma=0.6)
    session = _mock_session_with_fact(fact)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(value="张三", confidence=0.95, reasoning="T1: confirmed")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    expected_ewma = 0.7 * 0.6 + 0.3 * 0.95
    assert decisions[0].new_confidence_ewma is not None
    assert abs(decisions[0].new_confidence_ewma - expected_ewma) < 1e-10


@pytest.mark.asyncio
async def test_inactive_fact_not_matched():
    """is_active=False facts should not be matched."""
    session = _mock_session_with_fact(None)  # query returns None for inactive
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(reasoning="T0: new disclosure")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert decisions[0].decision == DecisionType.CREATE


@pytest.mark.asyncio
async def test_do_not_recall_fact_not_matched():
    """do_not_recall=True facts should not be matched."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(reasoning="T0: re-disclosure after prior soft delete")
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert decisions[0].decision == DecisionType.CREATE


# ── Defensive: implausible identity values (P0-3, "什么吗" bug) ──


@pytest.mark.asyncio
async def test_reject_disclosure_interrogative_name():
    """An LLM-mis-tagged interrogative disclosure (name="什么吗") → REJECT, no CREATE."""
    session = _mock_session_with_fact(None)  # no matching L3
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        attribute=Attribute.NAME,
        value="什么吗",
        kind=Kind.DISCLOSURE,
        reasoning="T0: LLM wrongly tagged '我叫什么吗' as a name disclosure",
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert decisions[0].decision == DecisionType.REJECT
    assert "implausible identity value" in decisions[0].reason


@pytest.mark.asyncio
async def test_valid_name_still_creates():
    """A legitimate name disclosure is unaffected by the guard → CREATE."""
    session = _mock_session_with_fact(None)
    resolver = Resolver(session, uuid4())
    candidate = _make_candidate(
        attribute=Attribute.NAME, value="张三", kind=Kind.DISCLOSURE, reasoning="T0: 我叫张三"
    )
    envelope = _make_envelope([candidate])

    decisions = await resolver.resolve(envelope)

    assert decisions[0].decision == DecisionType.CREATE


def test_is_implausible_identity_value_flags_interrogatives():
    assert is_implausible_identity_value(Attribute.NAME, "什么吗") is True
    assert is_implausible_identity_value(Attribute.NAME, "谁") is True
    assert is_implausible_identity_value(Attribute.NICKNAME, "啥呢") is True
    assert is_implausible_identity_value(Attribute.NAME, "  ") is True
    assert is_implausible_identity_value(Attribute.NAME, "我") is True


def test_is_implausible_identity_value_allows_real_names():
    assert is_implausible_identity_value(Attribute.NAME, "张三") is False
    assert is_implausible_identity_value(Attribute.NICKNAME, "年糕") is False
    assert is_implausible_identity_value(Attribute.NAME, "Alice") is False


def test_is_implausible_identity_value_scoped_to_identity_attrs():
    # Non-identity attributes are never flagged (a hobby/dislike can be anything).
    assert is_implausible_identity_value(Attribute.HOBBY, "什么") is False
    assert is_implausible_identity_value(Attribute.DISLIKE, "谁") is False
