#!/usr/bin/env bash
# scripts/upload-covers-prod.sh — Mac 端一键上传剧情封面到生产
#
# 把 ~/Downloads/test/*.png 用 rsync 推到生产服务器，再 ssh 进服务器、在 api 容器内
# 跑 backend/scripts/upload_scenario_covers.py（依赖 heart 包 + DATABASE_URL + S3 配置
# 只装在容器里，宿主机 python 跑会报 ModuleNotFoundError）。
#
# 用法：
#   bash scripts/upload-covers-prod.sh             # 只上传 cover_url 为空的剧情
#   bash scripts/upload-covers-prod.sh --dry-run   # 只检查匹配情况，不实际上传
#   bash scripts/upload-covers-prod.sh --force     # 强制覆盖已有 cover_url
#
# 可覆盖环境变量：
#   SRC_DIR=/path/to/covers        # 本地 .png 目录（默认 ~/Downloads/test）
#   HEART_PROD_SSH=deploy@1.2.3.4  # ssh 目标（默认 deploy@167.104.96.125）
#   HEART_PROD_PORT=52200          # ssh 端口（默认 52200）
#   HEART_PROD_DIR=/home/deploy/heart  # 服务器上仓库检出路径
#
# 前置：
#   - Mac 能 ssh 到服务器（~/.ssh 已配好密钥）
#   - 服务器已部署（api 容器在跑）
#   - docker-compose.prod.yml 已挂 ./covers_src:/covers:ro（见下方说明）
#   - .env.prod 里 DATABASE_URL / S3_* 已配（容器内已就绪）
#
# 退出码：0 成功；1 参数/前置失败；2 rsync 失败；3 远端上传失败。
set -euo pipefail

c_green="\033[32m"; c_blue="\033[34m"; c_yellow="\033[33m"; c_red="\033[31m"; c_reset="\033[0m"
log()  { printf "${c_green}[covers]${c_reset} %s\n" "$*"; }
info() { printf "${c_blue}[info]${c_reset} %s\n" "$*"; }
warn() { printf "${c_yellow}[warn]${c_reset} %s\n" "$*"; }
die()  { printf "${c_red}[error]${c_reset} %s\n" "$*" >&2; exit 1; }

# ── 参数 ──────────────────────────────────────────────────────────────────
SRC_DIR="${SRC_DIR:-/Users/wanglixun/Downloads/test}"
HEART_PROD_SSH="${HEART_PROD_SSH:-deploy@167.104.96.125}"
HEART_PROD_PORT="${HEART_PROD_PORT:-52200}"
HEART_PROD_DIR="${HEART_PROD_DIR:-/home/deploy/heart}"
REMOTE_COVERS_DIR="$HEART_PROD_DIR/covers_src"

FORCE_ARG=""
DRY_RUN_ARG=""

case "${1:-}" in
    --dry-run) DRY_RUN_ARG="--dry-run" ;;
    --force)   FORCE_ARG="--force" ;;
    "")        ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) die "未知参数: $1 （用 --dry-run 或 --force）" ;;
esac

# ── 前置检查 ──────────────────────────────────────────────────────────────
[[ -d "$SRC_DIR" ]] || die "封面目录不存在: $SRC_DIR"
png_count=$(find "$SRC_DIR" -maxdepth 1 -type f -name '*.png' | wc -l | tr -d ' ')
[[ "$png_count" -gt 0 ]] || die "封面目录没有 .png 文件: $SRC_DIR"

command -v rsync &>/dev/null || die "rsync 未安装（macOS 自带，若无：brew install rsync）"

log "上传 $png_count 张封面 → 生产"
info "源目录:   $SRC_DIR"
info "SSH 目标: $HEART_PROD_SSH:$HEART_PROD_PORT"
info "远端目录: $REMOTE_COVERS_DIR"
[[ -n "$DRY_RUN_ARG" ]] && info "模式:     dry-run（只检查匹配，不上传）"
[[ -n "$FORCE_ARG"   ]] && info "模式:     --force（强制覆盖已有 URL）"
echo ""

# ── 1) rsync 推 .png 到服务器 ────────────────────────────────────────────
log "1/2  rsync 同步 .png → $REMOTE_COVERS_DIR ..."
rsync -az --delete \
    -e "ssh -p $HEART_PROD_PORT" \
    --include='*.png' --exclude='*' \
    "$SRC_DIR/" "$HEART_PROD_SSH:$REMOTE_COVERS_DIR/" \
    || die "rsync 失败（exit $?）"

info "✓ 同步完成"

# ── 2) ssh 在 api 容器内跑上传脚本 ───────────────────────────────────────
# 容器内 WORKDIR=/app，脚本在 /app/scripts/upload_scenario_covers.py
# --src /covers = compose 挂载的 ./covers_src:ro
log "2/2  在 api 容器内运行 upload_scenario_covers.py $DRY_RUN_ARG $FORCE_ARG ..."
ssh -p "$HEART_PROD_PORT" "$HEART_PROD_SSH" "cd '$HEART_PROD_DIR' && \
    docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api \
    python -m scripts.upload_scenario_covers --src /covers $DRY_RUN_ARG $FORCE_ARG" \
    || { warn "远端上传失败（exit $?）"; exit 3; }

echo ""
log "✅ 完成。"
if [[ -n "$DRY_RUN_ARG" ]]; then
    warn "dry-run 未写库。确认无误后跑：bash scripts/upload-covers-prod.sh"
else
    info "封面已上传。前端 https://yuoyuo.app 探索页查看效果。"
fi
