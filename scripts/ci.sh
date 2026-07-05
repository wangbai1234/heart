#!/usr/bin/env bash
# scripts/ci.sh — Heart 项目最小 CI
#
# 设计目标：
#   - 本地优先：开发者随时 `bash scripts/ci.sh` 跑全套基础检查
#   - 失败立即退出（set -euo pipefail）
#   - 不依赖云端 runner / 主机组 / 容器编排
#   - GitHub Actions 等 CI 也直接调用同一脚本，行为完全一致
#
# 用法：
#   bash scripts/ci.sh                # 等同于 `all`：lint + unit-tests + schema
#   bash scripts/ci.sh lint
#   bash scripts/ci.sh unit-tests
#   bash scripts/ci.sh schema-validation
#   bash scripts/ci.sh integration-tests   # 需要本地 postgres + redis + API key
#
# 退出码：
#   0 成功；1 失败；2 未知 stage
#
# 兼容性：macOS 12+ / Linux（bash 3.2+），不依赖 GNU 专属选项

set -euo pipefail

# ---- 环境变量（CI测试用） ----
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-ci-test-secret-key-do-not-use-in-production-12345678}"
export JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}"
export OTP_PEPPER="${OTP_PEPPER:-ci-test-otp-pepper-not-for-production-12345678}"

# ---- 通用 ----
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

c_green="\033[32m"
c_red="\033[31m"
c_yellow="\033[33m"
c_reset="\033[0m"

log()  { printf "${c_green}[ci]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[ci][warn]${c_reset} %s\n" "$*" >&2; }
die()  { printf "${c_red}[ci][error]${c_reset} %s\n" "$*" >&2; exit 1; }

require_backend() {
    [ -d "$BACKEND_DIR" ]                || die "backend/ not found at $BACKEND_DIR"
    [ -f "$BACKEND_DIR/requirements.txt" ] || die "backend/requirements.txt missing"
}

# 本地默认假定虚拟环境已激活；CI 走 actions/setup-python 后直接安装。
pip_install() {
    pip install --quiet --disable-pip-version-check "$@"
}

# ---- stage: lint ----
stage_lint() {
    log "stage: lint (ruff + mypy)"
    require_backend
    pip_install ruff mypy
    pip_install -r "$BACKEND_DIR/requirements.txt"

    cd "$BACKEND_DIR"
    log "→ ruff check"
    ruff check heart/

    log "→ ruff format --check"
    ruff format --check heart/

    log "→ mypy"
    mypy heart/ --ignore-missing-imports --no-strict-optional || warn "mypy found type errors (non-blocking)"

    log "✓ lint passed"
}

# ---- stage: frontend ----
stage_frontend() {
    log "stage: frontend (tsc + vite build)"
    local web_dir="$REPO_ROOT/web"
    [ -f "$web_dir/package.json" ] || { warn "web/package.json missing; skipping frontend"; return 0; }

    cd "$web_dir"
    if [ ! -d node_modules ]; then
        # 用 npm install（不用 npm ci）：vite 8 的 rolldown 打包器依赖平台原生二进制
        # （@rolldown/binding-<os>-<arch>，作为 optionalDependencies）。单平台机器生成的
        # package-lock.json 只会锁定该平台的 binding（如 darwin-arm64），CI（linux-x64）
        # 用它安装会缺 linux binding → vite build 报 MODULE_NOT_FOUND。
        # 删除任何残留 lockfile 后 npm install，让 npm 按当前平台重新解析并装对原生二进制。
        rm -f package-lock.json
        log "→ npm install (fresh per-platform resolve)"
        npm install --no-audit --no-fund 2>&1 | tail -3
    fi

    log "→ tsc -b"
    npx tsc -b

    log "→ vite build"
    # tail 放宽到 20 行，构建失败时能看到真正的报错而不是被截断成收尾花括号。
    npx vite build 2>&1 | tail -20

    log "✓ frontend passed"
}

# ---- stage: unit-tests ----
stage_unit_tests() {
    log "stage: unit-tests"
    require_backend
    pip_install pytest pytest-asyncio pytest-cov pytest-mock
    pip_install -r "$BACKEND_DIR/requirements.txt"

    cd "$BACKEND_DIR"
    pytest tests/unit -v --cov=heart --cov-report=term

    log "✓ unit-tests passed"
}

# ---- stage: schema-validation ----
stage_schema_validation() {
    log "stage: schema-validation"
    cd "$REPO_ROOT"
    pip_install pyyaml

    python3 - <<'PYEOF'
import sys, yaml
from pathlib import Path

errors = []

def validate(d: Path, multi_doc: bool = False) -> None:
    if not d.exists():
        print(f"  (skip) {d} not present")
        return
    for f in d.rglob("*.yaml"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                if multi_doc:
                    list(yaml.safe_load_all(fh))
                else:
                    yaml.safe_load(fh)
            print(f"  ✓ {f}")
        except Exception as e:
            errors.append(f"  ✗ {f}: {e}")
            print(errors[-1])

validate(Path("soul_specs"))
validate(Path("config"))
validate(Path("backend/infra/kubernetes"), multi_doc=True)

if errors:
    print(f"\n{len(errors)} YAML validation error(s)")
    sys.exit(1)
print("\nall YAML files valid")
PYEOF

    log "✓ schema-validation passed"
}

# ---- stage: integration-tests (opt-in) ----
stage_integration_tests() {
    log "stage: integration-tests (opt-in)"
    require_backend

    : "${DATABASE_URL:?integration-tests requires DATABASE_URL}"
    : "${REDIS_URL:?integration-tests requires REDIS_URL}"
    : "${DEEPSEEK_API_KEY:?integration-tests requires DEEPSEEK_API_KEY}"

    pip_install pytest pytest-asyncio asyncpg redis alembic
    pip_install -r "$BACKEND_DIR/requirements.txt"

    cd "$BACKEND_DIR"
    if [ -f alembic.ini ]; then
        log "→ alembic upgrade head"
        alembic upgrade head || warn "alembic migrations failed; continuing"
    fi

    pytest tests/integration -v

    log "✓ integration-tests passed"
}

# ---- dispatch ----
stage="${1:-all}"

case "$stage" in
    lint)                stage_lint ;;
    unit-tests)          stage_unit_tests ;;
    schema-validation)   stage_schema_validation ;;
    frontend)            stage_frontend ;;
    integration-tests)   stage_integration_tests ;;
    all)
        stage_lint
        stage_unit_tests
        stage_schema_validation
        stage_frontend
        log "✓ all default stages passed (lint + unit-tests + schema + frontend)"
        ;;
    -h|--help|help)
        sed -n '1,30p' "$0"
        exit 0
        ;;
    *)
        die "unknown stage: $stage (use: lint | unit-tests | schema-validation | frontend | integration-tests | all)"
        ;;
esac
