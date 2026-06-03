"""Tier E E2E tests — real HTTP via uvicorn + pytest-playwright + real PostgreSQL.

These tests start a real uvicorn server in a subprocess and drive it through
Playwright's APIRequestContext (no browser required today; ready for browser
tests once a frontend exists).

Run with:
    pytest tests/e2e -m e2e          # opt-in marker
    HEART_E2E=true pytest tests/e2e  # env opt-in (same effect)

Requirements (caller responsibility):
    - PostgreSQL running and migrated (`docker compose up postgres` + `alembic upgrade head`)
    - Redis running (`docker compose up redis`)
    - DEEPSEEK_API_KEY set if you want real LLM (default uses fake)
    - `pip install -r requirements-dev.txt && playwright install chromium`
"""
