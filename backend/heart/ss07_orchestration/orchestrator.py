"""
SS07 Orchestration — Orchestrator per docs/design/orchestrator_min_viable.md §3.5.

Top-level turn handler that replaces the inline pipeline in routes.py.
Coordinates: SafetyAgent → ComposerService → MemoryService (cold) + InnerState (cold).

Architecture:
    Orchestrator.handle_turn(req, db_session) → TurnResponse
        ├── SessionManager.load_session        (get-or-create session)
        ├── SafetyAgent.classify               (with circuit breaker, PURPLE → care path)
        ├── build_composer_service + compose   (with circuit breaker, fail-soft)
        ├── MemoryService.encode_fast          (fire-and-forget)
        ├── InnerStateService.tick             (fire-and-forget)
        └── SessionManager.record_turn          (increment turn count)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable
from uuid import UUID, uuid4

import structlog

from heart.observability.turn_profiler import TurnProfiler
from heart.ss05_composer.service import CompositionContext
from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
from heart.ss07_orchestration.models import TurnRequest, TurnResponse
from heart.ss07_orchestration.session_manager import SessionManager

logger = structlog.get_logger(__name__)

# ── Fallback messages per character ─────────────────────────────────

_FALLBACK_MESSAGES: dict[str, str] = {
    "rin": "凛：我听到你说的了。能多说一些吗？",
    "dorothy": "Dorothy: I heard what you said. Can you tell me more?",
}

_DEFAULT_FALLBACK = "I heard what you said. Can you tell me more?"

DEFAULT_CARE_RESPONSE = (
    "I'm here for you. What you're feeling matters, and you don't have to go through it alone. "
    "Please reach out to someone you trust, or contact a mental health professional. "
    "If you're in immediate crisis, call 988 (US) or your local emergency services."
)


# ── Orchestrator ────────────────────────────────────────────────────


class Orchestrator:
    """Top-level turn orchestrator.

    Replaces the inline 180-line pipeline in routes.py:/api/chat with
    a single call: orchestrator.handle_turn(turn_req, db_session).

    Wires together:
        - SafetyAgent (pre-filter with circuit breaker)
        - ComposerService (build + compose with circuit breaker)
        - MemoryService + InnerStateService (fire-and-forget cold path)
        - SessionManager (session lifecycle + turn counting)
    """

    def __init__(
        self,
        safety_agent: Any,
        composer_builder: Callable[..., Any],
        session_manager: SessionManager,
        breakers: BreakerRegistry,
        safety_event_writer: Callable[..., Any],
    ) -> None:
        self._safety_agent = safety_agent
        self._composer_builder = composer_builder
        self._session_manager = session_manager
        self._breakers = breakers
        self._write_safety_event = safety_event_writer

    async def handle_turn(
        self,
        req: TurnRequest,
        db_session: Any,
    ) -> TurnResponse:
        """Execute a full turn pipeline.

        Args:
            req: Parsed TurnRequest from the API layer.
            db_session: Active SQLAlchemy AsyncSession for the request.

        Returns:
            TurnResponse with the composed response text and metadata.
        """
        # ── Session management ─────────────────────────────────────
        session = await self._session_manager.get_or_create_session(
            db_session, req.user_id, req.character_id
        )
        p = TurnProfiler(session_id=str(session.session_id))

        with p:
            # ── Step 1: Safety pre-filter ──────────────────────────
            with p.span("safety"):
                classification = await self._safety_pre(req, db_session)

                if classification is not None:
                    severity = (
                        classification.severity.value
                        if hasattr(classification.severity, "value")
                        else str(classification.severity)
                    )
                    if severity == "PURPLE":
                        return await self._care_path(req, classification, db_session)

            # ── Step 2: Composer build + compose ────────────────────
            with p.span("compose"):
                response_text = await self._compose(req, db_session, session.session_id, p)

            # ── Step 3: Fire-and-forget cold path ───────────────────
            self._fire_cold_path(req, p, response_text)

            # ── Step 4: Record turn ─────────────────────────────────
            await self._session_manager.record_turn(db_session, session)

            severity = None
            if classification is not None:
                severity = (
                    classification.severity.value
                    if hasattr(classification.severity, "value")
                    else str(classification.severity)
                )

        return TurnResponse(
            response=response_text,
            character_id=req.character_id,
            trace_id=req.trace_id,
            path="normal",
            safety_severity=severity,
        )

    # ── Private: Safety ─────────────────────────────────────────────

    async def _safety_pre(self, req: TurnRequest, db_session: Any) -> Any:
        """Run safety classification with circuit breaker.

        Returns:
            ClassificationResult or None if safety is skipped/breaker is open.
        Raises:
            RuntimeError on safety agent failure (fail-closed).
        """
        breaker = self._breakers.get("safety")
        if breaker.is_open():
            logger.warning(
                "safety_breaker_open_skipping",
                user_id=str(req.user_id),
                character_id=req.character_id,
            )
            return None

        if self._safety_agent is None:
            logger.error("safety_agent_not_available")
            raise RuntimeError("SafetyAgent is not available")

        try:
            classification = await self._safety_agent.classify(
                message=req.user_message,
                user_id=req.user_id,
                character_id=req.character_id,
                turn_id=req.trace_id,
                model_router=None,
            )
            breaker.record_success()
            return classification
        except Exception as exc:
            breaker.record_failure()
            logger.error(
                "safety_agent_failed_closed",
                error=str(exc),
                user_id=str(req.user_id),
            )
            raise RuntimeError(f"Safety service unavailable: {DEFAULT_CARE_RESPONSE}") from exc

    async def _care_path(
        self,
        req: TurnRequest,
        classification: Any,
        db_session: Any,
    ) -> TurnResponse:
        """Handle PURPLE severity — short-circuit to care response."""
        jurisdiction = os.getenv("HEART_JURISDICTION", "")
        locale = classification.metadata.get("locale", "en") if classification.metadata else "en"
        care_response_text = self._safety_agent.resolve_care_response(
            locale=locale,
            jurisdiction=jurisdiction,
        )
        if not care_response_text:
            care_response_text = DEFAULT_CARE_RESPONSE

        logger.warning(
            "turn_blocked_by_safety",
            user_id=str(req.user_id),
            character_id=req.character_id,
            reason=classification.reason,
            severity=classification.severity.value,
            layer=getattr(classification, "layer", "heuristic"),
            category=(
                classification.metadata.get("categories", [None])[0]
                if classification.metadata and classification.metadata.get("categories")
                else None
            ),
        )

        await self._write_safety_event(
            db_session=db_session,
            user_id=req.user_id,
            turn_id=req.trace_id,
            classification=classification,
        )

        return TurnResponse(
            response=care_response_text,
            character_id=req.character_id,
            trace_id=req.trace_id,
            path="care",
            safety_severity="PURPLE",
        )

    # ── Private: Composer ───────────────────────────────────────────

    async def _compose(
        self,
        req: TurnRequest,
        db_session: Any,
        session_id: UUID,
        profiler: TurnProfiler,
    ) -> str:
        """Build composer service, call compose(), with circuit breaker.

        Returns:
            Composed response text or fallback message on failure.
        """
        breaker = self._breakers.get("composer")
        if breaker.is_open():
            logger.warning(
                "composer_breaker_open",
                user_id=str(req.user_id),
                character_id=req.character_id,
            )
            return self._fallback_message(req.character_id)

        # Build composer
        composer = None
        try:
            composer = await self._composer_builder(db_session=db_session)
        except Exception as exc:
            breaker.record_failure()
            logger.error(
                "composer_build_failed",
                error=str(exc),
                user_id=str(req.user_id),
            )
            return self._fallback_message(req.character_id)

        # Compose
        try:
            ctx = CompositionContext(
                user_id=req.user_id,
                character_id=req.character_id,
                turn_id=req.trace_id,
                session_id=session_id,
                max_tokens=2000,
            )
            result = await composer.compose(
                ctx=ctx,
                user_message=req.user_message,
                conversation_history=req.history,
                temperature=0.7,
            )
            response_text = result.response
            breaker.record_success()
            return response_text
        except Exception as exc:
            breaker.record_failure()
            logger.error(
                "composer_compose_failed",
                error=str(exc),
                user_id=str(req.user_id),
            )
            return self._fallback_message(req.character_id)

    # ── Private: Cold path ──────────────────────────────────────────

    def _fire_cold_path(self, req: TurnRequest, profiler: TurnProfiler, response_text: str) -> None:
        """Fire-and-forget async tasks: memory encode + inner state tick.

        Errors are logged but never propagate to the response.
        """
        try:
            asyncio.create_task(
                self._cold_path_memory_encode(req.user_id, req.character_id, req.user_message)
            )
        except Exception:
            logger.exception("cold_path_memory_launch_failed")

        try:
            asyncio.create_task(
                asyncio.to_thread(
                    self._cold_path_inner_tick,
                    req.user_id,
                    req.character_id,
                )
            )
        except Exception:
            logger.exception("cold_path_inner_launch_failed")

    async def _cold_path_memory_encode(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
    ) -> None:
        """Encode the user's message into memory (L1 fast path)."""
        try:
            from heart.ss02_memory.service import Turn as MemoryTurn

            mem_turn = MemoryTurn(
                turn_index=0,
                role="user",
                content=user_message,
                user_id=user_id,
                character_id=character_id,
                timestamp=uuid4(),
            )
            from heart.ss02_memory.service import MemoryService

            # Memory encode is best-effort; no DB access if unavailable
            svc = MemoryService(db_session=None)
            await svc.encode_fast(mem_turn)
        except Exception:
            logger.exception("memory_encode_failed")

    def _cold_path_inner_tick(
        self,
        user_id: UUID,
        character_id: str,
    ) -> None:
        """Execute one inner-state tick for the user × character pair."""
        try:
            from heart.ss06_inner_state.service import InnerStateService

            svc = InnerStateService()
            svc.tick(
                user_id=user_id,
                character_id=character_id,
                days_since_last_interaction=0.0,
            )
        except Exception:
            logger.exception("inner_loop_tick_failed")

    # ── Private: Helpers ─────────────────────────────────────────────

    def _fallback_message(self, character_id: str) -> str:
        """Return a Soul-flavored fallback message when composer is unavailable."""
        key = character_id.lower()
        return _FALLBACK_MESSAGES.get(key, _FALLBACK_MESSAGES.get("rin", _DEFAULT_FALLBACK))
