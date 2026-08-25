"""应用全局配置 — per runtime_specs/08_engineering_architecture.md §3 (Configuration)"""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to repo root, not CWD.
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    """应用配置（从环境变量读取）"""

    model_config = SettingsConfigDict(
        env_file=str(_env_path) if _env_path.exists() else ".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: str = "development"
    heart_env: str = "dev"
    heart_dev_mode: str = ""
    heart_invariants: str = ""
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://heart:heartdev@localhost:5432/heart"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # LLM Providers - DeepSeek
    deepseek_api_key: str = ""
    # Optional comma-separated list of additional DeepSeek keys for the outbound pool.
    # Empty → fall back to the single deepseek_api_key (single-key behavior unchanged).
    deepseek_api_keys: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    # Actual upstream model IDs for the two selectable DeepSeek product entries.
    deepseek_v4_flash_model: str = "deepseek-chat"
    deepseek_v4_pro_model: str = "deepseek-reasoner"

    # LLM Providers - Gemini (MICU OpenAI-compatible relay)
    gemini_api_key: str = ""
    gemini_base_url: str = "https://api-slb.micuapi.ai"
    gemini_model: str = "gemini-3.1-flash-lite-preview"

    # LLM Providers - GPT (MICU Responses-compatible relay)
    gpt_api_key: str = ""
    gpt_base_url: str = "https://api-slb.micuapi.ai"
    gpt_model: str = "gpt-5.5"
    gpt_luna_model: str = "gpt-5.6-luna"
    gpt_sol_model: str = "gpt-5.6-sol"

    # LLM Providers - internal background tasks (separate MICU groups).
    # These credentials must never be shared with the user-selectable chat
    # providers above, even when the upstream model ID happens to be the same.
    background_gpt_api_key: str = ""
    background_gpt_base_url: str = "https://api-slb.micuapi.ai"
    background_gpt_luna_model: str = "gpt-5.6-luna"
    background_gpt_mini_model: str = "gpt-5.4-mini"
    background_gemini_api_key: str = ""
    background_gemini_base_url: str = "https://api-slb.micuapi.ai"
    background_gemini_25_model: str = "gemini-2.5-flash-lite"
    background_gemini_31_model: str = "gemini-3.1-flash-lite-preview"
    background_claude_api_key: str = ""
    background_claude_base_url: str = "https://api-slb.micuapi.ai"
    background_claude_haiku_model: str = "claude-haiku-4-5-20251001"
    background_claude_api_style: str = "anthropic"

    # Outbound LLM concurrency / failover (process-global; see llm_providers/pool.py)
    llm_max_concurrency: int = 8
    llm_max_retries: int = 2
    llm_key_cooldown_seconds: float = 15.0

    # LLM Model Configuration. Main/cheap are legacy compatibility slots only;
    # production internal tasks use the independent background chain below.
    main_llm_model: str = "deepseek-chat"
    cheap_llm_model: str = "deepseek-chat"
    background_llm_model: str = "background-gpt-5.6-luna"
    background_llm_failover: str = (
        "background-gpt-5.4-mini,background-gemini-2.5-flash-lite,"
        "background-gemini-3.1-flash-lite-preview,background-claude-haiku-4.5"
    )
    background_llm_attempt_timeout_seconds: float = 10.0

    # Embedding Service (OpenAI-compatible hosted endpoint, e.g. SiliconFlow bge-m3)
    embedding_model: str = "BAAI/bge-m3"
    embedding_batch_size: int = 32
    embedding_cache_ttl: int = 86400
    # When embedding_api_key is empty the EmbeddingService is disabled (build
    # returns None) and memory falls back to recency/identity retrieval — no crash.
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_dimensions: int = 1024  # bge-m3 native dim; must match the DB vector() column

    # S3 / Object Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "heart-dev"
    s3_region: str = "us-east-1"
    # Optional public base URL for objects (e.g. Cloudflare R2 r2.dev subdomain).
    # When set, upload_file() returns this URL instead of the API endpoint URL so
    # that third-party services (e.g. MiniMax voice clone) can fetch the object
    # without authentication. Leave empty to use the API endpoint URL (fine for
    # avatars which are proxied through the backend; only matters for voice clone).
    s3_public_base_url: str = ""

    # Observability
    prometheus_port: int = 9090
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    sentry_dsn: str = ""

    # Rate Limiting
    rate_limit_per_user: int = 60
    rate_limit_per_ip: int = 200

    # Feature Flags
    enable_voice: bool = False
    enable_video: bool = False
    enable_critic_agent: bool = True
    critic_sampling_rate: float = 0.3
    enable_wellbeing_monitor: bool = True

    # Proactive messages (SS06). Content uses the user's selected chat model,
    # falling back to the built-in templates when the selected model chain fails.
    proactive_llm_enabled: bool = True
    proactive_llm_max_tokens: int = 120
    # v2: route proactive through the full composer chain instead of the thin
    # LLM call, using time-based probability thresholds (1h=5%, 5h=10%, 10h=40%,
    # 24h=80%) and per-user quota instead of per-character.
    proactive_v2_enabled: bool = False
    # v2 frequency controls
    proactive_v2_daily_quota: int = 2  # per user (not per character)
    proactive_v2_cooldown_minutes: int = 240  # 4h cross-character cooldown

    # Memory Extractor Mode (Phase D — regex sunset)
    # Deprecated: "regex", "dual" — will be removed in 60 days (Phase D §5.3)
    memory_extractor_mode: str = (
        "llm"  # "llm" (default) | "regex" (deprecated) | "dual" (deprecated)
    )
    memory_extractor_llm_model: str = "deepseek-chat"
    memory_extractor_batch_turns: int = 6
    memory_extractor_idle_secs: int = 30
    # Coalesce same-(user,character) pending encode events per poll cycle into ONE
    # extraction LLM call (was 1 call/turn). memory_extractor_batch_turns caps group size.
    memory_batch_extraction_enabled: bool = True
    memory_extractor_cost_cap_usd: float = 0.05
    memory_promoter_interval_secs: int = 300
    memory_promoter_min_mentions: int = 3
    memory_promoter_min_confidence: float = 0.8
    memory_promoter_min_age_days: int = 1
    memory_promoter_min_cross_sessions: int = 2
    memory_promoter_contradiction_clear_days: int = 7
    memory_promoter_batch_size: int = 200
    memory_promoter_l4_cap: int = 50
    memory_promoter_demotion_window_days: int = 14
    memory_promoter_demotion_min_count: int = 2

    # CORS
    cors_allowed_origins: str = ""

    # Profiling
    heart_turn_profiler: str = "0"

    # Cost Limits
    user_daily_cost_limit: float = 10.0
    alert_cost_threshold: float = 5.0

    # Security / Auth
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "RS256"
    jwt_private_key: str = ""  # PEM private key for RS256
    jwt_public_key: str = ""  # PEM public key for RS256
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Admin API — set a strong random secret; empty = admin endpoints disabled
    admin_secret_key: str = ""

    # OTP
    otp_pepper: str = "change-me-otp-pepper-32chars-min"
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_per_hour: int = 5
    otp_max_attempts: int = 5

    # Email (SMTP / API)
    email_provider: str = "smtp"  # smtp | resend | brevo | fallback
    email_from: str = "noreply@mail.yuoyuo.app"
    email_from_name: str = "yuoyuo"
    resend_api_key: str = ""
    brevo_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""

    # Credits / Billing (centesimal: 1 display credit = 100 fen internally)
    signup_grant_credits: int = 4000  # 40 display credits × 100
    credits_per_text_turn: int = 100  # 1 display credit (legacy turn billing)
    credits_per_voice_turn: int = 500  # 5 display credits (legacy turn billing)
    credits_cost_text_message: int = 50  # 0.5 display credits per text bubble
    credits_cost_voice_message: int = 500  # 5 display credits per voice message
    afdian_user_id: str = ""
    afdian_webhook_token: str = ""
    # Afdian open-API token (开发者页面 → API Token). Used to query/reconcile
    # orders server-side (backfill missed webhooks, re-fulfill orders placed
    # before the SKU map was configured). Often equal to afdian_webhook_token
    # when the same secret is reused as the webhook URL query token.
    afdian_api_token: str = ""
    afdian_sponsor_url: str = "https://ifdian.net/a/yuoyuo"
    # Per-SKU afdian order/create deep links (JSON string, overridable via
    # AFDIAN_CHECKOUT_URLS env var). Maps our internal sku key → the afdian
    # order/create URL *without* custom_order_id (the frontend appends the user's
    # binding code as ?custom_order_id=<code> so orders auto-fulfill w/o a remark).
    #   会员(方案): {"plan_plus": "https://afdian.com/order/create?plan_id=<id>&product_type=0"}
    #   币包(商品): {"pack_6":   "https://afdian.com/order/create?plan_id=<id>&sku=<sku_id>&product_type=1"}
    # Empty map → frontend falls back to afdian_sponsor_url + manual remark (legacy).
    afdian_checkout_urls: str = "{}"

    # Per-action pricing (display coins; ×100 = fen internally).
    # Fields are float so fractional coin prices work (e.g. DEEPSEEK_COST_CREDITS=0.5);
    # pricing.py rounds coins×100 to integer fen at the billing boundary.
    deepseek_cost_credits: float = (
        1  # 100 fen per LLM turn (普通交流; only charged on tiers where deepseek is not free)
    )
    grok_cost_credits: float = 3  # 300 fen per LLM turn (私密陪伴)
    claude_cost_credits: float = (
        12  # 1200 fen per LLM turn (legacy; claude removed from tiers/failover)
    )
    mimo_tts_cost_credits: float = 5  # 500 fen per TTS bubble
    fish_tts_cost_credits: float = 8  # 800 fen per TTS bubble
    clone_mimo_cost_credits: float = 50  # 5000 fen per clone
    clone_fish_cost_credits: float = 100  # 10000 fen per clone

    # Story mode (SS09) pricing + tier gating
    story_unlock_cost_coins: float = (
        40  # 4000 fen, permanent per-scenario unlock (all users can unlock all scenarios)
    )
    story_minute_cost_coins: float = 1  # 100 fen per full minute of play (PR C2)

    # Voice call (语音通话) pricing + monthly free-minute allowance per tier.
    # Billed per full minute via a client heartbeat (like story playtime). Each
    # tier gets a monthly free allowance; minutes beyond it are charged
    # voice_call_minute_cost_coins per minute. Allowance resets every calendar
    # month (Asia/Shanghai month_key), tracked in user_voice_call_quotas.
    voice_call_minute_cost_coins: float = 20  # 2000 fen per full minute (1min = 20币)
    # Free monthly minutes by tier (JSON, overridable via VOICE_CALL_FREE_MINUTES env var).
    # free: 0 (pay from minute 1); plus: 10; immersive: 60.
    voice_call_free_minutes_config: str = '{"free":0,"plus":10,"immersive":60}'

    # Membership tier definitions (JSON string, overridable via MEMBERSHIP_TIERS_CONFIG env var).
    # Each tier maps to: models (allowed LLM slugs), tts (allowed TTS providers),
    # clone (allowed clone providers), monthly_grant (coins per 30-day cycle),
    # free (items complimentary on this tier — everything else is charged per use).
    # Access is universal. Only immersive waives selectable text-model costs;
    # plus receives a larger permanent daily grant instead of free text turns.
    membership_tiers_config: str = (
        '{"free":{"models":["gemini-3.1","deepseek-v4-flash","deepseek-v4-pro","claude-haiku-4.5","claude-sonnet-4.6","claude-opus-4.6","claude-opus-5","grok-4.5","grok-4.6","gpt-5.6-luna","gpt-5.5","gpt-5.6-sol"],"tts":["mimo","fish"],"clone":["fish"],"monthly_grant":0,"free":[]},'
        '"plus":{"models":["gemini-3.1","deepseek-v4-flash","deepseek-v4-pro","claude-haiku-4.5","claude-sonnet-4.6","claude-opus-4.6","claude-opus-5","grok-4.5","grok-4.6","gpt-5.6-luna","gpt-5.5","gpt-5.6-sol"],"tts":["mimo","fish"],"clone":["fish"],"monthly_grant":0,"free":["tts","asr","story_unlock"]},'
        '"immersive":{"models":["gemini-3.1","deepseek-v4-flash","deepseek-v4-pro","claude-haiku-4.5","claude-sonnet-4.6","claude-opus-4.6","claude-opus-5","grok-4.5","grok-4.6","gpt-5.6-luna","gpt-5.5","gpt-5.6-sol"],"tts":["mimo","fish"],"clone":["fish"],"monthly_grant":0,"free":["all_llm","deepseek","grok","tts","clone","asr","story_unlock","story_chat"]}}'
    )

    # Membership subscription prices (CNY/month, for pricing endpoint display only)
    membership_plus_price_monthly: int = 29
    membership_immersive_price_monthly: int = 69

    # Afdian SKU → fulfillment map (JSON string, overridable via AFDIAN_SKU_MAP env var).
    # Each entry: {"type":"membership","tier":"plus","days":30} or {"type":"coins","coins":220}
    afdian_sku_map: str = "{}"

    # Invite qualification and draw chances (Asia/Shanghai calendar day).
    invite_qualification_days: int = 7
    invite_binding_hours: int = 24
    invite_min_messages: int = 3
    invite_min_ai_replies: int = 2
    invite_min_valid_chars: int = 15
    invite_min_span_seconds: int = 120
    invite_chance_expiry_days: int = 30
    invite_daily_limit_free: int = 5
    invite_daily_limit_plus: int = 10
    invite_daily_limit_immersive: int = 20
    referral_signal_salt: str = ""

    # Daily check-in reward (display coins; ×100 = fen internally)
    daily_checkin_coins: int = 20  # granted once per calendar day (Asia/Shanghai)
    plus_daily_checkin_coins: int = 80
    immersive_daily_checkin_coins: int = 80

    # Push Notifications (V1)
    fcm_credentials_path: str = ""
    apns_credentials_path: str = ""

    # Payment (V1)
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # MiniMax TTS
    minimax_api_key: str | None = None
    minimax_group_id: str | None = None
    # Optional comma-separated pools for multi-key TTS rotation. When set, each entry in
    # minimax_api_keys is paired positionally with minimax_group_ids (missing group_ids
    # fall back to minimax_group_id). Empty → single-key behavior unchanged.
    minimax_api_keys: str | None = None
    minimax_group_ids: str | None = None
    minimax_base_url: str = "https://api.minimax.io/v1"
    minimax_rin_clone_voice_id: str | None = None
    minimax_dorothy_voice_id: str | None = None
    minimax_tts_model: str = "speech-2.8-hd"
    minimax_language_boost: str | None = "Chinese"
    voice_profiles: str | None = None

    # LLM Providers - Grok (xAI) — optional; leave empty to disable
    grok_api_key: str = ""
    grok_base_url: str = "https://api.x.ai"
    grok_model: str = "grok-3-mini-fast"
    grok_46_model: str = "grok-4.6"

    # LLM Providers - Claude (Anthropic) — optional; leave empty to disable
    claude_api_key: str = ""
    claude_base_url: str = "https://api.anthropic.com"
    claude_model: str = "claude-sonnet-4-5"
    claude_haiku_model: str = "claude-haiku-4-5"
    claude_opus_46_model: str = "claude-opus-4-6"
    claude_opus_5_model: str = "claude-opus-5"
    # "anthropic" for native /v1/messages; "openai-compat" for proxy
    claude_api_style: str = "anthropic"

    # Fish Audio TTS — optional; leave empty to disable
    fish_api_key: str = ""
    fish_base_url: str = "https://api.fish.audio"
    fish_model: str = "speech-1.6"
    # Fish realtime (WebSocket + MessagePack) streaming TTS. Fish's selling
    # point is being faster than MiMo; the realtime endpoint feeds text
    # sentence-by-sentence and returns audio incrementally (much lower
    # time-to-first-audio than the blocking REST synth). Default OFF: needs a
    # live Fish key to validate, and any realtime error falls back to REST.
    # Default ON: Fish preset/clone voices stream over the realtime WebSocket for
    # low time-to-first-audio. Any handshake/connect failure falls back to the
    # blocking REST StreamSession (see routes_chat_ws._create_stream_session), so
    # enabling this never hard-fails a turn — worst case it degrades to REST synth.
    fish_realtime_enabled: bool = True
    fish_realtime_url: str = "wss://realtime.fishaudio.org/v3/tts/live"
    fish_realtime_model: str = "fishaudio-s21pro-flash"
    # Emotion-control syntax injected into TTS text. Fish backbones each parse a
    # DIFFERENT scheme, and using the wrong one makes the marker get read ALOUD:
    #   "s2"  → [中文自然语言指令], e.g. [低声说] — for the S2.1 family
    #           (s21pro / s21pro-flash / s2pro). Instruction words are NOT spoken.
    #   "s1"  → (english-fixed-label), e.g. (sighing) — ONLY for fishaudio-s1.
    #   "off" → send clean prose, no markers (rely on speed only).
    # Default "s2" matches the production model fishaudio-s21pro-flash.
    fish_emotion_mode: str = "s2"

    # MiMo TTS (voiceclone v2.5)
    mimo_api_key: str | None = None
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    mimo_reference_audio_path: str = "assets/reference_voices/rin.mp3"
    mimo_model: str = "mimo-v2.5-tts-voiceclone"
    mimo_asr_model: str = "mimo-v2.5-asr"
    voice_provider: str = "minimax"  # "mimo" | "minimax"
    voice_fallback_enabled: bool = True

    # Qwen ASR (Aliyun DashScope) — primary speech-to-text.
    # Voice chat: one-shot transcription (record → transcribe) via the realtime
    # WS driven to completion. Voice call: true streaming via the realtime WS.
    # MiMo ASR remains wired as the fallback if Qwen is unconfigured/fails.
    qwen_asr_api_key: str | None = None
    qwen_asr_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_asr_ws_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    qwen_asr_model: str = "qwen3-asr-flash"
    qwen_asr_realtime_model: str = "qwen3-asr-flash-realtime"

    # ASR (speech-to-text) billing — 5 display credits = 500 fen
    asr_cost_credits: int = 500

    # Outbound TTS concurrency / failover (process-global; see ss08_voice/pooled_provider.py).
    # MiniMax account concurrency caps are typically single-digit → keep conservative.
    tts_max_concurrency: int = 4
    tts_max_retries: int = 1
    tts_key_cooldown_seconds: float = 20.0

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """Fail-fast if JWT config is weak (all environments)."""
        if self.jwt_algorithm == "RS256":
            if not self.jwt_private_key or not self.jwt_public_key:
                raise RuntimeError("RS256 requires JWT_PRIVATE_KEY and JWT_PUBLIC_KEY")
        else:
            if (
                self.jwt_secret_key in {"your-secret-key-here", "", "change-me"}
                or len(self.jwt_secret_key) < 32
            ):
                raise RuntimeError("JWT_SECRET_KEY must be set to a strong random value")
        return self


# 全局配置实例
settings = Settings()
