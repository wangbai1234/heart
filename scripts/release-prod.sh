#!/usr/bin/env bash
# Mac 端生产发布唯一入口。生产服务器上的容器编排仍由 deploy-prod.sh 负责。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROD_SSH="${HEART_PROD_SSH:-deploy@103.69.128.125}"
PROD_PORT="${HEART_PROD_PORT:-22}"
PROD_DIR="${HEART_PROD_DIR:-/home/deploy/heart}"
MODE="${1:---status}"

c_green="\033[32m"; c_blue="\033[34m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[release]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

SSH=(ssh -p "$PROD_PORT" -o BatchMode=yes -o ConnectTimeout=10 "$PROD_SSH")

usage() {
    cat <<EOF
用法：
  bash scripts/release-prod.sh --status     # 容器、Git、API 状态（默认）
  bash scripts/release-prod.sh --frontend   # 本机构建 web/dist，rsync 后即时生效
  bash scripts/release-prod.sh --backend    # 服务器 main 快进、重建后端、迁移
  bash scripts/release-prod.sh --full       # 先检查后端可部署，再发前端和后端
  bash scripts/release-prod.sh --logs api   # 查看远端日志

默认目标：$PROD_SSH:$PROD_PORT:$PROD_DIR
可用 HEART_PROD_SSH / HEART_PROD_PORT / HEART_PROD_DIR 覆盖。
EOF
}

check_ssh() {
    "${SSH[@]}" "test -d '$PROD_DIR' && test -f '$PROD_DIR/docker-compose.prod.yml'" \
        || die "无法访问生产目录 $PROD_SSH:$PROD_DIR"
}

remote_git_preflight() {
    "${SSH[@]}" "cd '$PROD_DIR' && \
        test -d .git && \
        test \"\$(git branch --show-current)\" = main && \
        test -z \"\$(git status --porcelain=v1 --untracked-files=no)\"" \
        || die "生产 Git 尚未处于干净 main；查看 docs/PRODUCTION_DEPLOYMENT.md 的‘当前阻塞’"
}

build_and_sync_frontend() {
    command -v npm &>/dev/null || die "本机未安装 npm"
    command -v rsync &>/dev/null || die "本机未安装 rsync"
    log "本机构建前端..."
    (cd "$REPO_ROOT/web" && npm ci && npm run build)
    [[ -f "$REPO_ROOT/web/dist/index.html" ]] || die "web/dist/index.html 不存在"
    log "同步 web/dist 到生产（静态文件即时生效）..."
    "${SSH[@]}" "mkdir -p '$PROD_DIR/web/dist'"
    rsync -az --delete -e "ssh -p $PROD_PORT" \
        "$REPO_ROOT/web/dist/" "$PROD_SSH:$PROD_DIR/web/dist/"
    info "✓ 前端发布完成，无需重启 Caddy"
}

deploy_backend() {
    log "服务器拉取 main、重建 api/worker、迁移并验证..."
    "${SSH[@]}" "cd '$PROD_DIR' && bash scripts/deploy-prod.sh --update-backend"
}

show_status() {
    "${SSH[@]}" "cd '$PROD_DIR' && \
        printf 'branch=' && git branch --show-current && \
        printf 'commit=' && git rev-parse --short HEAD && \
        printf 'tracked_dirty=' && git status --porcelain=v1 --untracked-files=no | wc -l && \
        bash scripts/deploy-prod.sh --status"
    printf "public_health="
    curl -fsS --max-time 10 https://yuoyuo.app/health/live || true
    printf "\n"
}

case "$MODE" in
    -h|--help) usage; exit 0 ;;
esac

check_ssh
case "$MODE" in
    --status) show_status ;;
    --frontend) build_and_sync_frontend; show_status ;;
    --backend) remote_git_preflight; deploy_backend; show_status ;;
    --full)
        remote_git_preflight
        build_and_sync_frontend
        deploy_backend
        show_status
        ;;
    --logs)
        target="${2:-api}"
        exec "${SSH[@]}" "cd '$PROD_DIR' && bash scripts/deploy-prod.sh --logs '$target'"
        ;;
    *) usage; die "未知参数: $MODE" ;;
esac
