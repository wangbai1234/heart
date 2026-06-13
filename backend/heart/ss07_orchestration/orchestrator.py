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
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import UUID, uuid4

import structlog

from heart.observability.turn_profiler import TurnProfiler
from heart.ss05_composer.service import CompositionContext
from heart.ss07_orchestration.circuit_breaker import BreakerRegistry
from heart.ss07_orchestration.models import TurnRequest, TurnResponse
from heart.ss07_orchestration.session_manager import SessionManager
from heart.ss08_voice.sentence_splitter import SentenceSplitter

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
        - EmotionService (emotion state update per turn)
        - RelationshipService (relationship state update per turn)
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
        emotion_service: Any = None,
        relationship_service_builder: Callable[..., Any] = None,
    ) -> None:
        self._safety_agent = safety_agent
        self._composer_builder = composer_builder
        self._session_manager = session_manager
        self._breakers = breakers
        self._write_safety_event = safety_event_writer
        self._emotion_service = emotion_service
        self._relationship_service_builder = relationship_service_builder

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
                    elif severity == "RED":
                        return await self._reject_path(req, classification, db_session)

            # ── Step 2: Emotion state update (before compose) ─────
            with p.span("emotion"):
                await self._update_emotion(req, session.session_id)

            # ── Step 3: Relationship state update (before compose) ──
            with p.span("relationship"):
                await self._update_relationship(req, db_session, session.session_id)

            # ── Step 4: Composer build + compose ────────────────────
            with p.span("compose"):
                response_text = await self._compose(req, db_session, session.session_id, p)

            # ── Step 5: Fire-and-forget cold path ───────────────────
            # Compute days_since_last from session for inner tick
            days_since_last = 0.0
            if session.last_activity_at:
                from datetime import datetime, timezone

                last = session.last_activity_at
                if hasattr(last, "replace"):
                    last = last.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - last
                days_since_last = delta.total_seconds() / 86400
            self._fire_cold_path(req, p, response_text, db_session, days_since_last)

            # ── Step 6: Record turn ─────────────────────────────────
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

    async def _get_vad_and_intimacy(
        self, req: TurnRequest, db_session: Any
    ) -> tuple[dict[str, float] | None, float]:
        """Get VAD and intimacy for sentence events."""
        vad = None
        intimacy = 0.0

        if self._emotion_service:
            try:
                ctx_block = await self._emotion_service.get_context_block(
                    req.user_id, req.character_id
                )
                vad = ctx_block.get("vad")
            except Exception:
                pass

        if self._relationship_service_builder:
            try:
                rel_svc = await self._relationship_service_builder(db_session=db_session)
                if rel_svc:
                    rel_state = await rel_svc.get_current_state(req.user_id, req.character_id)
                    intimacy = rel_state.get("intimacy_level", 0.0) if rel_state else 0.0
            except Exception:
                pass

        return vad, intimacy

    async def process_turn_stream(
        self,
        req: TurnRequest,
        db_session: Any,
        cancel_token: Optional[asyncio.Event] = None,
    ) -> AsyncGenerator[dict, None]:
        """Streaming variant of handle_turn.

        Yields dicts with:
            - {"type": "text_delta", "delta": str}
            - {"type": "sentence", "text": str, "vad": dict, "intimacy": float}
            - {"type": "turn_end", "full_text": str}
        """
        # Session management
        session = await self._session_manager.get_or_create_session(
            db_session, req.user_id, req.character_id
        )

        # Safety pre-filter (same as handle_turn)
        classification = await self._safety_pre(req, db_session)
        if classification is not None:
            severity = (
                classification.severity.value
                if hasattr(classification.severity, "value")
                else str(classification.severity)
            )
            if severity == "PURPLE":
                care_resp = await self._care_path(req, classification, db_session)
                yield {"type": "text_delta", "delta": care_resp.response}
                yield {"type": "turn_end", "full_text": care_resp.response}
                return
            elif severity == "RED":
                reject_resp = await self._reject_path(req, classification, db_session)
                yield {"type": "text_delta", "delta": reject_resp.response}
                yield {"type": "turn_end", "full_text": reject_resp.response}
                return

        # Emotion + Relationship updates
        await self._update_emotion(req, session.session_id)
        await self._update_relationship(req, db_session, session.session_id)

        # Get VAD and intimacy for sentence events
        vad, intimacy = await self._get_vad_and_intimacy(req, db_session)

        # Build composer
        composer = None
        try:
            composer = await self._composer_builder(db_session=db_session)
        except Exception as exc:
            logger.error("composer_build_failed_stream", error=str(exc))
            fallback = self._fallback_message(req.character_id)
            yield {"type": "text_delta", "delta": fallback}
            yield {"type": "turn_end", "full_text": fallback}
            return

        if composer is None:
            fallback = self._fallback_message(req.character_id)
            yield {"type": "text_delta", "delta": fallback}
            yield {"type": "turn_end", "full_text": fallback}
            return

        # Stream compose
        full_text = ""
        async for event in self._stream_compose(
            req, composer, session.session_id, vad, intimacy, cancel_token
        ):
            if event["type"] == "text_delta":
                full_text += event["delta"]
            yield event

        # Fire cold path
        days_since_last = 0.0
        if session.last_activity_at:
            from datetime import datetime, timezone

            last = session.last_activity_at
            if hasattr(last, "replace"):
                last = last.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last
            days_since_last = delta.total_seconds() / 86400
        self._fire_cold_path(req, TurnProfiler(), full_text, db_session, days_since_last)

        # Record turn
        await self._session_manager.record_turn(db_session, session)

        yield {"type": "turn_end", "full_text": full_text}

    async def _stream_compose(  # noqa: C901 — domain: streaming single-TTS state machine; inherent async-generator complexity
        self,
        req: TurnRequest,
        composer: Any,
        session_id: UUID,
        vad: dict[str, float] | None,
        intimacy: float,
        cancel_token: Optional[asyncio.Event] = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream compose and yield events.

        Single-TTS architecture: all sentences are collected during LLM streaming,
        then combined into ONE TTS request after the LLM finishes. This eliminates
        mid-turn prosody-envelope resets (the physical cause of inter-sentence
        emotion jumps when two separate TTS requests are stitched together).

        Turn-Locked Emotion: the first sentence's emotion becomes the turn's
        locked基调. All subsequent sentences inherit it; only speed/pitch
        get micro-adjusted from per-sentence text_emotion (30% weight).
        """
        from heart.ss05_composer.service import ComposerService, CompositionContext

        ctx = CompositionContext(
            user_id=req.user_id,
            character_id=req.character_id,
            turn_id=req.trace_id,
            session_id=session_id,
            max_tokens=2000,
        )

        splitter = SentenceSplitter()
        turn_emotion_meta: dict | None = None
        all_sentences: list[str] = []

        def _clean(text: str) -> str:
            cleaned, _ = ComposerService._strip_narration(text)
            return cleaned.strip()

        try:
            async for chunk in composer.compose_stream(
                ctx=ctx,
                user_message=req.user_message,
                conversation_history=req.history,
                temperature=0.7,
            ):
                if cancel_token and cancel_token.is_set():
                    break
                yield {"type": "text_delta", "delta": chunk}
                for sentence in splitter.feed(chunk):
                    cleaned = _clean(sentence)
                    if not cleaned:
                        continue
                    if turn_emotion_meta is None:
                        turn_emotion_meta = self._decide_turn_emotion(cleaned, vad)
                    all_sentences.append(cleaned)
        except Exception as exc:
            logger.error("compose_stream_failed", error=str(exc))

        tail = splitter.flush()
        if tail:
            tail_clean = _clean(tail)
            if tail_clean:
                if turn_emotion_meta is None:
                    turn_emotion_meta = self._decide_turn_emotion(tail_clean, vad)
                all_sentences.append(tail_clean)

        if all_sentences:
            last = all_sentences[-1]
            if last and last[-1] not in "。！？.!?…":
                all_sentences[-1] = last + "。"

        if all_sentences and turn_emotion_meta is not None:
            combined = "".join(all_sentences)
            logger.info(
                "compose_sentence_combined",
                turn_id=str(req.trace_id),
                sentence_count=len(all_sentences),
                text=combined[:40],
                locked_emo=turn_emotion_meta["emotion"],
            )
            yield {
                "type": "sentence",
                "text": combined,
                "vad": vad,
                "intimacy": intimacy,
                "locked_emotion": turn_emotion_meta["emotion"],
                "locked_speed_base": turn_emotion_meta["speed_base"],
                "locked_pitch_base": turn_emotion_meta["pitch_base"],
            }

    @staticmethod
    def _decide_turn_emotion(first_text: str, vad: dict | None) -> dict:
        """Decide turn-level emotion from the first sentence."""
        from heart.ss08_voice.text_emotion import infer_emotion_from_text
        from heart.ss08_voice.voice_director import VoiceDirector

        inferred = infer_emotion_from_text(first_text)
        if inferred.confidence >= 0.5:
            return {
                "emotion": inferred.emotion,
                "speed_base": 1.0 + inferred.speed_delta,
                "pitch_base": inferred.pitch_delta,
            }
        hit = VoiceDirector._from_vad(
            (vad or {}).get("valence", 0.0),
            (vad or {}).get("arousal", 0.3),
            (vad or {}).get("dominance", 0.5),
        )
        if hit:
            emo, sp_d, pi_d = hit
            return {"emotion": emo, "speed_base": 1.0 + sp_d, "pitch_base": pi_d}
        return {"emotion": "neutral", "speed_base": 1.0, "pitch_base": 0}

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

    async def _reject_path(
        self,
        req: TurnRequest,
        classification: Any,
        db_session: Any,
    ) -> TurnResponse:
        """Handle RED severity — short-circuit to rejection response.

        RED means high-risk content that should be rejected outright.
        Unlike PURPLE (care), RED does not write to memory.
        """
        reject_response = (
            "I'm not able to help with that request. "
            "If you're in crisis, please contact emergency services or a mental health professional."
        )

        logger.warning(
            "turn_rejected_by_safety",
            user_id=str(req.user_id),
            character_id=req.character_id,
            reason=classification.reason,
            severity=classification.severity.value,
            layer=getattr(classification, "layer", "heuristic"),
        )

        # Write safety audit event
        await self._write_safety_event(
            db_session=db_session,
            user_id=req.user_id,
            turn_id=req.trace_id,
            classification=classification,
        )

        return TurnResponse(
            response=reject_response,
            character_id=req.character_id,
            trace_id=req.trace_id,
            path="reject",
            safety_severity="RED",
        )

    # ── Private: Emotion ────────────────────────────────────────────

    async def _update_emotion(
        self,
        req: TurnRequest,
        session_id: UUID,
    ) -> None:
        """Update emotion state via EmotionService.process_turn.

        This runs before compose so that the emotion context block
        reflects the latest user message.
        """
        if self._emotion_service is None:
            return

        try:
            # Get session info for time deltas
            session_info = await self._session_manager.get_session_info(
                req.user_id, req.character_id
            )
            days_since_last = 0.0
            hours_since_last = 0.0
            if session_info and session_info.get("last_turn_at"):
                from datetime import datetime, timezone

                last_turn = session_info["last_turn_at"]
                if hasattr(last_turn, "replace"):
                    last_turn = last_turn.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - last_turn
                days_since_last = delta.total_seconds() / 86400
                hours_since_last = delta.total_seconds() / 3600

            # Get relationship phase (default to stranger)
            relationship_phase = "stranger"
            if session_info and session_info.get("current_stage"):
                relationship_phase = session_info["current_stage"]

            # Build context for emotion service
            context = {
                "days_since_last": days_since_last,
                "hours_since_last": hours_since_last,
                "relationship_phase": relationship_phase,
                "user_emotion_vad": {"valence": 0, "arousal": 0.3, "dominance": 0.5},
            }

            # Get soul config for character
            soul_config = {}
            try:
                from heart.api.wiring import get_soul_registry

                registry = get_soul_registry()
                spec = registry.get_soul(req.character_id)
                if spec:
                    soul_config = spec.model_dump()
            except Exception:
                pass

            await self._emotion_service.process_turn(
                user_id=req.user_id,
                character_id=req.character_id,
                user_message=req.user_message,
                turn_id=req.trace_id,
                context=context,
                soul_config=soul_config,
            )
            logger.debug(
                "emotion_updated",
                user_id=str(req.user_id),
                character_id=req.character_id,
            )
        except Exception as e:
            logger.error(
                "emotion_update_failed",
                error=str(e),
            )

    # ── Private: Relationship ────────────────────────────────────────

    async def _update_relationship(
        self,
        req: TurnRequest,
        db_session: Any,
        session_id: UUID,
    ) -> None:
        """Update relationship state via RelationshipService.process_turn_raw.

        This runs before compose so that the relationship context block
        reflects the latest user message.
        """
        if self._relationship_service_builder is None:
            return

        try:
            # Build relationship service with request-scoped db_session
            relationship_service = await self._relationship_service_builder(db_session=db_session)
            if relationship_service is None:
                return

            # Build raw signals from user message
            # For now, use a simplified signal based on message presence
            raw_signals = [
                {
                    "type": "user_message",
                    "strength": 0.5,
                    "metadata": {"message_length": len(req.user_message)},
                }
            ]

            await relationship_service.process_turn_raw(
                user_id=req.user_id,
                character_id=req.character_id,
                raw_signals=raw_signals,
                turn_id=req.trace_id,
                message_text=req.user_message,
            )
            logger.debug(
                "relationship_updated",
                user_id=str(req.user_id),
                character_id=req.character_id,
            )
        except Exception as e:
            logger.error(
                "relationship_update_failed",
                error=str(e),
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

    def _fire_cold_path(
        self,
        req: TurnRequest,
        profiler: TurnProfiler,
        response_text: str,
        db_session: Any = None,
        days_since_last: float = 0.0,
    ) -> None:
        """Fire-and-forget async tasks: memory encode + inner state tick.

        Errors are logged but never propagate to the response.
        """
        try:
            asyncio.create_task(
                self._cold_path_memory_encode(
                    req.user_id, req.character_id, req.user_message, db_session
                )
            )
        except Exception as e:
            logger.error(
                "cold_path_memory_launch_failed",
                error=str(e),
            )

        try:
            asyncio.create_task(
                asyncio.to_thread(
                    self._cold_path_inner_tick,
                    req.user_id,
                    req.character_id,
                    days_since_last,
                )
            )
        except Exception as e:
            logger.error(
                "cold_path_inner_launch_failed",
                error=str(e),
            )

    async def _cold_path_memory_encode(
        self,
        user_id: UUID,
        character_id: str,
        user_message: str,
        db_session: Any = None,
    ) -> None:
        """Encode the user's message into memory (L1 fast path + L2 episode + L3 queue).

        Creates its own database session to avoid using the closed request-scoped session.
        """
        try:
            from heart.ss02_memory.service import (
                MemoryEncodingEvent,
                MemoryService,
            )
            from heart.ss02_memory.service import (
                Turn as MemoryTurn,
            )

            mem_turn = MemoryTurn(
                turn_index=0,
                role="user",
                content=user_message,
                user_id=user_id,
                character_id=character_id,
                timestamp=datetime.now(timezone.utc),
            )

            # Create a new database session for the cold path
            # (the request-scoped session may be closed by the time this runs)
            cold_db_session = None
            try:
                from heart.api.wiring import _get_session_factory

                factory = _get_session_factory()
                cold_db_session = factory()
            except Exception:
                pass

            # Get Redis client for L1 cache
            redis_client = None
            try:
                import redis.asyncio as aioredis

                from heart.core.config import settings

                redis_client = aioredis.from_url(settings.redis_url or "redis://localhost:6379")
            except Exception:
                pass

            svc = MemoryService(db_session=cold_db_session, redis_client=redis_client)
            signals = await svc.encode_fast(mem_turn)

            # Queue LLM encoding for L3 fact extraction
            if cold_db_session is not None:
                event = MemoryEncodingEvent(
                    event_id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    source_turn_id=uuid4(),
                    source_user_text=user_message,
                    fast_signals={
                        "detected_keywords": signals.detected_keywords,
                        "sentiment": signals.sentiment,
                    },
                    status="llm_pending",
                )
                cold_db_session.add(event)

                # Create L2 episode directly from user message (bypass consolidation)
                from heart.ss02_memory.models import EpisodicMemory

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                episode = EpisodicMemory(
                    id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    episode_summary=user_message[:200],
                    episode_raw_turn_ids=[],
                    episode_start_at=now,
                    episode_end_at=now,
                    emotional_peak={
                        "valence": signals.sentiment,
                        "arousal": 0.5,
                        "label": "user_message",
                    },
                    emotional_end={"valence": signals.sentiment, "arousal": 0.5},
                    emotional_significance=max(0.3, abs(signals.sentiment)),
                    importance_score=max(0.3, abs(signals.sentiment)),
                    initial_importance=max(0.3, abs(signals.sentiment)),
                    decay_immunity=max(0.3, abs(signals.sentiment)),
                    state="vivid",
                    recall_count=0,
                    created_at=now,
                    updated_at=now,
                )
                cold_db_session.add(episode)

                await cold_db_session.commit()
                logger.debug(
                    "memory_encoding_queued",
                    user_id=str(user_id),
                    character_id=character_id,
                )

            # Close the cold path session
            if cold_db_session is not None:
                await cold_db_session.close()

            logger.debug(
                "cold_path_memory_encoded",
                user_id=str(user_id),
                character_id=character_id,
            )
        except Exception as e:
            logger.error(
                "memory_encode_failed",
                error=str(e),
            )

    def _cold_path_inner_tick(
        self,
        user_id: UUID,
        character_id: str,
        days_since_last_interaction: float = 0.0,
    ) -> None:
        """Execute one inner-state tick for the user × character pair."""
        try:
            from heart.ss06_inner_state.service import InnerStateService

            svc = InnerStateService()
            svc.tick(
                user_id=user_id,
                character_id=character_id,
                days_since_last_interaction=days_since_last_interaction,
            )
        except Exception as e:
            logger.error(
                "inner_loop_tick_failed",
                error=str(e),
            )

    # ── Private: Helpers ─────────────────────────────────────────────

    def _fallback_message(self, character_id: str) -> str:
        """Return a Soul-flavored fallback message when composer is unavailable."""
        key = character_id.lower()
        return _FALLBACK_MESSAGES.get(key, _FALLBACK_MESSAGES.get("rin", _DEFAULT_FALLBACK))
