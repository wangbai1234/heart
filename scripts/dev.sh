#!/usr/bin/env bash
# scripts/dev.sh — Heart 日常开发服务启动
#
# 启动三个服务：
#   - postgres + redis（docker compose）
#   - uvicorn FastAPI（backend/.venv）
#   - Vite dev server（web/）
#
# 用法：
#   bash scripts/dev.sh          启动（tmux 自动分屏，无 tmux 则后台进程）
#   bash scripts/dev.sh --stop   停止所有后台进程
#   bash scripts/dev.sh --logs   查看后台进程日志
#
# 前置条件：先运行 bash scripts/setup.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
WEB_DIR="$REPO_ROOT/web"
PID_DIR="$REPO_ROOT/.dev-pids"
LOG_DIR="/tmp/heart-dev"
SESSION="heart-dev"

c_green="\033[32m"; c_blue="\033[34m"; c_yellow="\033[33m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[dev]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

# ──────────────────────────────────────────────────────────────────────────────
# 前置检查
# ──────────────────────────────────────────────────────────────────────────────
[[ -f "$BACKEND_DIR/.venv/bin/python" ]] || die ".venv 未初始化。请先运行: bash scripts/setup.sh"
[[ -f "$REPO_ROOT/.env" ]] || die ".env 不存在。请先运行: bash scripts/setup.sh"

COMPOSE="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    command -v docker-compose &>/dev/null && COMPOSE="docker-compose" || die "docker compose 未找到"
fi

HAS_FRONTEND=false
if [[ -d "$WEB_DIR" && -d "$WEB_DIR/node_modules" ]] && command -v node &>/dev/null; then
    HAS_FRONTEND=true
fi

# ──────────────────────────────────────────────────────────────────────────────
# --stop：停止所有后台进程
# ──────────────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--stop" ]]; then
    log "停止所有 Heart 开发服务..."

    # tmux session
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
        info "✓ tmux 会话 '$SESSION' 已终止"
    fi

    # 后台进程 PID
    if [[ -d "$PID_DIR" ]]; then
        for pid_file in "$PID_DIR"/*.pid; do
            [[ -f "$pid_file" ]] || continue
            pid=$(cat "$pid_file")
            name=$(basename "$pid_file" .pid)
            if kill "$pid" 2>/dev/null; then
                info "✓ 已停止 $name (PID=$pid)"
            else
                warn "$name PID=$pid 已不在运行"
            fi
            rm -f "$pid_file"
        done
        rm -rf "$PID_DIR"
    fi

    # docker
    cd "$REPO_ROOT"
    $COMPOSE stop postgres redis 2>/dev/null || true
    info "✓ postgres + redis 已停止"

    echo ""
    log "✅ 全部服务已停止"
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# --logs：查看后台日志
# ──────────────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--logs" ]]; then
    if [[ -f "$LOG_DIR/api.log" ]] || [[ -f "$LOG_DIR/web.log" ]]; then
        log "跟踪后台日志（Ctrl+C 退出）..."
        tail -f "$LOG_DIR"/api.log "$LOG_DIR"/web.log 2>/dev/null
    else
        warn "未找到日志文件。服务可能通过 tmux 运行，请 tmux attach -t $SESSION"
    fi
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# 启动 docker compose
# ──────────────────────────────────────────────────────────────────────────────
start_docker() {
    log "启动 postgres + redis..."
    cd "$REPO_ROOT"
    $COMPOSE up -d postgres redis

    log "等待 postgres 就绪..."
    for i in $(seq 1 25); do
        if $COMPOSE ps postgres 2>/dev/null | grep -q "healthy"; then
            info "✓ postgres 就绪 (${i}s)"
            return
        fi
        sleep 1
    done
    warn "postgres 25s 内未显示 healthy（可能刚启动，继续...）"
}

# ──────────────────────────────────────────────────────────────────────────────
# 模式 A：tmux（推荐，自动分三个窗口）
# ──────────────────────────────────────────────────────────────────────────────
start_with_tmux() {
    start_docker

    # 如果已有同名 session 先清掉
    tmux kill-session -t "$SESSION" 2>/dev/null || true

    log "创建 tmux 会话 '$SESSION'..."

    # Window 1: api (FastAPI uvicorn)
    tmux new-session -d -s "$SESSION" -n "api" -x 220 -y 50
    tmux send-keys -t "$SESSION:api" \
        "cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn heart.api.main:app --reload --host 0.0.0.0 --port 8000" \
        Enter

    # Window 2: web (Vite)
    if $HAS_FRONTEND; then
        tmux new-window -t "$SESSION" -n "web"
        tmux send-keys -t "$SESSION:web" \
            "cd '$WEB_DIR' && npm run dev" \
            Enter
    fi

    # Window 3: docker logs
    tmux new-window -t "$SESSION" -n "docker"
    tmux send-keys -t "$SESSION:docker" \
        "cd '$REPO_ROOT' && $COMPOSE logs -f --tail=50" \
        Enter

    # 默认聚焦 api 窗口
    tmux select-window -t "$SESSION:api"

    echo ""
    log "✅ 开发环境启动完成"
    echo ""
    info "接入方法:"
    printf "  ${c_green}tmux attach -t $SESSION${c_reset}\n"
    echo ""
    info "窗口切换: Ctrl+b + 数字，或 Ctrl+b + n/p"
    printf "  ${c_blue}Ctrl+b 1${c_reset}  → api (uvicorn :8000)\n"
    $HAS_FRONTEND && printf "  ${c_blue}Ctrl+b 2${c_reset}  → web (vite :5173)\n"
    printf "  ${c_blue}Ctrl+b 3${c_reset}  → docker logs\n"
    info "离开会话（保持运行）: Ctrl+b + d"
    info "停止所有服务: bash scripts/dev.sh --stop"
    echo ""

    tmux attach -t "$SESSION"
}

# ──────────────────────────────────────────────────────────────────────────────
# 模式 B：在已有的 tmux 会话内（新开 window）
# ──────────────────────────────────────────────────────────────────────────────
start_in_existing_tmux() {
    start_docker

    tmux new-window -n "api"
    tmux send-keys \
        "cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn heart.api.main:app --reload --host 0.0.0.0 --port 8000" \
        Enter

    if $HAS_FRONTEND; then
        tmux new-window -n "web"
        tmux send-keys "cd '$WEB_DIR' && npm run dev" Enter
    fi

    tmux new-window -n "docker"
    tmux send-keys "cd '$REPO_ROOT' && $COMPOSE logs -f --tail=50" Enter

    tmux select-window -l

    echo ""
    log "✅ 已在当前 tmux 会话中新建 api / web / docker 窗口"
    info "切换: Ctrl+b + n/p，或 Ctrl+b + 数字"
}

# ──────────────────────────────────────────────────────────────────────────────
# 模式 C：无 tmux — 后台进程 + 前台 uvicorn
# ──────────────────────────────────────────────────────────────────────────────
start_background() {
    mkdir -p "$PID_DIR" "$LOG_DIR"
    start_docker

    # Vite（后台）
    if $HAS_FRONTEND; then
        log "启动 Vite dev server（后台）..."
        cd "$WEB_DIR"
        nohup npm run dev > "$LOG_DIR/web.log" 2>&1 &
        echo $! > "$PID_DIR/web.pid"
        info "✓ Vite PID=$(cat "$PID_DIR/web.pid")  日志: $LOG_DIR/web.log"
    fi

    echo ""
    log "✅ 后台服务已启动"
    echo ""
    if $HAS_FRONTEND; then
        info "Vite:    http://localhost:5173"
    fi
    info "API:     http://localhost:8000"
    echo ""
    info "日志:    bash scripts/dev.sh --logs"
    info "停止:    bash scripts/dev.sh --stop"
    echo ""
    log "前台启动 uvicorn（Ctrl+C 只停 uvicorn，其他服务保持运行）..."
    echo ""

    # 捕获 Ctrl+C，只停 uvicorn（不停 Vite 和 docker）
    trap 'echo ""; info "uvicorn 已停止。后台服务仍在运行，停止请运行: bash scripts/dev.sh --stop"; exit 0' INT

    cd "$BACKEND_DIR"
    source .venv/bin/activate
    uvicorn heart.api.main:app --reload --host 0.0.0.0 --port 8000
}

# ──────────────────────────────────────────────────────────────────────────────
# 入口：按环境自动选择模式
# ──────────────────────────────────────────────────────────────────────────────
echo ""
log "Heart 开发环境启动"

if command -v tmux &>/dev/null; then
    if [[ -n "${TMUX:-}" ]]; then
        # 已在 tmux 会话内
        start_in_existing_tmux
    else
        # 有 tmux 但在外面 → 新建 session 并 attach
        start_with_tmux
    fi
else
    # 没有 tmux
    warn "tmux 未找到，使用后台进程模式"
    warn "建议安装 tmux（Ubuntu: sudo apt install tmux）以获得更好体验"
    echo ""
    start_background
fi
