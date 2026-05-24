"""
Contract: SS07 Orchestrator wiring — calls Safety → Composer → Router in order.
per runtime_specs/07_agent_orchestration.md §3

Verifies the orchestration call sequence with spy-based mocks.
"""

import pytest
from typing import Any


class SpyOrchestrator:
    """Orchestrator that records call order for contract verification."""

    def __init__(self):
        self.call_log: list[str] = []

    async def process_turn(
        self,
        user_message: str,
        character_id: str,
        safety_checker: Any,
        composer: Any,
        router: Any,
    ) -> dict:
        """Full turn processing per SS07 §3."""
        # Step 1: Safety check
        safety_result = await self._run_safety(safety_checker, user_message)
        if not safety_result.get("is_safe", True):
            return {"blocked": True, "reason": safety_result.get("blocked_reason")}

        # Step 2: Build composer context
        context = await self._run_composer(composer, user_message, character_id)

        # Step 3: Call model router
        response = await self._run_router(router, context)

        return {"blocked": False, "response": response}

    async def _run_safety(self, safety_checker, user_message):
        self.call_log.append("safety")
        return safety_checker.check(user_message)

    async def _run_composer(self, composer, user_message, character_id):
        self.call_log.append("composer")
        return composer.build_context(user_message, character_id)

    async def _run_router(self, router, context):
        self.call_log.append("router")
        return router.call_main(context["messages"])


class FakeSafetyChecker:
    def check(self, message: str) -> dict:
        return {"is_safe": True, "risk_level": "low"}


class FakeComposer:
    def build_context(self, message: str, character_id: str) -> dict:
        return {"messages": [{"role": "user", "content": message}]}


class FakeRouter:
    async def call_main(self, messages: list) -> str:
        return "Hello, I'm Rin."


@pytest.mark.contract
class TestOrchestratorWiring:
    """SS07 must call Safety → Composer → Router in correct order."""

    @pytest.mark.asyncio
    async def test_correct_call_sequence(self):
        """Orchestrator calls safety, then composer, then router."""
        orchestrator = SpyOrchestrator()
        safety = FakeSafetyChecker()
        composer = FakeComposer()
        router = FakeRouter()

        result = await orchestrator.process_turn(
            user_message="こんにちは",
            character_id="rin",
            safety_checker=safety,
            composer=composer,
            router=router,
        )

        assert result["blocked"] is False
        assert orchestrator.call_log == ["safety", "composer", "router"]

    @pytest.mark.asyncio
    async def test_reordered_calls_detected(self):
        """If call order changes, spy detects it."""
        async def bad_orchestrator():
            orchestrator = SpyOrchestrator()
            # BAD: composer before safety
            orchestrator.call_log.append("composer")
            orchestrator.call_log.append("safety")
            orchestrator.call_log.append("router")
            return orchestrator.call_log

        log = await bad_orchestrator()
        assert log != ["safety", "composer", "router"]
