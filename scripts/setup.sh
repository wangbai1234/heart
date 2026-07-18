#!/usr/bin/env bash
# scripts/setup.sh — Heart 开发环境一次性初始化
#
# 功能：
#   1. 自动安装缺失的系统包（Ubuntu/Debian）
#   2. 创建 backend/.venv 并安装 Python 依赖
#   3. 安装前端 Node 依赖（web/node_modules）
#   4. 生成 .env（若不存在）
#   5. 启动 Docker 服务 + 运行 DB 迁移
#
# 用法：
#   bash scripts/setup.sh          完整初始化
#   bash scripts/setup.sh --no-db  跳过 Docker + 迁移（仅安装依赖）
#
# 之后每次启动开发服务器：
#   bash scripts/dev.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
WEB_DIR="$REPO_ROOT/web"

c_green="\033[32m"; c_blue="\033[34m"; c_yellow="\033[33m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[setup]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

SKIP_DB=false
[[ "${1:-}" == "--no-db" ]] && SKIP_DB=true

# ──────────────────────────────────────────────────────────────────────────────
# 1. 检测操作系统
# ──────────────────────────────────────────────────────────────────────────────
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ -f /etc/debian_version ]]; then
    OS="debian"
fi
info "OS: $OS"

# ──────────────────────────────────────────────────────────────────────────────
# 2. 找 Python（优先 3.12 → 3.11 → 3）
# ──────────────────────────────────────────────────────────────────────────────
PYTHON3=""
for py in python3.12 python3.11 python3; do
    if command -v "$py" &>/dev/null; then
        PYTHON3="$py"
        break
    fi
done
[[ -z "$PYTHON3" ]] && die "Python 3.11+ 未找到。Ubuntu: sudo apt install python3.12"

PY_VERSION=$($PYTHON3 --version 2>&1)
PY_MINOR=$($PYTHON3 -c "import sys; print(sys.version_info.minor)")
info "Python: $PYTHON3 ($PY_VERSION)"

# ──────────────────────────────────────────────────────────────────────────────
# 3. 安装系统依赖（Ubuntu/Debian 专用）
# ──────────────────────────────────────────────────────────────────────────────
install_system_deps() {
    if [[ "$OS" != "debian" ]]; then
        info "非 Debian 系统，跳过 apt 安装"
        return
    fi

    log "检查系统依赖..."
    local pkgs=()

    # python venv module
    if ! $PYTHON3 -m venv --help &>/dev/null 2>&1; then
        pkgs+=("python3.${PY_MINOR}-venv")
    fi

    # python dev headers（编译某些 pip 包需要）
    if ! dpkg -l "python3.${PY_MINOR}-dev" &>/dev/null 2>&1; then
        pkgs+=("python3.${PY_MINOR}-dev")
    fi

    # node / npm
    if ! command -v node &>/dev/null; then
        pkgs+=(nodejs npm)
        warn "注意：apt 的 nodejs 版本可能较旧（<18）。"
        warn "如遇前端构建问题，建议用 nvm 安装 Node 20："
        warn "  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
        warn "  nvm install 20 && nvm use 20"
    fi

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        log "安装: ${pkgs[*]}"
        sudo apt-get update -qq
        sudo apt-get install -y "${pkgs[@]}"
        info "✓ 系统依赖安装完成"
    else
        info "✓ 系统依赖已就绪"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# 4. 创建并填充 .venv
# ──────────────────────────────────────────────────────────────────────────────
setup_venv() {
    log "设置 Python 虚拟环境..."
    cd "$BACKEND_DIR"

    if [[ ! -d ".venv" ]]; then
        $PYTHON3 -m venv .venv
        info "✓ 创建 .venv ($PYTHON3)"
    else
        info "✓ .venv 已存在"
    fi

    log "安装 Python 依赖..."
    .venv/bin/pip install --quiet --upgrade pip

    # requirements.txt is the authoritative runtime deps list (CI uses it).
    # Install it first, then pyproject.toml [dev] extras + editable install.
    if [[ -f "requirements.txt" ]]; then
        info "  → 安装 requirements.txt（运行时依赖）..."
        .venv/bin/pip install --quiet -r requirements.txt
    fi
    info "  → 安装 pyproject.toml 的 dev 依赖 + editable 包..."
    .venv/bin/pip install --quiet -e ".[dev]"

    # Sanity check：能否 import 关键模块
    if ! .venv/bin/python -c "import slowapi, boto3, pgvector, greenlet, aiosmtplib" 2>/dev/null; then
        die "依赖安装不完整。运行 .venv/bin/pip check 排查。"
    fi
    info "✓ Python 依赖安装完成（关键模块 import OK）"
}

# ──────────────────────────────────────────────────────────────────────────────
# 5. 安装前端依赖
# ──────────────────────────────────────────────────────────────────────────────
setup_frontend() {
    if [[ ! -d "$WEB_DIR" ]]; then
        warn "web/ 目录不存在，跳过前端"
        return
    fi
    if ! command -v node &>/dev/null; then
        warn "node 未找到，跳过前端依赖。安装 node 后重运行此脚本。"
        return
    fi

    NODE_MAJOR=$(node -e "process.stdout.write(String(parseInt(process.versions.node)))")
    if [[ "$NODE_MAJOR" -lt 18 ]]; then
        warn "Node.js $NODE_MAJOR 过旧（需要 ≥18）。请升级再运行前端。"
        return
    fi

    log "安装前端依赖（npm install）..."
    cd "$WEB_DIR"
    npm install --silent
    info "✓ 前端依赖安装完成（Node $NODE_MAJOR）"
}

# ──────────────────────────────────────────────────────────────────────────────
# 6. 生成 .env
# ──────────────────────────────────────────────────────────────────────────────
setup_env() {
    cd "$REPO_ROOT"
    if [[ -f ".env" ]]; then
        info "✓ .env 已存在"
        return
    fi

    log "从 .env.example 生成 .env..."
    cp .env.example .env

    # 自动生成随机密钥（如果 openssl 可用）
    if command -v openssl &>/dev/null; then
        JWT_KEY=$(openssl rand -hex 32)
        OTP_KEY=$(openssl rand -hex 32)
        if [[ "$OS" == "macos" ]]; then
            sed -i '' "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|" .env
            sed -i '' "s|OTP_PEPPER=.*|OTP_PEPPER=$OTP_KEY|" .env
        else
            sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|" .env
            sed -i "s|OTP_PEPPER=.*|OTP_PEPPER=$OTP_KEY|" .env
        fi
        info "✓ JWT_SECRET_KEY 和 OTP_PEPPER 已自动生成"
    fi

    # 本地开发默认启用 workers（memory_promoter / inner_loop / encoder 等）
    # 生产环境由 encoder-worker 容器负责，此处仅影响本地 .env
    if [[ "$OS" == "macos" ]]; then
        sed -i '' "s|^HEART_WORKERS_ENABLED=.*|HEART_WORKERS_ENABLED=true|" .env
    else
        sed -i "s|^HEART_WORKERS_ENABLED=.*|HEART_WORKERS_ENABLED=true|" .env
    fi
    info "✓ HEART_WORKERS_ENABLED=true（本地 dev 完整 worker 模式）"

    echo ""
    warn "⚠️  .env 已创建，请填写以下 API Key（nano .env 或记事本）："
    warn "    DEEPSEEK_API_KEY=sk-..."
    warn "    MINIMAX_API_KEY=sk-api-..."
    warn "    MINIMAX_GROUP_ID=206538..."
    warn "    MINIMAX_RIN_CLONE_VOICE_ID=yuoyuo_rin_v1"
    warn "    MINIMAX_DOROTHY_VOICE_ID=yuoyuo_dorothy_v1"
    echo ""
    read -r -p "$(printf "${c_yellow}[warn]${c_reset} 填完 .env 后按 Enter 继续，或 Ctrl+C 中止... ")"
}

# ──────────────────────────────────────────────────────────────────────────────
# 7. Docker + 数据库迁移
# ──────────────────────────────────────────────────────────────────────────────
setup_db() {
    if $SKIP_DB; then
        info "跳过 DB 初始化（--no-db）"
        return
    fi

    if ! command -v docker &>/dev/null; then
        warn "docker 未找到，跳过 DB 初始化。安装 Docker 后手动运行迁移。"
        return
    fi

    COMPOSE="docker compose"
    if ! docker compose version &>/dev/null 2>&1; then
        command -v docker-compose &>/dev/null && COMPOSE="docker-compose" || {
            warn "docker compose 未找到，跳过 DB 初始化"
            return
        }
    fi

    log "启动 postgres + redis..."
    cd "$REPO_ROOT"
    $COMPOSE up -d postgres redis

    log "等待 postgres 就绪（最多 30s）..."
    for i in $(seq 1 30); do
        if $COMPOSE ps postgres 2>/dev/null | grep -q "healthy"; then
            info "✓ postgres 就绪"
            break
        fi
        [[ "$i" -eq 30 ]] && die "postgres 30s 内未就绪，检查 docker 状态"
        sleep 1
    done

    log "运行数据库迁移（两个 head）..."
    cd "$BACKEND_DIR"
    .venv/bin/python -m alembic upgrade 022_identity_narrative_backfill
    .venv/bin/python -m alembic upgrade 033_chat_messages_is_proactive
    # ⚠️ 商业化 V1（docs/upgrade/yuoyuo_coin）新增迁移 034-037 落地后，
    #    在此追加一行升级到最新 head，例如：
    #    .venv/bin/python -m alembic upgrade 037_invites
    #    否则 dev DB 会缺少会员/邀请/音色 provider 等表（撒谎式绿灯）。

    echo ""
    .venv/bin/python -m alembic current
    echo ""
    info "✓ 数据库迁移完成（两个 head 均显示 (head)）"
}

# ──────────────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────────────
main() {
    echo ""
    log "Heart 开发环境初始化"
    echo "────────────────────────────────────────"

    install_system_deps
    setup_venv
    setup_frontend
    setup_env
    setup_db

    echo ""
    echo "────────────────────────────────────────"
    log "✅ 初始化完成！"
    echo ""
    echo "  下一步启动开发服务器："
    echo ""
    echo "    bash scripts/dev.sh              # 启动 API + 前端（workers 由 .env 决定）"
    echo ""
    info "Workers 说明（memory_promoter / inner_loop / encoder）："
    echo "    .env 已设置 HEART_WORKERS_ENABLED=true"
    echo "    所有 workers 会随 uvicorn 一起启动，无需额外操作"
    echo ""
}

main
