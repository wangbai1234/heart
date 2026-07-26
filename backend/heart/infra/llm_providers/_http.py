"""Shared httpx client construction for LLM providers.

Every provider talks to its upstream over the same kind of link — often a
cross-border hop (e.g. an HK app server → a US-fronted relay). They used to each
hand-roll ``httpx.AsyncClient(base_url=..., headers=..., timeout=...)`` with no
connection tuning, so this centralizes it: change the transport policy once here
instead of in four places.
"""

from __future__ import annotations

from typing import Dict, Optional

import httpx

# httpx's default keepalive_expiry is 5s: any gap >5s between turns drops the
# pooled connection, so the next turn pays a fresh TLS handshake. On a long-haul
# link that handshake is several RTTs (hundreds of ms) of pure first-token
# latency. Hold the connection warm for 5 minutes, and cap the pool so a burst
# can't hoard sockets against the vendor's per-account concurrency limit.
_LIMITS = httpx.Limits(max_keepalive_connections=20, keepalive_expiry=300.0)


def make_async_client(
    base_url: Optional[str],
    headers: Dict[str, str],
    timeout: float,
) -> httpx.AsyncClient:
    """AsyncClient tuned for streaming LLM calls (warm keepalive over long-haul)."""
    return httpx.AsyncClient(
        base_url=base_url or "",
        headers=headers,
        timeout=timeout,
        limits=_LIMITS,
    )
