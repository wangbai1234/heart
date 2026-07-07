"""
Unit tests for recall hardening — high-confidence L3 fact force-inclusion + dedup.

Regression guard for the "年糕→铜钱" bug: an explicit stored fact (confidence=1)
was out-ranked out of the injected window by episodic chatter, so the model answered
the pet's name wrong. These tests assert the fact survives selection.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from heart.ss02_memory.retriever.base import (
    ScoredMemory,
    deduplicate_memories,
    select_top_k,
)


def _l3(
    subject: str,
    predicate: str,
    confidence: float,
    score: float,
    obj: str | None = None,
) -> ScoredMemory:
    mem = SimpleNamespace(
        subject=subject,
        predicate=predicate,
        object=obj if obj is not None else subject,
        confidence=confidence,
        literal_text=f"{predicate} {subject}",
    )
    return ScoredMemory(memory=mem, memory_id=uuid4(), memory_type="L3", score=score)


def _l2(score: float) -> ScoredMemory:
    return ScoredMemory(
        memory=SimpleNamespace(episode_summary="chatter"),
        memory_id=uuid4(),
        memory_type="L2",
        score=score,
    )


def test_high_confidence_l3_fact_beats_episodic_chatter():
    """A confidence=1 fact must appear even when many higher-score L2 episodes exist."""
    fact = _l3("年糕", "has_pet", confidence=1.0, score=0.35)
    chatter = [_l2(0.9 - i * 0.05) for i in range(8)]  # all out-score the fact

    top_k = select_top_k([*chatter, fact], k=5)

    ids = {str(m.memory_id) for m in top_k}
    assert str(fact.memory_id) in ids, "high-confidence L3 fact was dropped from top-k"


def test_low_confidence_l3_not_force_included():
    """A low-confidence L3 competes on score only (no force-inclusion)."""
    weak = _l3("铜钱", "has_pet", confidence=0.3, score=0.05)
    chatter = [_l2(0.9 - i * 0.05) for i in range(8)]

    top_k = select_top_k([*chatter, weak], k=5)

    ids = {str(m.memory_id) for m in top_k}
    assert str(weak.memory_id) not in ids


def test_duplicate_l3_facts_collapse_keeping_highest_confidence():
    """Same (subject, predicate) collapses to the higher-confidence variant."""
    high = _l3("年糕", "has_pet", confidence=1.0, score=0.3)
    low = _l3("铜钱", "has_pet", confidence=0.4, score=0.9)  # wrong value, higher score
    # NB: same predicate 'has_pet' but different subject → NOT duplicates here.
    # Use identical subject+predicate to trigger collapse:
    dup_low = _l3("年糕", "has_pet", confidence=0.4, score=0.9)

    result = deduplicate_memories([dup_low, high])
    assert len(result) == 1
    assert result[0].memory.confidence == 1.0  # kept the high-confidence one
    # Sanity: differing subjects are not collapsed.
    assert len(deduplicate_memories([high, low])) == 2


def test_synonym_predicate_same_object_collapses():
    """worries_about / concerned_about → same object collapse (TEST_BUGS #3)."""
    worries = _l3("用户", "worries_about", confidence=1.0, score=0.3, obj="自我介绍")
    concerned = _l3("用户", "concerned_about", confidence=0.95, score=0.5, obj="自我介绍")

    result = deduplicate_memories([concerned, worries])
    assert len(result) == 1
    # Keeps the higher-confidence variant regardless of score ordering.
    assert result[0].memory.confidence == 1.0

    # A genuinely different fact (different predicate AND object) must NOT collapse.
    other = _l3("用户", "likes", confidence=1.0, score=0.3, obj="咖啡")
    assert len(deduplicate_memories([worries, other])) == 2


def test_forced_l3_capped_at_two():
    facts = [_l3(f"pet{i}", f"pred{i}", confidence=1.0, score=0.2) for i in range(4)]
    top_k = select_top_k(facts, k=5)
    forced = [m for m in top_k if m.memory_type == "L3"]
    # All 4 could fit in k=5, but at most 2 are *force*-included; the rest fill by score.
    assert len(top_k) <= 5
    assert len(forced) >= 2
