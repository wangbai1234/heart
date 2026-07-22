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
from sqlalchemy import text
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


def get_db_session_factory():
    """Return the async session factory (for background tasks)."""
    return _get_session_factory()


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a fresh AsyncSession per request."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Process singletons ────────────────────────────────────────────


@lru_cache
def get_soul_registry():
    """Process singleton: delegates to the module-level registry singleton.

    Previously this built its own SoulRegistry instance, causing a dual-singleton
    hazard where the wiring layer and the rest of the codebase saw different
    character sets.  Now it simply returns the shared module singleton so there is
    exactly one registry in the process.  cache_clear() is kept as a belt-and-
    suspenders hook called by reload.py on hot-reload.
    """
    from heart.ss01_soul.registry import get_soul_registry as _module_registry

    return _module_registry()


@lru_cache
def get_model_router():
    """Process singleton: ModelRouter (LLM client). Returns None if no API key."""
    if not settings.deepseek_api_key:
        logger.warning("wiring_no_llm_api_key", hint="Set DEEPSEEK_API_KEY in .env")
        return None
    try:
        import os

        from heart.infra.llm_providers import ModelRouter, initialize_registry

        # Bridge settings → env (registry.initialize_registry reads os.getenv).
        # setdefault means an explicitly-exported env var still wins.
        os.environ.setdefault("DEEPSEEK_API_KEY", settings.deepseek_api_key)
        if settings.deepseek_api_keys:
            os.environ.setdefault("DEEPSEEK_API_KEYS", settings.deepseek_api_keys)
        if settings.deepseek_base_url:
            os.environ.setdefault("DEEPSEEK_BASE_URL", settings.deepseek_base_url)
        # Make config.py the source of truth for model + concurrency defaults.
        os.environ.setdefault("MAIN_LLM_MODEL", settings.main_llm_model)
        os.environ.setdefault("CHEAP_LLM_MODEL", settings.cheap_llm_model)
        os.environ.setdefault("LLM_MAX_CONCURRENCY", str(settings.llm_max_concurrency))
        os.environ.setdefault("LLM_MAX_RETRIES", str(settings.llm_max_retries))
        os.environ.setdefault("LLM_KEY_COOLDOWN_SECONDS", str(settings.llm_key_cooldown_seconds))

        registry = initialize_registry()
        main_model = os.getenv("MAIN_LLM_MODEL", "deepseek-chat")
        cheap_model = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")
        router = ModelRouter(registry, main_model, cheap_model)
        logger.info("wiring_model_router_initialized")
        return router
    except Exception as e:
        logger.warning("wiring_model_router_init_failed", error=str(e))
        return None


@lru_cache
def get_embedding_service():
    """Process singleton: EmbeddingService. Returns None if no EMBEDDING_API_KEY.

    When None, memory writes skip semantic_vector and retrieval falls back to
    recency/identity — i.e. exactly the pre-semantic-recall behaviour.
    """
    from heart.infra.embeddings import build_embedding_service

    return build_embedding_service(settings)


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
    """Process singleton: EmotionService (lexicon-based, in-memory).

    Injects a session_factory so the singleton can persist each turn's
    EmotionEvent through its own short-lived cold session (it holds no
    request-bound session). Without it the append-only emotion_events log
    would never be written.
    """
    try:
        from heart.ss03_emotion.service import EmotionService

        svc = EmotionService(session_factory=_get_session_factory())
        logger.info("wiring_emotion_service_initialized")
        return svc
    except Exception as e:
        logger.warning("wiring_emotion_service_init_failed", error=str(e))
        return None


# Generation-keyed memo for the spec map passed to RelationshipService.
# Rebuilt only when the registry generation advances (i.e. a new UGC character
# was registered or invalidated), so the O(N) model_dump() loop runs at most
# once per registry mutation rather than on every request.
_spec_map_cache: dict[str, Any] = {"generation": -1, "soul_specs": {}}


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
        gen = registry.generation
        if _spec_map_cache["generation"] != gen:
            soul_specs = {}
            for char_id in registry.list_characters():
                spec = registry.get_soul(char_id)
                soul_specs[char_id] = spec.model_dump()
            _spec_map_cache["generation"] = gen
            _spec_map_cache["soul_specs"] = soul_specs
        soul_specs = _spec_map_cache["soul_specs"]

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


@lru_cache
def get_story_service():
    """Process singleton: StoryService (SS09 story engine).

    Reuses the model router + safety agent + session factory. Returns None if
    the LLM router is unavailable (no API key) so callers can 503 cleanly.
    """
    router = get_model_router()
    if router is None:
        logger.warning("wiring_story_service_no_router")
        return None
    try:
        from heart.ss09_story.service import StoryService

        svc = StoryService(
            session_factory=_get_session_factory(),
            model_router=router,
            safety_agent=get_safety_agent(),
        )
        logger.info("wiring_story_service_initialized")
        return svc
    except Exception as e:
        logger.warning("wiring_story_service_init_failed", error=str(e))
        return None


def _build_minimax_members() -> list:
    """Build one MiniMaxProvider per configured key (primary + optional pool extras)."""
    from heart.ss08_voice.minimax_provider import MiniMaxProvider

    keys: list[str] = []
    if settings.minimax_api_key:
        keys.append(settings.minimax_api_key.strip())
    if settings.minimax_api_keys:
        keys.extend(k.strip() for k in settings.minimax_api_keys.split(",") if k.strip())
    # De-dup while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            deduped.append(k)
    keys = deduped

    group_ids = [g.strip() for g in (settings.minimax_group_ids or "").split(",") if g.strip()]
    default_group = settings.minimax_group_id or ""

    members = []
    for idx, key in enumerate(keys):
        group_id = group_ids[idx] if idx < len(group_ids) else default_group
        members.append(
            MiniMaxProvider(api_key=key, group_id=group_id, base_url=settings.minimax_base_url)
        )
    return members


def _build_primary_voice_provider() -> Any:
    """Build the primary TTS provider: MiMo first, then Fish, then MiniMax last.

    Priority order (B5):
    1. MiMo — if MIMO_API_KEY set
    2. Fish Audio — if FISH_API_KEY set
    3. MiniMax — legacy fallback (clone voice_id support)
    """
    if settings.mimo_api_key:
        try:
            from heart.ss08_voice.mimo_provider import MiMoProvider

            provider = MiMoProvider(
                api_key=settings.mimo_api_key,
                base_url=settings.mimo_base_url,
            )
            logger.info("wiring_mimo_primary_initialized")
            return provider
        except Exception as e:
            logger.warning("wiring_mimo_provider_init_failed", error=str(e))

    if settings.fish_api_key:
        try:
            from heart.ss08_voice.fish_provider import FishProvider

            provider = FishProvider(
                api_key=settings.fish_api_key,
                base_url=settings.fish_base_url,
                model=settings.fish_model,
            )
            logger.info("wiring_fish_primary_initialized")
            return provider
        except Exception as e:
            logger.warning("wiring_fish_provider_init_failed", error=str(e))

    if settings.minimax_api_key or settings.minimax_api_keys:
        try:
            from heart.ss08_voice.pooled_provider import PooledTTSProvider

            members = _build_minimax_members()
            if members:
                provider = PooledTTSProvider(
                    members,
                    max_concurrency=settings.tts_max_concurrency,
                    max_retries=settings.tts_max_retries,
                    cooldown_seconds=settings.tts_key_cooldown_seconds,
                )
                logger.info("wiring_minimax_primary_initialized", keys=len(members))
                return provider
        except Exception as e:
            logger.warning("wiring_minimax_provider_init_failed", error=str(e))

    return None


def _build_fallback_voice_provider(primary_provider: Any) -> Any:
    """Build the fallback TTS provider.

    - MiMo primary → Fish fallback (if configured), else MiniMax
    - Fish primary → MiniMax fallback (if configured)
    - MiniMax primary → MiMo fallback (if configured)
    """
    if not settings.voice_fallback_enabled:
        return None
    primary_name = primary_provider.name if primary_provider else ""
    try:
        if primary_name == "mimo":
            if settings.fish_api_key:
                from heart.ss08_voice.fish_provider import FishProvider

                provider = FishProvider(
                    api_key=settings.fish_api_key,
                    base_url=settings.fish_base_url,
                    model=settings.fish_model,
                )
                logger.info("wiring_fish_fallback_initialized")
                return provider
            if settings.minimax_api_key:
                from heart.ss08_voice.minimax_provider import MiniMaxProvider

                provider = MiniMaxProvider(
                    api_key=settings.minimax_api_key,
                    group_id=settings.minimax_group_id or "",
                    base_url=settings.minimax_base_url,
                )
                logger.info("wiring_minimax_fallback_initialized")
                return provider
        elif primary_name == "fish" and settings.minimax_api_key:
            from heart.ss08_voice.minimax_provider import MiniMaxProvider

            provider = MiniMaxProvider(
                api_key=settings.minimax_api_key,
                group_id=settings.minimax_group_id or "",
                base_url=settings.minimax_base_url,
            )
            logger.info("wiring_minimax_fallback_initialized")
            return provider
        elif primary_name == "minimax" and settings.mimo_api_key:
            from heart.ss08_voice.mimo_provider import MiMoProvider

            provider = MiMoProvider(
                api_key=settings.mimo_api_key,
                base_url=settings.mimo_base_url,
            )
            logger.info("wiring_mimo_fallback_initialized")
            return provider
    except Exception as e:
        logger.warning("wiring_voice_fallback_init_failed", error=str(e))
    return None


def _build_mimo_provider() -> Any:
    """Construct a MiMo TTS provider if MIMO_API_KEY is set, else None."""
    if not settings.mimo_api_key:
        return None
    try:
        from heart.ss08_voice.mimo_provider import MiMoProvider

        return MiMoProvider(api_key=settings.mimo_api_key, base_url=settings.mimo_base_url)
    except Exception as e:
        logger.warning("wiring_mimo_provider_init_failed", error=str(e))
        return None


def _build_fish_provider() -> Any:
    """Construct a Fish TTS provider if FISH_API_KEY is set, else None."""
    if not settings.fish_api_key:
        return None
    try:
        from heart.ss08_voice.fish_provider import FishProvider

        return FishProvider(
            api_key=settings.fish_api_key,
            base_url=settings.fish_base_url,
            model=settings.fish_model,
        )
    except Exception as e:
        logger.warning("wiring_fish_provider_init_failed", error=str(e))
        return None


def _build_minimax_pooled_provider() -> Any:
    """Construct the pooled MiniMax provider if any MiniMax key is set, else None."""
    if not (settings.minimax_api_key or settings.minimax_api_keys):
        return None
    try:
        from heart.ss08_voice.pooled_provider import PooledTTSProvider

        members = _build_minimax_members()
        if not members:
            return None
        return PooledTTSProvider(
            members,
            max_concurrency=settings.tts_max_concurrency,
            max_retries=settings.tts_max_retries,
            cooldown_seconds=settings.tts_key_cooldown_seconds,
        )
    except Exception as e:
        logger.warning("wiring_minimax_provider_init_failed", error=str(e))
        return None


# Priority for the process-default primary (built-in / unconfigured characters).
_PRIMARY_PRIORITY = ("mimo", "fish", "minimax")
# Fallback order keyed by the primary provider name (mirrors the legacy rules).
_FALLBACK_ORDER = {
    "mimo": ("fish", "minimax"),
    "fish": ("minimax",),
    "minimax": ("mimo",),
}


@lru_cache
def get_tts_provider_registry() -> dict:
    """Process singleton: every configured TTS provider keyed by ``.name``.

    Enables per-character provider selection (character_voices.voice_provider)
    at synthesis time — a Fish-cloned voice must be rendered by Fish, not by the
    process-default primary. Providers absent from the environment are simply
    omitted; callers fall back to the default chain.
    """
    registry: dict = {}
    for build in (_build_mimo_provider, _build_fish_provider, _build_minimax_pooled_provider):
        provider = build()
        if provider is not None:
            registry[provider.name] = provider
    return registry


@lru_cache
def get_voice_service():
    """Process singleton: VoiceService over the full TTS provider registry.

    The primary is chosen by priority (MiMo → Fish → MiniMax) and drives the
    default path for built-in / unconfigured characters. Per-character
    synthesis routing (voice_provider) selects from the registry inside
    VoiceService.synthesize_with_fallback.
    """
    registry = get_tts_provider_registry()
    if not registry:
        logger.warning(
            "wiring_no_voice_provider",
            hint="Set MIMO_API_KEY, FISH_API_KEY, or MINIMAX_API_KEY in .env",
        )
        return None

    primary_provider = next((registry[n] for n in _PRIMARY_PRIORITY if n in registry), None)
    if not primary_provider:
        primary_provider = next(iter(registry.values()))

    fallback_provider = None
    if settings.voice_fallback_enabled:
        fallback_provider = next(
            (registry[n] for n in _FALLBACK_ORDER.get(primary_provider.name, ()) if n in registry),
            None,
        )

    try:
        from heart.ss08_voice.service import VoiceService

        svc = VoiceService(primary_provider, fallback=fallback_provider, providers=registry)
        logger.info(
            "wiring_voice_service_initialized",
            primary=primary_provider.name,
            fallback=fallback_provider.name if fallback_provider else None,
            providers=list(registry.keys()),
        )
        return svc
    except Exception as e:
        logger.warning("wiring_voice_service_init_failed", error=str(e))
        return None


@lru_cache
def get_mimo_asr_provider() -> Any:
    """Process singleton: MiMoProvider for ASR (transcription).

    Returns None when MIMO_API_KEY is not configured.
    """
    if not settings.mimo_api_key:
        return None
    try:
        from heart.ss08_voice.mimo_provider import MiMoProvider

        provider = MiMoProvider(api_key=settings.mimo_api_key, base_url=settings.mimo_base_url)
        logger.info("wiring_mimo_asr_initialized")
        return provider
    except Exception as e:
        logger.warning("wiring_mimo_asr_init_failed", error=str(e))
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

        svc = MemoryService(
            db_session=db_session,
            redis_client=redis_client,
            embedding_service=get_embedding_service(),
        )
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
            text(
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
        logger.error("safety_event_write_failed")
