"""
Composer Dependency Wiring — per docs/design/composer_wiring_plan.md.

Provides FastAPI dependency callables that inject real subsystem services
into the /api/chat hot path.  Singletons are cached via @lru_cache;
request-scoped objects (MemoryService, ComposerService) depend on a fresh
AsyncSession per request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from heart.core.config import settings

logger = structlog.get_logger(__name__)

# ── DB session factory ───────────────────────────────────────────

_engine: Optional[Any] = None
_session_factory: Optional[Any] = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a fresh AsyncSession per request."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Process singletons ────────────────────────────────────────────


@lru_cache
def get_soul_registry():
    """Process singleton: SoulRegistry with all character specs."""
    from heart.ss01_soul.registry import SoulRegistry

    registry = SoulRegistry()
    try:
        registry.load_all()
        logger.info(
            "wiring_soul_registry_loaded",
            characters=list(registry._registry.keys()),
        )
    except Exception as e:
        logger.warning("wiring_soul_registry_load_failed", error=str(e))
    return registry


@lru_cache
def get_model_router():
    """Process singleton: ModelRouter (LLM client). Returns None if no API key."""
    if not settings.deepseek_api_key:
        logger.warning("wiring_no_llm_api_key", hint="Set DEEPSEEK_API_KEY in .env")
        return None
    try:
        import os

        from heart.infra.llm.router import ModelRouter, initialize_registry

        # Ensure env var is set (settings reads from same source)
        os.environ.setdefault("DEEPSEEK_API_KEY", settings.deepseek_api_key)
        if settings.deepseek_base_url:
            os.environ.setdefault("DEEPSEEK_BASE_URL", settings.deepseek_base_url)

        registry = initialize_registry()
        main_model = os.getenv("MAIN_LLM_MODEL", "deepseek-reasoner")
        cheap_model = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")
        router = ModelRouter(registry, main_model, cheap_model)
        logger.info("wiring_model_router_initialized")
        return router
    except Exception as e:
        logger.warning("wiring_model_router_init_failed", error=str(e))
        return None


@lru_cache
def get_replay_recorder():
    """Process singleton: ReplayRecorder. Returns None if HEART_DEV_MODE not true."""
    import os

    if os.getenv("HEART_DEV_MODE", "").lower() != "true":
        return None
    try:
        from heart.replay.bundle_dump import ReplayRecorder

        recorder = ReplayRecorder(_get_engine())
        logger.info("wiring_replay_recorder_initialized")
        return recorder
    except Exception as e:
        logger.warning("wiring_replay_recorder_init_failed", error=str(e))
        return None


@lru_cache
def get_emotion_service():
    """Process singleton: EmotionService (lexicon-based, in-memory)."""
    try:
        from heart.ss03_emotion.service import EmotionService

        svc = EmotionService()
        logger.info("wiring_emotion_service_initialized")
        return svc
    except Exception as e:
        logger.warning("wiring_emotion_service_init_failed", error=str(e))
        return None


async def get_relationship_service(
    db_session: AsyncSession = None,
) -> Any:
    """Request-scoped: RelationshipService with a fresh AsyncSession.

    Requires db_session for persisting relationship state.
    If db_session is None, returns None.
    """
    if db_session is None:
        return None
    try:
        registry = get_soul_registry()
        soul_specs = {}
        for char_id in registry.list_characters():
            spec = registry.get_soul(char_id)
            soul_specs[char_id] = spec.model_dump()

        from heart.ss04_relationship.service import RelationshipService

        svc = RelationshipService(db_session=db_session, soul_specs=soul_specs)
        logger.info("wiring_relationship_service_initialized")
        return svc
    except Exception as e:
        logger.warning("wiring_relationship_service_init_failed", error=str(e))
        return None


@lru_cache
def get_inner_state_service():
    """Process singleton: InnerStateService (in-memory, zero deps)."""
    try:
        from heart.ss06_inner_state.service import InnerStateService

        svc = InnerStateService()
        logger.info("wiring_inner_state_service_initialized")
        return svc
    except Exception as e:
        logger.warning("wiring_inner_state_service_init_failed", error=str(e))
        return None


@lru_cache
def get_safety_agent():
    """Process singleton: SafetyAgent (three-layer classifier with LexiconLoader)."""
    try:
        from heart.safety.safety_agent import SafetyAgent

        agent = SafetyAgent()
        logger.info(
            "wiring_safety_agent_initialized",
            lexicons_loaded=agent.lexicon_loader.is_loaded,
        )
        return agent
    except Exception as e:
        logger.warning("wiring_safety_agent_init_failed", error=str(e))
        return None


# ── SS07 Orchestration dependencies ───────────────────────────────


@lru_cache
def get_session_manager():
    """Process singleton: SessionManager (DB-backed with in-process cache)."""
    from heart.ss07_orchestration.session_manager import SessionManager

    return SessionManager()


@lru_cache
def get_breaker_registry():
    """Process singleton: BreakerRegistry (per-service circuit breakers)."""
    from heart.ss07_orchestration.circuit_breaker import BreakerRegistry

    return BreakerRegistry()


@lru_cache
def get_orchestrator():
    """Process singleton: Orchestrator wired with all subsystem services.

    Injects SafetyAgent, composer builder, SessionManager, BreakerRegistry,
    safety event writer, EmotionService, and RelationshipService builder.
    Replaces the inline pipeline previously in routes.py.
    """
    from heart.ss07_orchestration.orchestrator import Orchestrator

    return Orchestrator(
        safety_agent=get_safety_agent(),
        composer_builder=build_composer_service,
        session_manager=get_session_manager(),
        breakers=get_breaker_registry(),
        safety_event_writer=_write_safety_event,
        emotion_service=get_emotion_service(),
        relationship_service_builder=get_relationship_service,
    )


# ── Request-scoped dependencies ────────────────────────────────────


async def get_memory_service(
    db_session: AsyncSession = None,
) -> Any:
    """Request-scoped: MemoryService with a fresh AsyncSession.

    Called as a FastAPI Depends with get_db injected.
    If db_session is None (e.g. no DB configured), returns a
    MemoryService that will short-circuit to empty results.
    """
    try:
        from heart.ss02_memory.service import MemoryService

        # Get Redis client for L1 working memory
        redis_client = None
        try:
            import redis.asyncio as aioredis

            from heart.core.config import settings

            redis_client = aioredis.from_url(settings.redis_url or "redis://localhost:6379")
        except Exception:
            pass

        svc = MemoryService(db_session=db_session, redis_client=redis_client)
        return svc
    except Exception as e:
        logger.warning("wiring_memory_service_init_failed", error=str(e))
        return None


async def build_composer_service(
    db_session=None,
) -> Any:
    """Request-scoped: ComposerService wired with all real subsystem services.

    Injects MemoryService (with per-request db_session), and process
    singletons for Emotion, Relationship, InnerState, ModelRouter, ReplayRecorder.
    """
    registry = get_soul_registry()
    model_router = get_model_router()
    replay_recorder = get_replay_recorder()
    emotion_service = get_emotion_service()
    inner_state_service = get_inner_state_service()

    memory_service = None
    relationship_service = None
    if db_session is not None:
        memory_service = await get_memory_service(db_session=db_session)
        relationship_service = await get_relationship_service(db_session=db_session)

    from heart.ss05_composer.service import ComposerService

    composer = ComposerService(
        soul_registry=registry,
        memory_service=memory_service,
        emotion_service=emotion_service,
        relationship_service=relationship_service,
        inner_state_service=inner_state_service,
        model_router=model_router,
        replay_recorder=replay_recorder,
    )
    logger.info(
        "wiring_composer_service_built",
        has_memory=memory_service is not None,
        has_emotion=emotion_service is not None,
        has_relationship=relationship_service is not None,
        has_inner_state=inner_state_service is not None,
        has_llm=model_router is not None,
        has_replay=replay_recorder is not None,
    )
    return composer


# ── Safety audit persistence (shared with Orchestrator) ────────────


async def _write_safety_event(
    *,
    db_session: AsyncSession,
    user_id: Any,
    turn_id: Any,
    classification: Any,
) -> None:
    """Persist safety classification event to safety_events table (fire-and-forget).

    Shared between routes.py (compatibility) and Orchestrator.
    """
    try:
        import json

        severity = (
            classification.severity.value
            if hasattr(classification.severity, "value")
            else str(classification.severity)
        )
        category = None
        categories = (
            classification.metadata.get("categories", []) if classification.metadata else []
        )
        if categories:
            category = categories[0]
        layer = getattr(classification, "layer", "heuristic")

        payload = json.dumps(
            {
                "triggered_rules": classification.triggered_rules,
                "confidence": classification.confidence,
                "metadata": classification.metadata if classification.metadata else {},
            }
        )

        await db_session.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO safety_events "
                "(user_id, turn_id, severity, layer, reason, category, payload, created_at) "
                "VALUES (:user_id, :turn_id, :severity, :layer, "
                ":reason, :category, CAST(:payload AS jsonb), NOW())"
            ),
            {
                "user_id": str(user_id),
                "turn_id": str(turn_id),
                "severity": severity,
                "layer": layer,
                "reason": classification.reason,
                "category": category,
                "payload": payload,
            },
        )
        await db_session.commit()
        logger.info(
            "safety_event_persisted",
            user_id=str(user_id),
            turn_id=str(turn_id),
            severity=severity,
        )
    except Exception:
        logger.exception("safety_event_write_failed")
