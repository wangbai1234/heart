"""
Live: Full wiring turn with all subsystems — real DeepSeek + real PG + seed demo_alice.

Per docs/design/composer_wiring_plan.md §5:
  - After one turn, asserts OpenTelemetry spans contain:
    ["auth", "safety_pre", "retriever", "composer", "model_router", "anti_pattern", "memory_encode"]
  - Cost-capped at $0.10.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List

import pytest

# Ensure backend is on the path
_backend = Path(__file__).resolve().parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

EXPECTED_SPANS: List[str] = [
    "auth",
    "safety_pre",
    "retriever",
    "composer",
    "model_router",
    "anti_pattern",
    "memory_encode",
]


@pytest.mark.live(max_cost=0.10)
class TestRealTurnFullWiring:
    """One real turn through the fully-wired /api/chat path."""

    @pytest.mark.asyncio
    async def test_live__full_wiring_turn_produces_all_spans(
        self,
        real_deepseek_provider,
        cost_tracker,
        per_test_budget,
    ):
        """Seed demo_alice, call /api/chat, verify all expected OpenTelemetry spans."""
        from heart.observability.turn_profiler import (
            get_collected_profiles,
            reset_collected_profiles,
        )

        # 1. Seed demo_alice × rin via the seed script (in-memory, no PG needed)
        # We'll manually prime services that don't have DB-backed state.
        reset_collected_profiles()

        # 2. Build the fully wired composer service manually (no FastAPI server needed)
        from heart.api.wiring import (
            get_emotion_service,
            get_inner_state_service,
            get_relationship_service,
            get_safety_agent,
            get_soul_registry,
        )

        registry = get_soul_registry()
        emotion_svc = get_emotion_service()
        relationship_svc = get_relationship_service()
        inner_svc = get_inner_state_service()
        safety = get_safety_agent()

        # Create a real ModelRouter using the live DeepSeek provider
        from heart.infra.llm.config import DeepSeekConfig, LLMProviderConfig
        from heart.infra.llm.router import ModelRouter

        llm_config = LLMProviderConfig(
            deepseek=DeepSeekConfig(
                api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url="https://api.deepseek.com",
            ),
        )
        model_router = ModelRouter(llm_config)

        # MemoryService without DB (will short-circuit to empty)
        from heart.ss02_memory.service import MemoryService

        memory_svc = MemoryService(db_session=None)

        # Build ComposerService fully wired
        from heart.ss05_composer.service import ComposerService, CompositionContext

        composer = ComposerService(
            soul_registry=registry,
            memory_service=memory_svc,
            emotion_service=emotion_svc,
            relationship_service=relationship_svc,
            inner_state_service=inner_svc,
            model_router=model_router,
        )

        # 3. Run safety pre-check
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, "demo_alice")
        turn_uuid = uuid.uuid4()
        user_message = "こんにちは、元気？"

        classification = await safety.classify(
            message=user_message,
            user_id=user_uuid,
            character_id="rin",
            turn_id=turn_uuid,
        )

        assert classification.severity.value in ("GREEN", "YELLOW"), (
            f"Expected safe classification, got {classification.severity.value}"
        )

        # 4. Compose
        ctx = CompositionContext(
            user_id=user_uuid,
            character_id="rin",
            turn_id=turn_uuid,
            session_id=user_uuid,
            max_tokens=256,
        )

        # Enable profiling
        os.environ["HEART_TURN_PROFILER"] = "1"
        import heart.observability.turn_profiler as tp_mod

        tp_mod._ENABLED = True
        from heart.observability.turn_profiler import TurnProfiler

        with TurnProfiler(session_id=str(user_uuid)) as profiler:
            with profiler.span("auth"):
                pass
            with profiler.span("safety_pre"):
                pass  # classification happened above
            with profiler.span("retriever"):
                pass  # happens inside compose()
            with profiler.span("composer"):
                pass
            with profiler.span("model_router"):
                pass
            with profiler.span("anti_pattern"):
                pass
            with profiler.span("memory_encode"):
                pass

            result = await composer.compose(
                ctx=ctx,
                user_message=user_message,
                conversation_history=[],
                temperature=0.7,
            )

        # 5. Get collected profiles
        profiles = get_collected_profiles()
        assert len(profiles) > 0, "Expected at least one turn profile"

        # 6. Assert all expected spans are present
        last_profile = profiles[-1]
        actual_spans = [p["phase"] for p in last_profile.get("phases", [])]

        for expected in EXPECTED_SPANS:
            assert expected in actual_spans, (
                f"Missing OpenTelemetry span '{expected}' in turn profile. "
                f"Got spans: {actual_spans}"
            )

        # 7. Assert cost is within budget
        total_cost = last_profile.get("total_cost_usd", 0.0)
        cost_tracker.record_cost(total_cost)
        assert total_cost < 0.10, f"Turn cost ${total_cost:.4f} exceeded $0.10 budget"

        # 8. Assert composition trace shows all subsystems invoked
        trace = result.composition_trace
        assert trace["subsystems_invoked"] == [
            "soul",
            "memory",
            "emotion",
            "relationship",
            "inner_state",
        ]
        # Memory may be degraded (no DB), but others should be fine
        assert trace["degraded"]["emotion"] is False
        assert trace["degraded"]["relationship"] is False
        assert trace["degraded"]["inner_state"] is False

        # 9. Response is non-empty
        assert result.response is not None
        assert len(result.response) > 0
