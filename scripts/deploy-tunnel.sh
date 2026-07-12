#!/usr/bin/env bash
# scripts/deploy-tunnel.sh — 场景 1：Windows + WSL Ubuntu + Cloudflare Tunnel
#
# 用途：Windows 上的 WSL2 Ubuntu 里跑完整栈，通过 Cloudflare Tunnel
#       生成公网 URL，用手机浏览器直接测试（无需备案 / 无需公网 IP）。
#
# 架构：
#   [手机] → [Cloudflare 边缘] → [WSL Ubuntu cloudflared]
#          → Vite :5173 (frontend)
#          → (Vite proxy) → uvicorn :8000 (backend + WebSocket)
#          → postgres/redis (docker compose)
#
# 用法：
#   bash scripts/deploy-tunnel.sh              首次运行（自动装依赖 + 起服务 + 建 tunnel）
#   bash scripts/deploy-tunnel.sh --url-only   只启动 tunnel（假设服务已在跑）
#   bash scripts/deploy-tunnel.sh --stop       停止所有服务和 tunnel
#
# 前置条件：
#   - Windows 11 + WSL2 + Ubuntu 22.04+（推荐 24.04）
#   - 已进入 WSL Ubuntu shell（不要在 PowerShell 里跑）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="/tmp/heart-tunnel"
PID_DIR="$REPO_ROOT/.tunnel-pids"
SESSION="heart-tunnel"

c_green="\033[32m"; c_blue="\033[34m"; c_yellow="\033[33m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[tunnel]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

MODE="${1:-full}"

# ──────────────────────────────────────────────────────────────────────────────
# --stop：停止 tunnel + 所有开发服务
# ──────────────────────────────────────────────────────────────────────────────
if [[ "$MODE" == "--stop" ]]; then
    log "停止 Cloudflare Tunnel + 开发服务..."

    # 停 tmux 会话
    if command -v tmux &>/dev/null && tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
        info "✓ tmux 会话 '$SESSION' 已终止"
    fi

    # 停后台 PID
    if [[ -d "$PID_DIR" ]]; then
        for pid_file in "$PID_DIR"/*.pid; do
            [[ -f "$pid_file" ]] || continue
            pid=$(cat "$pid_file")
            name=$(basename "$pid_file" .pid)
            kill "$pid" 2>/dev/null && info "✓ 已停止 $name (PID=$pid)" || true
            rm -f "$pid_file"
        done
        rm -rf "$PID_DIR"
    fi

    # 停 cloudflared 残留进程
    pkill -f "cloudflared tunnel" 2>/dev/null && info "✓ cloudflared 残留进程已清理" || true

    # 停 docker
    cd "$REPO_ROOT"
    docker compose stop postgres redis 2>/dev/null || true
    info "✓ postgres + redis 已停止"

    log "✅ 全部服务已停止"
    exit 0
fi

# ──────────────────────────────────────────────────────────────────────────────
# 前置检查
# ──────────────────────────────────────────────────────────────────────────────
check_wsl() {
    if grep -qi "microsoft" /proc/version 2>/dev/null; then
        info "✓ 检测到 WSL 环境"
    else
        warn "未检测到 WSL 环境。此脚本设计用于 WSL2 Ubuntu，纯 Linux 也能用但请忽略 WSL 相关提示。"
    fi

    if [[ ! -f /etc/debian_version ]]; then
        die "此脚本仅支持 Ubuntu/Debian。macOS 请用 dev.sh + brew install cloudflared"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# 安装 cloudflared
# ──────────────────────────────────────────────────────────────────────────────
install_cloudflared() {
    if command -v cloudflared &>/dev/null; then
        info "✓ cloudflared 已安装（$(cloudflared --version 2>&1 | head -1)）"
        return
    fi

    log "安装 cloudflared..."
    local arch
    arch=$(dpkg --print-architecture)
    local url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb"

    local tmpfile="/tmp/cloudflared.deb"
    if command -v curl &>/dev/null; then
        curl -fsSL "$url" -o "$tmpfile"
    elif command -v wget &>/dev/null; then
        wget -q "$url" -O "$tmpfile"
    else
        die "curl 或 wget 未找到，请先安装：sudo apt install -y curl"
    fi

    sudo dpkg -i "$tmpfile"
    rm -f "$tmpfile"
    info "✓ cloudflared 已安装"
}

# ──────────────────────────────────────────────────────────────────────────────
# 启动 docker + uvicorn + vite（后台）
# ──────────────────────────────────────────────────────────────────────────────
start_services() {
    [[ -f "$REPO_ROOT/backend/.venv/bin/python" ]] || {
        warn ".venv 未初始化，先运行 setup.sh..."
        bash "$REPO_ROOT/scripts/setup.sh"
    }

    mkdir -p "$LOG_DIR" "$PID_DIR"

    log "启动 postgres + redis..."
    cd "$REPO_ROOT"
    docker compose up -d postgres redis

    for i in $(seq 1 25); do
        docker compose ps postgres 2>/dev/null | grep -q "healthy" && { info "✓ postgres 就绪 (${i}s)"; break; }
        sleep 1
    done

    # 启动 uvicorn（后台）
    log "启动 uvicorn（后台）..."
    cd "$REPO_ROOT/backend"
    nohup "$REPO_ROOT/backend/.venv/bin/python" -m uvicorn \
        heart.api.main:app --reload --host 127.0.0.1 --port 8000 \
        > "$LOG_DIR/api.log" 2>&1 &
    echo $! > "$PID_DIR/api.pid"
    info "✓ uvicorn PID=$(cat "$PID_DIR/api.pid")  日志: $LOG_DIR/api.log"

    # 启动 Vite（后台）
    if [[ -d "$REPO_ROOT/web/node_modules" ]]; then
        log "启动 Vite（后台）..."
        cd "$REPO_ROOT/web"
        # --host 0.0.0.0 允许 cloudflared 从任意接口访问
        nohup npm run dev -- --host 127.0.0.1 \
            > "$LOG_DIR/web.log" 2>&1 &
        echo $! > "$PID_DIR/web.pid"
        info "✓ Vite PID=$(cat "$PID_DIR/web.pid")  日志: $LOG_DIR/web.log"
    else
        die "web/node_modules 不存在，请先运行 setup.sh"
    fi

    # 等 Vite 起来
    log "等待 Vite 启动..."
    for i in $(seq 1 30); do
        if curl -sf http://127.0.0.1:5173 >/dev/null 2>&1; then
            info "✓ Vite 就绪 (${i}s)"
            return
        fi
        sleep 1
    done
    warn "Vite 30s 内未响应，可能仍在初始化。查看日志: tail -f $LOG_DIR/web.log"
}

# ──────────────────────────────────────────────────────────────────────────────
# 启动 Cloudflare Tunnel（Quick Tunnel — 免注册，即用即弃）
# ──────────────────────────────────────────────────────────────────────────────
start_tunnel() {
    log "启动 Cloudflare Tunnel（Quick Tunnel，指向 Vite :5173）..."
    mkdir -p "$LOG_DIR" "$PID_DIR"

    # 用 nohup + tee 后台跑，实时捕获输出以提取 trycloudflare URL
    nohup cloudflared tunnel --url http://127.0.0.1:5173 \
        > "$LOG_DIR/tunnel.log" 2>&1 &
    echo $! > "$PID_DIR/tunnel.pid"
    info "✓ cloudflared PID=$(cat "$PID_DIR/tunnel.pid")"

    # 等待并抓取公网 URL
    log "等待公网 URL 生成..."
    local url=""
    for i in $(seq 1 30); do
        url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG_DIR/tunnel.log" 2>/dev/null | head -1 || true)
        [[ -n "$url" ]] && break
        sleep 1
    done

    if [[ -z "$url" ]]; then
        die "30s 内未获取到公网 URL。查看日志: tail -f $LOG_DIR/tunnel.log"
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    printf "  ${c_green}✅ 公网测试 URL:${c_reset}\n\n"
    printf "  ${c_blue}${url}${c_reset}\n\n"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # 生成二维码（如果 qrencode 存在）
    if command -v qrencode &>/dev/null; then
        info "扫码打开："
        qrencode -t ansiutf8 "$url"
        echo ""
    else
        warn "提示：安装 qrencode 可在终端显示二维码 → sudo apt install -y qrencode"
        echo ""
    fi

    info "日志实时查看:"
    echo "  uvicorn:    tail -f $LOG_DIR/api.log"
    echo "  vite:       tail -f $LOG_DIR/web.log"
    echo "  cloudflared: tail -f $LOG_DIR/tunnel.log"
    echo ""
    info "停止所有服务:  bash scripts/deploy-tunnel.sh --stop"
    echo ""
    warn "⚠️  Quick Tunnel URL 会话结束即失效。如需固定域名，见文档最后。"
}

# ──────────────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────────────
main() {
    echo ""
    log "Heart — Windows/WSL Ubuntu + Cloudflare Tunnel 测试部署"
    echo "──────────────────────────────────────────────────────────"

    check_wsl
    install_cloudflared

    if [[ "$MODE" != "--url-only" ]]; then
        start_services
    else
        info "跳过服务启动（--url-only 模式）"
    fi

    start_tunnel
}

main
