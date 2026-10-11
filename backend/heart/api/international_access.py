"""Fail-closed region enforcement behind a verified edge proxy (HTTP and WS)."""

import hmac

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class InternationalAccessMiddleware:
    def __init__(self, app: ASGIApp, *, enabled: bool, origin_secret: str) -> None:
        self.app = app
        self.enabled = enabled
        self.origin_secret = origin_secret

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled or scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        # Local container probes contain no user content and need no edge headers.
        if scope.get("path") in {"/health/live", "/health/ready"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        provided = headers.get(b"x-yuoyuo-origin", b"")
        country = headers.get(b"cf-ipcountry", b"").decode("ascii", errors="ignore").upper()
        authenticated = bool(self.origin_secret) and hmac.compare_digest(
            provided, self.origin_secret.encode()
        )
        if (
            not authenticated
            or len(country) != 2
            or not country.isalpha()
            or country in {"CN", "XX", "T1"}
        ):
            if scope["type"] == "websocket":
                await send(
                    {"type": "websocket.close", "code": 1008, "reason": "Region unavailable"}
                )
            else:
                await JSONResponse(
                    {
                        "detail": {
                            "code": "regionUnavailable",
                            "message": "Service unavailable in this region.",
                        }
                    },
                    status_code=403,
                    headers={"Cache-Control": "no-store"},
                )(scope, receive, send)
            return
        scope.setdefault("state", {})["edge_country"] = country
        await self.app(scope, receive, send)
