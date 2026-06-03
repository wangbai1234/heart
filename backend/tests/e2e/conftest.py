"""Tier E E2E fixtures — uvicorn subprocess + Playwright API context + raw DB.

Design:
    - session-scope `e2e_server`: spawns `uvicorn heart.api.main:create_app --factory`
      on a free port, waits for /api/health/ready, yields base_url, SIGTERMs on teardown.
    - session-scope `api_context`: Playwright sync APIRequestContext bound to base_url.
    - function-scope `pg_conn`: psycopg2 connection to the same Postgres the server uses.
    - function-scope `clean_demo_user`: deletes any prior session rows for the test user
      so each run starts deterministic.

Opt-in: tests are skipped unless `-m e2e` or `HEART_E2E=true`.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Iterator
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

# ─── opt-in gate ──────────────────────────────────────────────────────


def _e2e_enabled(config: pytest.Config) -> bool:
    if os.environ.get("HEART_E2E", "").lower() in ("1", "true", "yes"):
        return True
    markexpr = config.getoption("-m", default="") or ""
    return "e2e" in markexpr


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _e2e_enabled(config):
        return
    skip = pytest.mark.skip(reason="E2E disabled (use -m e2e or HEART_E2E=true)")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


# ─── helpers ──────────────────────────────────────────────────────────


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(base_url: str, timeout_s: float = 30.0) -> None:
    import httpx

    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/health/ready", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(0.3)
    raise RuntimeError(f"server at {base_url} did not become ready: {last_err}")


# ─── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def e2e_server() -> Iterator[str]:
    """Start uvicorn in a subprocess; yield base URL; tear down."""
    port = int(os.environ.get("HEART_E2E_PORT", _free_port()))
    base_url = f"http://127.0.0.1:{port}"

    repo_root = Path(__file__).resolve().parents[3]
    backend_dir = repo_root / "backend"

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql+asyncpg://heart:heartdev@localhost:5432/heart")
    env.setdefault("REDIS_URL", "redis://localhost:6379/0")
    env.setdefault("LLM_PROVIDER", "fake")  # default to fake LLM; override to test real
    env.setdefault("HEART_TURN_PROFILER", "1")
    # Stable JWT secret for the run
    env.setdefault("JWT_SECRET_KEY", "e2e-test-secret-not-for-prod-do-not-reuse")

    proc = subprocess.Popen(
        [
            "uvicorn",
            "heart.api.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(backend_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_ready(base_url)
    except Exception:
        proc.terminate()
        try:
            out = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
        except Exception:
            out = ""
        raise RuntimeError(f"uvicorn failed to start.\n--- server output ---\n{out}")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def api_context(e2e_server: str):
    """Playwright APIRequestContext — HTTP client with a base URL."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.request.new_context(base_url=e2e_server)
        yield ctx
        ctx.dispose()


@pytest.fixture
def pg_conn():
    """psycopg2 connection for verifying DB side-effects."""
    import psycopg2

    dsn = os.environ.get(
        "HEART_E2E_PG_DSN",
        "dbname=heart user=heart password=heartdev host=localhost port=5432",
    )
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()


# ─── demo user identity ───────────────────────────────────────────────

DEMO_USER_ID = "e2e_demo_user"
DEMO_CHARACTER_ID = "rin"


def demo_user_uuid() -> UUID:
    """Same coercion as routes._coerce_uuid for non-UUID user_ids."""
    return uuid5(NAMESPACE_DNS, DEMO_USER_ID)


@pytest.fixture
def clean_demo_user(pg_conn) -> None:
    """Wipe any prior sessions for the demo user so each test starts clean."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM sessions WHERE user_id = %s AND character_id = %s",
            (str(demo_user_uuid()), DEMO_CHARACTER_ID),
        )
    pg_conn.commit()
