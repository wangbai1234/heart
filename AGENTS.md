# AGENTS.md — Heart (心屿)

## Session entry

**Start every session by reading `docs/PROJECT_STATUS.md`.** It is the single source of truth: current phase, active blockers, next steps. The README also says this.

**Claude Code 自动行为**: 每个 session 开始时自动读取 `.claude/CLAUDE.md`；当任务匹配时自动加载 `.claude/skills/` 下对应的技能（如 e2e-test）。无需手动指定。

## Tech & architecture

- **Stack**: Python 3.11, FastAPI, PostgreSQL 15+ (pgvector), Redis 7, SQLAlchemy 2.0 + Alembic, Docker
- **Entrypoint**: `uvicorn heart.api.main:app` (inside `backend/`)
- **8 subsystems (SS01–SS08)**: Soul → Memory → Emotion → Relationship → Composer → Inner State → Orchestration → Infrastructure
- **Spec-driven**: `runtime_specs/0X_*.md` is authoritative. Do not drift from it.
- **Modular monolith** under `backend/heart/`. Subsystems are plain packages; no microservices yet.
- **SS03–SS07 code** is on `main`（已通过 PR #17 集成）。`feature/ss04-stage-engine` 已完成使命。
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

## Testing — Tier E End-to-End

Real path: uvicorn subprocess → FastAPI → Orchestrator → PostgreSQL. Use this to prove a change
works end-to-end (not just unit/integration mocks). Default uses fake LLM; opt into real with env vars.

```bash
# Prerequisites (one-time)
docker compose up -d postgres redis
cd backend && alembic upgrade head
pip install -r requirements-dev.txt
python -m playwright install chromium

# Run (opt-in by default)
pytest tests/e2e -m e2e -v           # fake LLM
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-... pytest tests/e2e -m e2e -v  # real DeepSeek
```

**Files**:
- `backend/tests/e2e/` — test suite (login → chat → DB assertion)
- `.claude/skills/e2e-test/SKILL.md` — detailed SOP (when to run, how to diagnose failures)

## Integration verification tiers (CI error handling)

CI / lint / type-check errors are handled by tier:

| Tier | Type | Disposition |
|------|------|-------------|
| **A** | Functional errors (test failures, import errors, runtime crashes) | Stop immediately. Must fix or revert. No noqa/config relaxation. |
| **B** | **New** lint/type errors introduced by the integration (baseline diff proves baseline is clean) | Same as Tier A. No silent passing. |
| **C** | **Existing** debt carried from source branch (baseline diff proves it exists) | Non-blocking, but requires "debt registration ceremony" (see below). |
| **D** | Domain convention vs lint rule conflict (math symbols `L/N/K`, etc.) | Local `# noqa: <rule> — <domain reason>`, one comment per occurrence. |

**Debt registration ceremony** (Tier C only, all three steps required):
1. Register in `pyproject.toml` with `per-file-ignores`, with issue number and sunset date comment.
2. Open a tracking issue listing each debt (file/line/fix suggestion/sunset).
3. Add `## Imported Tech Debt` section in the integration PR body referencing the issue.

**Prohibitions**: global ruff/mypy rule relaxation, unjustified `# noqa`, disguising A/B as C, `per-file-ignores` without issue link + sunset comment.

## Git & branching

- **Never commit directly to main.** Use feature branches + PR.
- **Never commit `.env` / secrets / API keys.**
- Commit format: `type: description` (types: `feat fix refactor test ci docs chore`).
- Force-push to main is forbidden. Tag and release are manual.
- No hard deletes on user data — use logical delete.
- Existing branch: `feature/ss04-stage-engine` (super-branch with SS03–SS07, not yet in main).

## Key gotchas

- **Two LLM provider trees** exist (`infra/llm/` and `infra/llm_providers/`) — known debt, do not add to the split.
- **`archive/execution/EXECUTION_PLAN.md`** is 97KB of historical planning; do not read it fully. Use `docs/PROJECT_STATUS.md` instead.
- **Archived content** is in `archive/`. Do not delete it — it preserves decision history.
- **Subsystem specs** in `runtime_specs/` are the contract. Code that contradicts them is a bug, not a feature.
- **CI is minimal**: `scripts/ci.sh` is the only pipeline. Old Gitee Go workflows are archived.
- **JWT secret**: `JWT_ALGORITHM=RS256` (in `.env`). Generate key with `openssl rand -hex 32`.

## Project status snapshot (2026-06-04)

- Phase 7 verification completed — all 7 phases passed.
- SS03-07 merged to main (PR #17), governance merged (PR #16).
- Safety wiring verified: real SafetyAgent + CarePathHandler + 14 templates + _routing.yaml.
- Remaining blocker: #4 dual LLM provider tree.
- Next: Phase 7 implementation (integration test pyramid + soul drift regression).
- Current active branch: `main`.
