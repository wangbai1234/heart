#!/usr/bin/env bash
# 角色审核命令行工具 —— 封装 /api/admin/characters/* 端点。
#
# 环境变量:
#   ADMIN_KEY   管理员密钥（对应后端 ADMIN_SECRET_KEY），必填
#   API_BASE    API 根地址，默认 http://localhost:8000
#
# 用法:
#   scripts/review_characters.sh list                 列出待审核角色
#   scripts/review_characters.sh approve <char_id>    通过（发放奖励）
#   scripts/review_characters.sh reject  <char_id> "原因"   驳回
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
if [[ -z "${ADMIN_KEY:-}" ]]; then
  echo "错误: 请先设置 ADMIN_KEY 环境变量（后端 ADMIN_SECRET_KEY）" >&2
  exit 1
fi

_hdr=(-H "X-Admin-Key: ${ADMIN_KEY}" -H "Content-Type: application/json")

cmd="${1:-}"
case "$cmd" in
  list)
    curl -s "${_hdr[@]}" "${API_BASE}/api/admin/characters/pending" | python3 -m json.tool
    ;;
  approve)
    cid="${2:?用法: approve <char_id>}"
    curl -s -X POST "${_hdr[@]}" "${API_BASE}/api/admin/characters/${cid}/approve" | python3 -m json.tool
    ;;
  reject)
    cid="${2:?用法: reject <char_id> \"原因\"}"
    reason="${3:?用法: reject <char_id> \"原因\"}"
    payload=$(python3 -c 'import json,sys; print(json.dumps({"reason": sys.argv[1]}))' "$reason")
    curl -s -X POST "${_hdr[@]}" -d "$payload" \
      "${API_BASE}/api/admin/characters/${cid}/reject" | python3 -m json.tool
    ;;
  *)
    echo "用法: $0 {list|approve <char_id>|reject <char_id> \"原因\"}" >&2
    exit 1
    ;;
esac
