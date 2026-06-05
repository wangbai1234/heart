"""
Heart API Main Application

FastAPI application entry point with health endpoints and middleware.
"""

import time

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy import text
from starlette.responses import Response

from .routes import router
from .routes_proactive import router as proactive_router
from .routes_state import dev_router, memory_router
from .routes_state import router as state_router

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


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Heart AI Companion API",
        version="0.1.0",
        description="Backend API for Heart AI Companion system",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on environment
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
    app.include_router(proactive_router)
    app.include_router(state_router)
    app.include_router(memory_router)
    app.include_router(dev_router)

    # OpenTelemetry instrumentation
    FastAPIInstrumentor.instrument_app(app)

    logger.info("heart_api_initialized", version="0.1.0")

    return app


app = create_app()
