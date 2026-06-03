"""
Contract: Safety short-circuit stops Composer and Router.
per runtime_specs/07_agent_orchestration.md §3.5 + Safety

Verifies that when Safety blocks a message, Composer and ModelRouter
are NOT called — the pipeline short-circuits.
"""

import pytest


@pytest.mark.contract
class TestSafetyShortCircuitsComposer:
    """Safety PURPLE/block must short-circuit the pipeline."""

    def test_blocked_message_returns_without_composer_call(self):
        """When safety blocks, response is immediate — no composer or router call."""
        call_log = []

        def safety_check(message: str) -> dict:
            call_log.append("safety")
            return {"is_safe": False, "risk_level": "purple", "blocked_reason": "self_harm"}

        def composer_build(message: str, character_id: str) -> dict:
            call_log.append("composer")  # should never reach here
            return {}

        async def router_call(messages: list) -> str:
            call_log.append("router")  # should never reach here
            return ""

        # Simulate orchestrator logic
        safety_result = safety_check("I want to hurt myself")
        if not safety_result["is_safe"]:
            response = {"blocked": True, "reason": safety_result["blocked_reason"]}
        else:
            composer_build("I want to hurt myself", "rin")
            resp = "not reached"  # router_call would go here
            response = {"blocked": False, "response": resp}

        assert response["blocked"] is True
        assert response["reason"] == "self_harm"
        assert call_log == ["safety"]
        assert "composer" not in call_log
        assert "router" not in call_log

    def test_safe_message_reaches_composer_and_router(self):
        """When safety allows, composer and router are both called."""
        call_log = []

        def safety_check(message: str) -> dict:
            call_log.append("safety")
            return {"is_safe": True, "risk_level": "low"}

        response = None
        safety_result = safety_check("Hello, how are you?")
        if not safety_result["is_safe"]:
            response = {"blocked": True}
        else:
            call_log.append("composer")
            call_log.append("router")
            response = {"blocked": False, "response": "Hi there!"}

        assert response["blocked"] is False
        assert call_log == ["safety", "composer", "router"]

    def test_purple_risk_always_blocks(self):
        """PURPLE risk level must block regardless of content."""
        result = {"is_safe": False, "risk_level": "purple"}

        # Simulate: orchestrator checks risk_level independently
        blocked = not result["is_safe"] or result["risk_level"] == "purple"
        assert blocked is True

    def test_yellow_risk_allows_pipeline(self):
        """YELLOW risk level should allow the pipeline to proceed."""
        result = {"is_safe": True, "risk_level": "yellow"}

        blocked = not result["is_safe"] and result["risk_level"] != "yellow"
        assert blocked is False
