#!/usr/bin/env bash
# scripts/local-startup.sh — Heart 项目一键启动脚本
#
# 用途：完全初始化本地开发环境并启动服务器
# 前置条件：
#   - Docker Desktop (或 docker + docker compose)
#   - Python 3.11+ (python3 or python3.11)
#   - 已复制 .env.example → .env （至少设置 JWT_SECRET_KEY）
#
# 用法：
#   bash scripts/local-startup.sh          启动（docker + deps + migrate + dev server）
#   bash scripts/local-startup.sh --setup  仅初始化环境，不启动 server
#   bash scripts/local-startup.sh --test   跑完整测试流程
#   bash scripts/local-startup.sh --clean  停止所有 docker + 清缓存

set -euo pipefail

# 颜色
c_green="\033[32m"
c_blue="\033[34m"
c_yellow="\033[33m"
c_red="\033[31m"
c_reset="\033[0m"

log()  { printf "${c_green}[startup]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

# Detect python3 binary (prefer explicit version if available)
PYTHON3="python3"
if command -v python3.11 &>/dev/null; then
    PYTHON3="python3.11"
elif command -v python3.12 &>/dev/null; then
    PYTHON3="python3.12"
elif ! command -v python3 &>/dev/null; then
    die "python3 未找到。请安装 Python 3.11+"
fi

# Detect docker compose command (v2 preferred, fall back to v1)
if docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    die "docker compose 未找到。请安装 Docker Desktop 或 Docker Engine + Compose plugin"
fi

# ---- 前置条件检查 ----
check_prerequisites() {
    log "检查前置条件..."

    # Docker
    if ! command -v docker &>/dev/null; then
        die "docker 未找到。请安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
    fi

    # .env
    if [ ! -f "$REPO_ROOT/.env" ]; then
        die "$REPO_ROOT/.env 不存在。请先: cp .env.example .env  （并填写 JWT_SECRET_KEY 等必填项）"
    fi

    info "✓ 前置条件 OK (python: $PYTHON3, compose: $DOCKER_COMPOSE)"
}

# ---- 启动 Docker ----
docker_up() {
    log "启动 Docker 服务（postgres + redis）..."
    cd "$REPO_ROOT"
    $DOCKER_COMPOSE up -d postgres redis

    log "等待服务就绪（最多 30 秒）..."
    for i in $(seq 1 30); do
        if $DOCKER_COMPOSE ps postgres | grep -q "healthy"; then
            info "✓ postgres 已就绪"
            break
        fi
        sleep 1
    done

    for i in $(seq 1 30); do
        if $DOCKER_COMPOSE ps redis | grep -q "healthy"; then
            info "✓ redis 已就绪"
            break
        fi
        sleep 1
    done
}

# ---- 安装依赖 ----
install_deps() {
    log "安装 Python 依赖..."
    cd "$BACKEND_DIR"
    $PYTHON3 -m pip install -q --disable-pip-version-check -e ".[dev]"
    info "✓ 依赖安装完成"
}

# ---- 数据库迁移 ----
run_migrations() {
    log "运行数据库迁移..."
    cd "$BACKEND_DIR"

    # Show current state first
    $PYTHON3 -m alembic current 2>&1 | grep -v "^$" || true

    # This project has a multi-head Alembic DAG. "alembic upgrade heads" upgrades all
    # heads in one pass. If this fails with "Multiple head revisions", run each head
    # explicitly:
    #   alembic upgrade 022_identity_narrative_backfill
    #   alembic upgrade 031_preset_voice_sample_endpoint
    $PYTHON3 -m alembic upgrade heads 2>&1 | grep -v "^$"

    info "✓ 迁移完成（运行 'alembic current' 验证两个 head 都显示 (head)）"
}

# ---- 启动开发服务器 ----
start_dev_server() {
    log "启动 FastAPI 开发服务器..."
    echo ""
    cd "$BACKEND_DIR"
    $PYTHON3 -m uvicorn heart.api.main:app --reload --host 127.0.0.1 --port 8000
}

# ---- 完整测试流程 ----
run_tests() {
    log "测试核心 endpoint..."
    sleep 3

    BASE_URL="http://localhost:8000"

    echo ""
    info "1️⃣  GET /"
    curl -s "$BASE_URL/" | $PYTHON3 -m json.tool || true
    echo ""

    info "2️⃣  GET /health/live"
    curl -s "$BASE_URL/health/live" | $PYTHON3 -m json.tool || true
    echo ""

    info "3️⃣  GET /health/ready"
    curl -s "$BASE_URL/health/ready" | $PYTHON3 -m json.tool || true
    echo ""

    info "4️⃣  POST /api/auth/otp/request (OTP login flow)"
    curl -s -X POST "$BASE_URL/api/auth/otp/request" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com"}' | $PYTHON3 -m json.tool || true
    echo ""

    warn "基础 endpoint 测试完成"
    warn "完整登录需要 OTP 验证码（见邮箱），请在浏览器打开 http://localhost:5173 测试"
}

# ---- 清理 ----
cleanup() {
    log "停止 Docker + 清缓存..."
    cd "$REPO_ROOT"
    $DOCKER_COMPOSE down || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    info "✓ 清理完成"
}

# ---- 主流程 ----
main() {
    local mode="${1:-start}"

    case "$mode" in
        --setup)
            check_prerequisites
            docker_up
            install_deps
            run_migrations
            echo ""
            log "✅ 环境初始化完成"
            echo ""
            echo "下一步，启动开发服务器："
            echo "  cd backend"
            echo "  $PYTHON3 -m uvicorn heart.api.main:app --reload --host 127.0.0.1 --port 8000"
            ;;
        --test)
            run_tests
            ;;
        --clean)
            cleanup
            ;;
        start|"")
            check_prerequisites
            docker_up
            install_deps
            run_migrations
            echo ""
            log "✅ 初始化完成，启动服务器..."
            echo ""
            start_dev_server
            ;;
        -h|--help|help)
            sed -n '1,25p' "$0"
            echo ""
            echo "用法："
            echo "  bash scripts/local-startup.sh          启动（docker + deps + migrate + dev server）"
            echo "  bash scripts/local-startup.sh --setup  仅初始化环境，不启动 server"
            echo "  bash scripts/local-startup.sh --test   跑完整测试流程"
            echo "  bash scripts/local-startup.sh --clean  停止所有 docker + 清缓存"
            ;;
        *)
            die "未知选项: $mode （用 --help 查看帮助）"
            ;;
    esac
}

main "$@"
