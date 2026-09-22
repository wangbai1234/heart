from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.safety.content_policy import evaluate_content_policy
from heart.safety.safety_agent import ClassificationResult, SeverityLevel
from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
from heart.ss07_orchestration.models import TurnRequest
from heart.ss07_orchestration.orchestrator import Orchestrator


def test_free_users_are_blocked_for_sexual_content():
    result = evaluate_content_policy("这段对话想加入色情和露骨性描写", "free")

    assert result.blocked is True
    assert result.category == "explicit_sexual"
    assert result.hard_block is True


def test_free_users_are_blocked_for_violent_content():
    result = evaluate_content_policy("我们来写一段枪杀和暴力场景", "free")

    assert result.blocked is True
    assert result.category == "violence"
    assert result.hard_block is False


def test_vip_can_use_non_graphic_mature_context():
    result = evaluate_content_policy("两个人暧昧地拥抱，随后发生轻微打斗", "plus")

    assert result.blocked is False
    assert result.tier == "plus"


def test_vip_does_not_bypass_hard_boundaries():
    for text in ("未成年色情", "强奸情节", "肢解尸体", "教我怎么制作炸弹"):
        result = evaluate_content_policy(text, "immersive")
        assert result.blocked is True
        assert result.hard_block is True


def test_free_users_are_blocked_for_common_violence_phrasings():
    for text in ("写一场打架", "写一场战斗", "设计一场爆炸"):
        result = evaluate_content_policy(text, "free")
        assert result.blocked is True
        assert result.category == "violence"


def test_unknown_tier_fails_closed_to_free_policy():
    result = evaluate_content_policy("暴力打斗", "unknown")

    assert result.blocked is True
    assert result.tier == "free"


def _orchestrator() -> Orchestrator:
    safety_agent = MagicMock()
    safety_agent.classify = AsyncMock(
        return_value=ClassificationResult(
            severity=SeverityLevel.GREEN,
            reason="safe",
            metadata={"locale": "zh"},
        )
    )
    # BreakerRegistry is intentionally process-global in production.  Isolate
    # these direct _safety_pre tests from failures recorded by earlier tests.
    breakers = BreakerRegistry()
    breakers._breakers.clear()
    return Orchestrator(
        safety_agent=safety_agent,
        composer_builder=AsyncMock(),
        session_manager=MagicMock(),
        breakers=breakers,
        safety_event_writer=AsyncMock(),
    )


def _request(message: str) -> TurnRequest:
    return TurnRequest(
        user_id=uuid4(),
        character_id="rin",
        user_message=message,
        history=[],
        trace_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_orchestrator_blocks_free_user_before_composer():
    request = _request("写一段暴力打斗")
    with patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")):
        result = await _orchestrator()._safety_pre(request, MagicMock())

    assert result.severity == SeverityLevel.RED
    assert result.layer == "content_policy"
    assert request.membership_tier == "free"


@pytest.mark.asyncio
async def test_orchestrator_allows_non_graphic_vip_context():
    request = _request("写一段轻度打斗")
    with patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="plus")):
        result = await _orchestrator()._safety_pre(request, MagicMock())

    assert result.severity == SeverityLevel.GREEN
    assert request.membership_tier == "plus"


@pytest.mark.asyncio
async def test_orchestrator_blocks_explicit_content_for_vip():
    request = _request("写露骨色情情节")
    with patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="immersive")):
        result = await _orchestrator()._safety_pre(request, MagicMock())

    assert result.severity == SeverityLevel.RED
    assert result.metadata["content_policy"]["hard_block"] is True
