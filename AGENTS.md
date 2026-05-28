# AGENTS.md — Heart (心屿)

## Session entry

**Start every session by reading `docs/PROJECT_STATUS.md`.** It is the single source of truth: current phase, active blockers, next steps. The README also says this.

## Tech & architecture

- **Stack**: Python 3.11, FastAPI, PostgreSQL 15+ (pgvector), Redis 7, SQLAlchemy 2.0 + Alembic, Docker
- **Entrypoint**: `uvicorn heart.api.main:app` (inside `backend/`)
- **8 subsystems (SS01–SS08)**: Soul → Memory → Emotion → Relationship → Composer → Inner State → Orchestration → Infrastructure
- **Spec-driven**: `runtime_specs/0X_*.md` is authoritative. Do not drift from it.
- **Modular monolith** under `backend/heart/`. Subsystems are plain packages; no microservices yet.
- **SS03–SS07 code** is on `feature/ss04-stage-engine`, not on `main`. Check which branch is relevant.
- **JWT uses RS256**, not HS256. Keys are in `.env`.

## Commands (always from repo root)

```bash
# Canonical CI — local and CI run identically
bash scripts/ci.sh                    # lint + unit-tests + schema-validation
bash scripts/ci.sh lint
bash scripts/ci.sh unit-tests
bash scripts/ci.sh integration-tests  # opt-in; needs postgres + redis + DEEPSEEK_API_KEY

# Quick bootstrap
make bootstrap      # docker-up + pip install + migrate
make dev            # start API on :8000
make test           # pytest with coverage
make lint           # ruff + mypy
make format         # ruff format

# Single module tests
cd backend && pytest tests/unit/ss01_soul -v
```

- All python commands run inside `backend/`. Use `make …` or `cd backend && …`.
- Prefer `python3.11` over bare `python3` — CI enforces 3.11.
- Tests have markers: `pytest -m 'not live and not requires_postgres'` is the default filter.
- Migration tip: `alembic upgrade heads` (plural) — there may be multiple heads.

## Git & branching

- **Never commit directly to main.** Use feature branches + PR.
- **Never commit `.env` / secrets / API keys.**
- Commit format: `type: description` (types: `feat fix refactor test ci docs chore`).
- Force-push to main is forbidden. Tag and release are manual.
- No hard deletes on user data — use logical delete.
- Existing branch: `feature/ss04-stage-engine` (super-branch with SS03–SS07, not yet in main).

## Key gotchas

- **Two LLM provider trees** exist (`infra/llm/` and `infra/llm_providers/`) — known debt, do not add to the split.
- **`engineering_execution/EXECUTION_PLAN.md`** is 97KB of historical planning; do not read it fully. Use `docs/PROJECT_STATUS.md` instead.
- **Archived content** is in `archive/`. Do not delete it — it preserves decision history.
- **Subsystem specs** in `runtime_specs/` are the contract. Code that contradicts them is a bug, not a feature.
- **CI is minimal**: `scripts/ci.sh` is the only pipeline. Old Gitee Go workflows are archived.
- **JWT secret**: `JWT_ALGORITHM=RS256` (in `.env`). Generate key with `openssl rand -hex 32`.

## Project status snapshot (2026-05-24)

- Phase 6 done, Phase 7 blocked by **Top 10 architecture audit findings** (41 total).
- Priority: fix critical blockers (#1–#4 in `docs/PROJECT_STATUS.md`) before starting Phase 7.
- Current active branches: `feat/misc-updates` (repo refactor), `feature/ss04-stage-engine` (main work).
