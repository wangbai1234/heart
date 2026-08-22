"""Mask identity precedence over durable L3/L4 user-name memories."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from heart.ss05_composer.service import ComposerService, CompositionContext


def _memory(
    text: str,
    memory_type: str,
    source_metadata: dict[str, str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        memory_id=uuid4(),
        memory_type=memory_type,
        reconstructed_text=text,
        score=0.95,
        uncertainty_level=0.0,
        source_metadata=source_metadata or {},
    )


class _MemoryServiceStub:
    def __init__(self, memories: list[SimpleNamespace]) -> None:
        self.memories = memories

    async def retrieve(self, **_kwargs):
        return SimpleNamespace(
            memories=self.memories,
            recently_forgotten_hints=[SimpleNamespace(hint_text="好像和王白这个称呼有关")],
            l4_included=True,
        )


def _context(message: str, *, masked: bool) -> CompositionContext:
    return CompositionContext(
        user_id=uuid4(),
        character_id="shiyan",
        turn_id=uuid4(),
        user_message=message,
        user_mask={"name": "时衍", "gender": "male", "bio": "以时衍的身份相处。"}
        if masked
        else None,
    )


def _service() -> ComposerService:
    service = ComposerService.__new__(ComposerService)
    service._memory_service = _MemoryServiceStub(
        [
            _memory(
                "用户的名字是王白",
                "L4",
                {"category": "user_identity", "key": "has_name"},
            ),
            _memory(
                "用户昵称是小白",
                "L3",
                {"subject": "self", "predicate": "has_nickname"},
            ),
            _memory("用户的生日是五月十日", "L4", {"category": "personal", "key": "birthday"}),
            _memory("用户的猫叫团子", "L3", {"subject": "pet", "predicate": "name"}),
            _memory("你们一起看过海", "L2"),
        ]
    )
    return service


@pytest.mark.asyncio
async def test_mask_hides_only_old_user_names_during_ordinary_chat() -> None:
    block, degraded, reason = await _service()._build_memory_block(
        _context("今天想去散步", masked=True)
    )

    visible = [item["text"] for item in block.retrieved_memories]
    assert degraded is False
    assert reason is None
    assert "用户的名字是王白" not in visible
    assert "用户昵称是小白" not in visible
    assert "用户的生日是五月十日" in visible
    assert "用户的猫叫团子" in visible
    assert "你们一起看过海" in visible
    assert block.historical_identity_memories == []
    assert block.recently_forgotten_hints == []


@pytest.mark.asyncio
async def test_mask_exposes_old_names_only_for_explicit_history_question() -> None:
    block, _, _ = await _service()._build_memory_block(
        _context("你还记得我以前叫什么吗？", masked=True)
    )

    visible = [item["text"] for item in block.retrieved_memories]
    historical = [item["text"] for item in block.historical_identity_memories]
    assert "用户的名字是王白" not in visible
    assert "用户昵称是小白" not in visible
    assert historical == ["用户的名字是王白", "用户昵称是小白"]


@pytest.mark.asyncio
async def test_generic_current_name_question_does_not_expose_old_identity() -> None:
    block, _, _ = await _service()._build_memory_block(_context("我叫什么？", masked=True))

    assert block.historical_identity_memories == []


@pytest.mark.asyncio
async def test_unbound_mask_restores_original_memory_view() -> None:
    block, _, _ = await _service()._build_memory_block(_context("今天想去散步", masked=False))

    visible = [item["text"] for item in block.retrieved_memories]
    assert "用户的名字是王白" in visible
    assert "用户昵称是小白" in visible
    assert block.recently_forgotten_hints == ["好像和王白这个称呼有关"]
