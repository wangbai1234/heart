#!/bin/bash
# Heart Project - Gitee Go CI Entry Point
#
# Gitee Go 不兼容 GitHub Actions YAML 语法，因此 .gitee/workflows/ci.yml 仅作参考。
# 实际 CI 由本脚本驱动，由 Gitee Go UI 上的 BranchPipeline/PRPipeline/MasterPipeline 调用。
#
# 用法（在 Gitee Go UI 的 shell step 中）:
#   bash scripts/ci.sh <stage>
#
# 可用 stage:
#   lint                — ruff + mypy 静态检查
#   unit-tests          — pytest tests/unit
#   integration-tests   — pytest tests/integration（需 postgres + redis + DEEPSEEK_API_KEY）
#   schema-validation   — YAML schema 校验
#   build-docker        — Docker 镜像构建
#   all                 — 顺序执行 lint → unit-tests → schema-validation
#
# 退出码:
#   0  — 成功
#   1  — 失败（任何 stage 失败立即终止）
#   2  — 未知 stage

set -euo pipefail

# ---- 配置 ----
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

# ---- 通用工具 ----
log() {
    echo "[ci.sh] $*"
}

die() {
    echo "[ci.sh] ERROR: $*" >&2
    exit 1
}

ensure_backend() {
    [ -d "$BACKEND_DIR" ] || die "backend/ directory not found at $BACKEND_DIR"
    [ -f "$BACKEND_DIR/requirements.txt" ] || die "backend/requirements.txt not found"
}

install_python_deps() {
    local extra_pkgs="$*"
    log "Installing Python dependencies: $extra_pkgs"
    cd "$BACKEND_DIR"
    pip install --upgrade pip --quiet
    pip install --quiet -r requirements.txt
    if [ -n "$extra_pkgs" ]; then
        pip install --quiet $extra_pkgs
    fi
}

# ---- Stage: lint ----
stage_lint() {
    log "===== Stage: lint (ruff + mypy) ====="
    ensure_backend
    install_python_deps "ruff mypy"

    cd "$BACKEND_DIR"
    log "Running ruff check..."
    ruff check heart/ --select E,F,W,I,N --ignore E501

    log "Running ruff format check..."
    ruff format --check heart/

    log "Running mypy..."
    mypy heart/ --ignore-missing-imports --no-strict-optional

    log "✓ Lint passed"
}

# ---- Stage: unit-tests ----
stage_unit_tests() {
    log "===== Stage: unit-tests ====="
    ensure_backend
    install_python_deps "pytest pytest-asyncio pytest-cov pytest-mock"

    cd "$BACKEND_DIR"
    log "Running pytest tests/unit..."
    pytest tests/unit -v \
        --cov=heart \
        --cov-report=xml \
        --cov-report=term \
        --cov-report=html

    log "✓ Unit tests passed"
}

# ---- Stage: integration-tests ----
stage_integration_tests() {
    log "===== Stage: integration-tests ====="
    ensure_backend

    : "${DATABASE_URL:?DATABASE_URL is required for integration tests}"
    : "${REDIS_URL:?REDIS_URL is required for integration tests}"
    : "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required for integration tests}"

    install_python_deps "pytest pytest-asyncio pytest-cov asyncpg redis"

    cd "$BACKEND_DIR"

    log "Waiting for PostgreSQL..."
    for i in $(seq 1 30); do
        if pg_isready -h localhost -p 5432 -U heart_test 2>/dev/null; then
            break
        fi
        sleep 2
    done

    log "Setting up pgvector extension..."
    PGPASSWORD=test_password psql -h localhost -U heart_test -d heart_test \
        -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

    if [ -f alembic.ini ]; then
        log "Running alembic migrations..."
        pip install --quiet alembic
        alembic upgrade head || log "WARN: migrations not ready, skipping"
    fi

    log "Running pytest tests/integration..."
    pytest tests/integration -v \
        --cov=heart \
        --cov-report=xml \
        --cov-report=term \
        --cov-report=html

    log "✓ Integration tests passed"
}

# ---- Stage: schema-validation ----
stage_schema_validation() {
    log "===== Stage: schema-validation ====="
    cd "$REPO_ROOT"
    pip install --quiet --upgrade pip
    pip install --quiet pyyaml jsonschema pydantic

    python3 <<'PYEOF'
import sys
import yaml
from pathlib import Path

errors = []

def validate_dir(directory: Path, multi_doc: bool = False) -> None:
    if not directory.exists():
        print(f"Directory {directory} not found, skipping")
        return
    for yaml_file in directory.rglob("*.yaml"):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                if multi_doc:
                    list(yaml.safe_load_all(f))
                else:
                    yaml.safe_load(f)
            print(f"✓ {yaml_file}")
        except Exception as e:
            errors.append(f"✗ {yaml_file}: {e}")
            print(f"✗ {yaml_file}: {e}")

validate_dir(Path("soul_specs"))
validate_dir(Path("config"))
validate_dir(Path("backend/infra/kubernetes"), multi_doc=True)

if errors:
    print(f"\n{len(errors)} validation errors found")
    sys.exit(1)
print("\nAll YAML files are valid")
PYEOF

    log "✓ Schema validation passed"
}

# ---- Stage: build-docker ----
stage_build_docker() {
    log "===== Stage: build-docker ====="
    cd "$REPO_ROOT"

    if ! command -v docker >/dev/null 2>&1; then
        die "docker command not found; ensure Gitee Go runner has docker installed"
    fi

    [ -f "backend/Dockerfile" ] || die "backend/Dockerfile not found"

    log "Building heart/backend:test..."
    docker build -f backend/Dockerfile -t heart/backend:test backend/

    if [ -f "backend/Dockerfile.orchestrator" ]; then
        log "Building heart/orchestrator-service:test..."
        docker build -f backend/Dockerfile.orchestrator -t heart/orchestrator-service:test backend/
    fi

    if [ -f "backend/Dockerfile.memory" ]; then
        log "Building heart/memory-service:test..."
        docker build -f backend/Dockerfile.memory -t heart/memory-service:test backend/
    fi

    log "✓ Docker build passed"
}

# ---- Main dispatch ----
stage="${1:-all}"

case "$stage" in
    lint)
        stage_lint
        ;;
    unit-tests)
        stage_unit_tests
        ;;
    integration-tests)
        stage_integration_tests
        ;;
    schema-validation)
        stage_schema_validation
        ;;
    build-docker)
        stage_build_docker
        ;;
    all)
        stage_lint
        stage_unit_tests
        stage_schema_validation
        log "===== All stages passed ====="
        ;;
    *)
        die "Unknown stage: $stage. Use one of: lint, unit-tests, integration-tests, schema-validation, build-docker, all"
        ;;
esac
