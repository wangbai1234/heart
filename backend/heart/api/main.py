"""
Heart API Main Application

FastAPI application entry point with health endpoints and middleware.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env into os.environ for the real server process only, so raw os.getenv
# flags that are NOT pydantic Settings fields (HEART_DEV_MODE, HEART_WORKERS_ENABLED,
# HEART_INNER_LOOP_ENABLED, ...) take effect from .env. Skipped under pytest so the
# test process never inherits dev-only flags (e.g. HEART_DEV_MODE=true would register
# the dev auth/login stub). override=False keeps real process env authoritative.
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists() and "pytest" not in sys.modules:
    load_dotenv(_env_path, override=False)

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.responses import Response

from .routes import dev_auth_router, router
from .routes import dev_router as profile_dev_router
from .routes_account import router as account_router
from .routes_auth import router as auth_router
from .routes_characters import router as characters_router
from .routes_chat_ws import router as chat_ws_router
from .routes_credits import router as credits_router
from .routes_proactive import router as proactive_router
from .routes_profile import router as profile_router
from .routes_state import dev_router, memory_router
from .routes_state import router as state_router
from .routes_voice import router as voice_router
from .routes_webhooks import router as webhooks_router

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "heart_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "heart_api_request_duration_seconds",
    "API request latency",
    ["method", "endpoint"],
)


async def _startup():
    """Application startup: init LLM router + start workers."""
    import os

    from heart.core.config import settings

    os.environ.setdefault("DEEPSEEK_API_KEY", settings.deepseek_api_key or "")
    if settings.deepseek_base_url:
        os.environ.setdefault("DEEPSEEK_BASE_URL", settings.deepseek_base_url)

    from heart.infra.llm import initialize_router

    await initialize_router(config=None)
    logger.info("llm_router_initialized")

    from heart.workers.runner import start_workers

    await start_workers()


async def _shutdown():
    """Application shutdown: stop workers + cleanup."""
    from heart.workers.runner import stop_workers

    await stop_workers()

    from heart.infra.llm import shutdown_router

    await shutdown_router()
    logger.info("shutdown_complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager (replaces deprecated on_event)."""
    await _startup()
    from heart.core.config import settings

    try:
        settings.validate_jwt_secret()
    except RuntimeError as e:
        logger.warning("jwt_secret_invalid", error=str(e))

    # Check migration drift — logs ERROR if disk heads ≠ alembic_version rows.
    try:
        from heart.api.wiring import _get_engine
        from heart.infra.migration_check import check_migration_drift

        await check_migration_drift(_get_engine())
    except Exception as _exc:
        logger.warning("migration_check_failed", error=str(_exc))

    # Warm DB-sourced UGC soul specs and character content overlays.
    # Uses a short-lived connection so the pool is not held during the full
    # lifespan.  Failure is non-fatal: the service starts with file specs only.
    try:
        from heart.api.wiring import _get_engine
        from heart.ss01_soul.character_content import CharacterContent, register_content
        from heart.ss01_soul.content_store import fetch_all_content
        from heart.ss01_soul.registry import get_soul_registry
        from heart.ss01_soul.spec_store import fetch_active_specs

        async with _get_engine().connect() as conn:
            spec_rows = await fetch_active_specs(conn)
            content_rows = await fetch_all_content(conn)

        report = get_soul_registry().load_db_overlay(spec_rows)
        logger.info(
            "soul_spec_db_overlay_warm",
            loaded=len(report.loaded),
            skipped=len(report.skipped),
        )

        for crow in content_rows:
            cid = crow["character_id"]
            templates = crow["proactive_templates"]
            if isinstance(templates, str):
                import json as _json

                templates = _json.loads(templates)
            register_content(
                cid,
                CharacterContent(
                    proactive_persona=crow["proactive_persona"] or "",
                    proactive_templates=templates or [],
                    ritual_morning=crow["ritual_morning"] or "",
                    ritual_night=crow["ritual_night"] or "",
                ),
            )
        logger.info("character_content_overlay_warm", count=len(content_rows))
    except Exception as _exc:
        logger.warning("db_overlay_warm_failed", error=str(_exc))

    yield
    await _shutdown()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Heart AI Companion API",
        version="0.1.0",
        description="Backend API for Heart AI Companion system",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware — configurable via CORS_ALLOWED_ORIGINS env var
    from heart.core.config import settings

    cors_origins = [
        o.strip() for o in getattr(settings, "cors_allowed_origins", "").split(",") if o.strip()
    ] or ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware
    @app.middleware("http")
    async def logging_middleware(request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        logger.info(
            "api_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )

        # Prometheus metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response

    # Health endpoints
    @app.get("/health/live")
    async def liveness():
        """Kubernetes liveness probe."""
        return {"status": "alive"}

    @app.get("/health/ready")
    async def readiness():
        """Kubernetes readiness probe — checks DB and Redis connectivity."""
        components = {"api": "ok"}

        # Check DB connectivity
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            from heart.core.config import settings

            engine = create_async_engine(settings.database_url, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            components["database"] = "ok"
            await engine.dispose()
        except Exception:
            components["database"] = "unavailable"

        # Check Redis connectivity
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url or "redis://localhost:6379")
            await r.ping()
            components["redis"] = "ok"
            await r.close()
        except Exception:
            components["redis"] = "unavailable"

        all_ok = all(v == "ok" for v in components.values())
        return {
            "status": "ready" if all_ok else "degraded",
            "components": components,
        }

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type="text/plain")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "Heart AI Companion API",
            "version": "0.1.0",
            "status": "running",
        }

    # Include API routes
    app.include_router(router)
    app.include_router(auth_router)  # /api/auth/* (OTP, refresh, logout, me)
    app.include_router(credits_router)  # /api/credits/* (balance, transactions, redeem, pricing)
    app.include_router(webhooks_router)  # /api/webhooks/* (afdian)
    app.include_router(profile_router)  # /api/profile/* (GET/PATCH profile, avatar)
    app.include_router(account_router)  # /api/account/* (clear, delete, export)
    app.include_router(characters_router)  # /api/characters/* (voice settings)
    app.include_router(proactive_router)
    app.include_router(state_router)
    app.include_router(memory_router)
    app.include_router(voice_router)
    app.include_router(chat_ws_router)

    # Dev-only routes: gated behind HEART_DEV_MODE (process env takes precedence over .env)
    if os.environ.get("HEART_DEV_MODE", "").lower() == "true":
        app.include_router(dev_router)  # /api/dev/*
        app.include_router(profile_dev_router, prefix="/api/profile")  # /api/profile/*
        app.include_router(dev_auth_router)  # /api/auth/login (stub, dev only)

    # Rate limiting
    from .rate_limit import limiter

    app.state.limiter = limiter

    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    # OpenTelemetry instrumentation
    FastAPIInstrumentor.instrument_app(app)

    logger.info("heart_api_initialized", version="0.1.0")

    return app


app = create_app()
