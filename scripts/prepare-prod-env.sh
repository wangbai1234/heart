#!/usr/bin/env bash
# Build a production dotenv file without copying development infrastructure secrets.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_ENV="${1:-$REPO_ROOT/.env}"
OUTPUT_ENV="${2:-$REPO_ROOT/.env.prod}"
TEMPLATE_ENV="$REPO_ROOT/.env.prod.example"

[[ -f "$SOURCE_ENV" ]] || { echo "source env not found: $SOURCE_ENV" >&2; exit 1; }
[[ -f "$TEMPLATE_ENV" ]] || { echo "template env not found: $TEMPLATE_ENV" >&2; exit 1; }
[[ ! -e "$OUTPUT_ENV" ]] || { echo "refusing to overwrite: $OUTPUT_ENV" >&2; exit 1; }
command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
tmp_env="$tmp_dir/env.prod"

cp "$TEMPLATE_ENV" "$tmp_env"

openssl genpkey -algorithm RSA -out "$tmp_dir/jwt-private.pem" \
  -pkeyopt rsa_keygen_bits:2048 >/dev/null 2>&1
openssl rsa -pubout -in "$tmp_dir/jwt-private.pem" \
  -out "$tmp_dir/jwt-public.pem" >/dev/null 2>&1

jwt_private=$(awk '{printf "%s\\n", $0}' "$tmp_dir/jwt-private.pem")
jwt_public=$(awk '{printf "%s\\n", $0}' "$tmp_dir/jwt-public.pem")

cat >> "$tmp_env" <<EOF

# Generated production overrides. Later entries intentionally win.
POSTGRES_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
OTP_PEPPER=$(openssl rand -hex 32)
ADMIN_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY="$jwt_private"
JWT_PUBLIC_KEY="$jwt_public"
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=$(openssl rand -hex 16)
S3_SECRET_ACCESS_KEY=$(openssl rand -hex 32)
S3_BUCKET_NAME=yuoyuo-media-prod
S3_REGION=us-east-1
S3_PUBLIC_BASE_URL=
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://yuoyuo.app,https://www.yuoyuo.app
HEART_INNER_LOOP_ENABLED=false
PROACTIVE_LLM_ENABLED=false
SENTRY_DSN=
EOF

# Import only external-provider and business settings. Infrastructure, auth,
# database, Redis, storage and admin secrets are always generated above.
allowlist='DEEPSEEK_API_KEY DEEPSEEK_BASE_URL DEEPSEEK_V4_FLASH_MODEL DEEPSEEK_V4_PRO_MODEL MAIN_LLM_MODEL CHEAP_LLM_MODEL BACKGROUND_GPT_API_KEY BACKGROUND_GPT_BASE_URL BACKGROUND_GPT_LUNA_MODEL BACKGROUND_GPT_MINI_MODEL BACKGROUND_GEMINI_API_KEY BACKGROUND_GEMINI_BASE_URL BACKGROUND_GEMINI_25_MODEL BACKGROUND_GEMINI_31_MODEL BACKGROUND_CLAUDE_API_KEY BACKGROUND_CLAUDE_BASE_URL BACKGROUND_CLAUDE_HAIKU_MODEL BACKGROUND_CLAUDE_API_STYLE BACKGROUND_LLM_MODEL BACKGROUND_LLM_FAILOVER BACKGROUND_LLM_ATTEMPT_TIMEOUT_SECONDS EMBEDDING_API_KEY EMBEDDING_BASE_URL EMBEDDING_MODEL EMBEDDING_DIMENSIONS MINIMAX_API_KEY MINIMAX_GROUP_ID MINIMAX_BASE_URL MINIMAX_TTS_MODEL MINIMAX_LANGUAGE_BOOST MINIMAX_RIN_CLONE_VOICE_ID MINIMAX_DOROTHY_VOICE_ID MIMO_API_KEY MIMO_BASE_URL MIMO_MODEL MIMO_REFERENCE_AUDIO_PATH VOICE_PROVIDER VOICE_FALLBACK_ENABLED TTS_MAX_CONCURRENCY TTS_MAX_RETRIES TTS_KEY_COOLDOWN_SECONDS EMAIL_PROVIDER EMAIL_FROM EMAIL_FROM_NAME RESEND_API_KEY BREVO_API_KEY GROK_API_KEY GROK_BASE_URL GROK_MODEL GROK_46_MODEL CLAUDE_API_KEY CLAUDE_BASE_URL CLAUDE_MODEL CLAUDE_HAIKU_MODEL CLAUDE_OPUS_46_MODEL CLAUDE_OPUS_5_MODEL CLAUDE_API_STYLE GEMINI_API_KEY GEMINI_BASE_URL GEMINI_MODEL GPT_API_KEY GPT_BASE_URL GPT_MODEL GPT_LUNA_MODEL GPT_SOL_MODEL FISH_API_KEY FISH_BASE_URL FISH_MODEL FISH_REALTIME_ENABLED FISH_REALTIME_URL FISH_REALTIME_MODEL QWEN_ASR_API_KEY QWEN_ASR_BASE_URL QWEN_ASR_WS_URL QWEN_ASR_MODEL QWEN_ASR_REALTIME_MODEL AFDIAN_USER_ID AFDIAN_API_TOKEN AFDIAN_WEBHOOK_TOKEN AFDIAN_SPONSOR_URL AFDIAN_SKU_MAP AFDIAN_CHECKOUT_URLS INVITE_REFERRAL_GRANT_COINS INVITE_MILESTONE_5_COINS INVITE_MILESTONE_10_COINS DAILY_CHECKIN_COINS'

awk -v allowlist="$allowlist" '
  BEGIN {
    count = split(allowlist, keys, " ")
    for (i = 1; i <= count; i++) allowed[keys[i]] = i
  }
  /^[A-Za-z_][A-Za-z0-9_]*=/ {
    key = $0
    sub(/=.*/, "", key)
    if (key in allowed) last[key] = $0
  }
  END {
    print ""
    print "# Approved existing external-provider and business settings."
    for (i = 1; i <= count; i++) {
      key = keys[i]
      if (key in last) print last[key]
    }
  }
' "$SOURCE_ENV" >> "$tmp_env"

install -m 600 "$tmp_env" "$OUTPUT_ENV"
echo "created $OUTPUT_ENV with production-generated internal secrets"
