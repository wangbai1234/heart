#!/usr/bin/env bash
# scripts/import-scenarios-prod.sh — Mac 端一键导入剧情到生产
#
# 把 ~/Downloads/剧情设定/*.txt 用 rsync 推到生产服务器，再 ssh 进服务器、在 api 容器内
# 跑 backend/scripts/import_scenarios.py（依赖 structlog/heart 包 + DATABASE_URL + LLM key
# 只装在容器里，宿主机 python 跑会报 ModuleNotFoundError）。
#
# 用法：
#   bash scripts/import-scenarios-prod.sh             # 全量 --publish（正式发布）
#   bash scripts/import-scenarios-prod.sh --dry-run   # 只抽取卡片元数据、不写库（核对用）
#   bash scripts/import-scenarios-prod.sh --publish   # 显式 publish（同默认）
#
# 可覆盖环境变量：
#   SRC_DIR=/path/to/scenarios   # 本地 .txt 目录（默认 ~/Downloads/剧情设定）
#   HEART_PROD_SSH=deploy@1.2.3.4   # ssh 目标（默认 deploy@167.104.96.125）
#   HEART_PROD_PORT=52200           # ssh 端口（默认 52200）
#   HEART_PROD_DIR=/home/deploy/heart  # 服务器上仓库检出路径
#
# 前置：
#   - Mac 能 ssh 到服务器（~/.ssh 已配好密钥）
#   - 服务器已部署（api 容器在跑），且 docker-compose.prod.yml 已挂 ./scenarios_src:/scenarios:ro
#   - .env.prod 里 DEEPSEEK_API_KEY / DATABASE_URL 已配（容器内已就绪）
#
# 退出码：0 成功；1 参数/前置失败；2 rsync 失败；3 远端导入失败。
set -euo pipefail

c_green="\033[32m"; c_blue="\033[34m"; c_yellow="\033[33m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[import]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

# ── 参数 ──────────────────────────────────────────────────────────────────
SRC_DIR="${SRC_DIR:-/Users/wanglixun/Downloads/剧情设定}"
HEART_PROD_SSH="${HEART_PROD_SSH:-deploy@167.104.96.125}"
HEART_PROD_PORT="${HEART_PROD_PORT:-52200}"
HEART_PROD_DIR="${HEART_PROD_DIR:-/home/deploy/heart}"
REMOTE_DIR="$HEART_PROD_DIR/scenarios_src"

MODE_ARG="--publish"
case "${1:-}" in
    --dry-run) MODE_ARG="--dry-run" ;;
    --publish|"") MODE_ARG="--publish" ;;
    -h|--help)
        sed -n '2,26p' "$0"; exit 0 ;;
    *) die "未知参数: $1 （用 --publish 或 --dry-run）" ;;
esac

# ── 前置检查 ──────────────────────────────────────────────────────────────
[[ -d "$SRC_DIR" ]] || die "源目录不存在: $SRC_DIR"
txt_count=$(find "$SRC_DIR" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')
[[ "$txt_count" -gt 0 ]] || die "源目录没有 .txt 文件: $SRC_DIR"

command -v rsync &>/dev/null || die "rsync 未安装（macOS 自带，若无：brew install rsync）"

log "导入 $txt_count 个剧本 → 生产"
info "源目录:   $SRC_DIR"
info "SSH 目标: $HEART_PROD_SSH:$HEART_PROD_PORT"
info "远端目录: $REMOTE_DIR"
info "模式:     $MODE_ARG"
echo ""

# ── 1) rsync 推 .txt 到服务器（--delete 保持镜像，只同步 .txt，不推 .DS_Store 等）──
log "1/2  rsync 同步 .txt → $REMOTE_DIR ..."
rsync -az --delete \
    -e "ssh -p $HEART_PROD_PORT" \
    --include='*.txt' --exclude='*' \
    "$SRC_DIR/" "$HEART_PROD_SSH:$REMOTE_DIR/" \
    || die "rsync 失败（exit $?)"

info "✓ 同步完成（远端 .txt 数量见下方导入日志）"

# ── 2) ssh 在 api 容器内跑导入器 ──────────────────────────────────────────
# 容器内 WORKDIR=/app，脚本在 /app/scripts/import_scenarios.py（build context=./backend）。
# --src /scenarios = compose 挂载的 ./scenarios_src:ro。env-file 让 compose 看到 DB/LLM 配置。
log "2/2  在 api 容器内运行 import_scenarios.py $MODE_ARG ..."
ssh -p "$HEART_PROD_PORT" "$HEART_PROD_SSH" "cd '$HEART_PROD_DIR' && \
    docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api \
    python -m scripts.import_scenarios --src /scenarios $MODE_ARG" \
    || { warn "远端导入失败（exit $?）"; exit 3; }

echo ""
log "✅ 完成。"
if [[ "$MODE_ARG" == "--publish" ]]; then
    info "已发布剧本。核对："
    info "  ssh -p $HEART_PROD_PORT $HEART_PROD_SSH \"cd $HEART_PROD_DIR && docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api python -m alembic current\""
    info "  或前端 https://yuoyuo.app 探索页查看卡片。"
else
    warn "dry-run 未写库。核对元数据后跑：bash scripts/import-scenarios-prod.sh --publish"
fi
