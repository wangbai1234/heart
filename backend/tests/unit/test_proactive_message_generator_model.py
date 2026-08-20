"""Selected-model routing for the standalone proactive generator."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss06_inner_state.composer import InnerState
from heart.ss06_inner_state.initiative_decider import InitiativeDecision, TriggerType
from heart.ss06_inner_state.proactive_message import ProactiveMessageGenerator


@pytest.mark.asyncio
async def test_generator_and_reroll_use_selected_model():
    router = MagicMock()
    router.call_for = AsyncMock(
        side_effect=[
            ("我只是来看看你。", "grok-4.5"),
            ("刚好路过。", "grok-4.5"),
        ]
    )
    generator = ProactiveMessageGenerator(router, max_retries=1)
    generator._check_anti_pattern = MagicMock(
        side_effect=[("我只是来看看你。", ["too direct"]), ("刚好路过。", [])]
    )

    result = await generator.generate(
        InitiativeDecision(
            act=True,
            trigger_type=TriggerType.THOUGHT_SHARE,
            planned_message_seed={},
        ),
        InnerState(user_id=uuid4(), character_id="rin"),
        "rin",
        model="grok-4.5",
    )

    assert result.success is True
    assert router.call_for.await_count == 2
    assert all(call.args[0] == "grok-4.5" for call in router.call_for.await_args_list)
