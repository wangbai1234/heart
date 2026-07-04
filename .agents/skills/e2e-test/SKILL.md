---
name: e2e-test
description: Run the Heart project's Tier E end-to-end tests (real uvicorn + real Postgres + Playwright APIRequestContext). Use this when the user asks to "test the real path", "run e2e", "verify end-to-end", or after a backend change that touches the HTTP / orchestrator / DB pipeline and they want proof it works against the real stack — not just unit/integration mocks. Spins up local services if needed, runs `pytest tests/e2e -m e2e`, summarizes failures.
---

# Heart Tier E — Real-Path Test Runner

Drives `backend/tests/e2e/` against the **real** stack:
uvicorn subprocess → FastAPI → Orchestrator → Composer → LLM → Postgres.

Tier B uses fake LLM + testcontainers DB. Tier C uses real LLM but constructs services
by hand (no HTTP). **Tier E is the only layer that proves the full wired path.**

## When to invoke

- "run e2e", "test the real path", "verify end-to-end", "check the wiring"
- After changing: `heart/api/`, `heart/ss07_orchestration/`, `heart/ss05_composer/`,
  any `migrations/`, or DI in `heart/api/wiring.py`
- Before merging any PR that touches the hot path

## Standard procedure

Execute these steps in order. Stop and report on the **first** failure — don't paper over.

### 1. Prereqs check

```bash
# Postgres up?
docker compose ps postgres | grep -q "Up" || docker compose up -d postgres
# Redis up?
docker compose ps redis | grep -q "Up" || docker compose up -d redis
# Migrated to head?
cd backend && alembic current | grep -q "head" || alembic upgrade head
```

If `docker compose` is not running, ask the user before launching containers.
If migrations need to run, ask before applying.

### 2. Python deps

```bash
cd backend
pip install -r requirements-dev.txt   # idempotent
python -m playwright install chromium # one-time per machine; safe to re-run
```

### 3. Run the suite

```bash
cd backend
pytest tests/e2e -m e2e -v
```

Default uses **fake LLM**. For real-LLM E2E (incurs cost):

```bash
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=... pytest tests/e2e -m e2e -v
```

### 4. On failure — diagnose, don't retry blindly

Look at the **first** failing test and check in this order:

1. Did uvicorn fail to start? Look for `uvicorn failed to start` in pytest output.
   - Common: missing env vars (`JWT_SECRET_KEY`), bad `DATABASE_URL`, port in use.
2. Did `/api/health/ready` time out?
   - Server started but a dependency (PG / Redis) is unreachable.
3. Did login return non-200?
   - Auth wiring broken; check `heart/core/auth.py` and `routes.py:60`.
4. Did chat return 500?
   - Check uvicorn stdout (captured in subprocess) and the orchestrator path.
5. Did DB assertion fail (no `sessions` row)?
   - Orchestrator's `SessionManager.record_turn` not reaching DB, or transaction not committed.

### 5. Report

Always end with:
- ✅ pass count / ❌ fail count
- For failures: file:line + one-line root cause hypothesis
- Total wall-clock time
- Cost (if real LLM was used)

Do **not** mark the task complete if any e2e test failed — failures here mean the
real path is broken, even if unit tests pass.

## Adding new e2e tests

Place them in `backend/tests/e2e/`. Use:

- `api_context` fixture → Playwright APIRequestContext bound to the running server
- `pg_conn` fixture → psycopg2 connection for DB assertions
- `clean_demo_user` fixture → deterministic per-test cleanup
- Mark every class/function with `@pytest.mark.e2e`

When the frontend lands, add browser-driven tests in the same dir using the standard
`page` fixture — `e2e_server` already gives you a running app to navigate to.

## Files this skill operates on

- `backend/tests/e2e/` — the suite
- `backend/pyproject.toml` — `e2e` marker registered, excluded by default `addopts`
- `backend/requirements-dev.txt` — pytest-playwright + playwright
- `docker-compose.yml` — `postgres` and `redis` services
