"""Loopback-only boundary for browsing a restored production catalogue locally."""

from ipaddress import ip_address

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class LocalReviewOnlyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode("ascii", errors="ignore").split(":")[0]
        try:
            local_peer = ip_address((scope.get("client") or ("",))[0]).is_loopback
        except ValueError:
            local_peer = False
        allowed = (
            local_peer
            and host in {"localhost", "127.0.0.1"}
            and not any(
                key in headers
                for key in (b"cf-connecting-ip", b"cf-ray", b"forwarded", b"x-forwarded-host")
            )
        )
        if allowed:
            await self.app(scope, receive, send)
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": "Local review only"})
        else:
            await JSONResponse({"detail": "Local review only"}, status_code=403)(
                scope, receive, send
            )


def configure_local_review(app: FastAPI, enabled: bool) -> None:
    if enabled:
        app.add_middleware(LocalReviewOnlyMiddleware)


async def review_catalog_records(db, enabled: bool) -> dict:
    if not enabled:
        return {}
    from sqlalchemy import text

    result = await db.execute(
        text(
            "SELECT character_id, batch_id, original_visibility, original_status, "
            "original_review_status FROM local_review.character_visibility"
        )
    )
    return {row["character_id"]: {"local_review": dict(row)} for row in result.mappings()}
