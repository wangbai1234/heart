# Tier E — End-to-End Tests

Real HTTP path: `uvicorn → FastAPI → Orchestrator → Composer → LLM` + DB verification.

## What's different from Tier B / C

| Tier | HTTP server | DB | LLM | Purpose |
|---|---|---|---|---|
| B integration | ❌ (in-proc) | ✅ real (testcontainers) | ❌ fake | wire integration |
| C live | ❌ (constructs services by hand) | ❌ none | ✅ real DeepSeek | LLM behavior |
| **E e2e** | **✅ real uvicorn subprocess** | **✅ real PG (local)** | fake by default, real opt-in | **prove the whole path** |

## Prereqs

```bash
docker compose up -d postgres redis           # local services
cd backend
alembic upgrade head                          # migrate
pip install -r requirements-dev.txt           # installs pytest-playwright
playwright install chromium                   # one-time; needed even for API ctx
```

## Run

```bash
# default: fake LLM, real PG/Redis
pytest tests/e2e -m e2e -v

# with real DeepSeek (incurs cost)
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... pytest tests/e2e -m e2e -v

# pin port for parallel debugging
HEART_E2E_PORT=8765 pytest tests/e2e -m e2e -v
```

## Env switches

| Var | Default | Meaning |
|---|---|---|
| `HEART_E2E` | unset | `true` enables tests without `-m e2e` |
| `HEART_E2E_PORT` | random | pin uvicorn port |
| `HEART_E2E_PG_DSN` | `dbname=heart user=heart password=heartdev host=localhost port=5432` | psycopg2 DSN for verification queries |
| `DATABASE_URL` | `postgresql+asyncpg://heart:heartdev@localhost:5432/heart` | server-side DB URL |
| `REDIS_URL` | `redis://localhost:6379/0` | server-side Redis URL |
| `LLM_PROVIDER` | `fake` | set to `deepseek` for real LLM |

## Adding browser tests later

When a frontend lands, add `playwright.sync_api.Browser`-based tests in this same
directory — the `e2e_server` fixture already gives you a running app:

```python
def test_ui_flow(e2e_server, page):
    page.goto(e2e_server)
    page.get_by_role("button", name="Login").click()
    ...
```
