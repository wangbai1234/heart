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
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # LLM Providers - DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # LLM Model Configuration
    main_llm_model: str = "deepseek-reasoner"
    cheap_llm_model: str = "deepseek-chat"

    # Embedding Service
    embedding_model: str = "BAAI/bge-m3"
    embedding_batch_size: int = 32
    embedding_cache_ttl: int = 86400

    # S3 / Object Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "heart-dev"
    s3_region: str = "us-east-1"

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

    # Memory Extractor Mode (Phase D — regex sunset)
    # Deprecated: "regex", "dual" — will be removed in 60 days (Phase D §5.3)
    memory_extractor_mode: str = (
        "llm"  # "llm" (default) | "regex" (deprecated) | "dual" (deprecated)
    )
    memory_extractor_llm_model: str = "deepseek-chat"
    memory_extractor_batch_turns: int = 6
    memory_extractor_idle_secs: int = 30
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

    # OTP
    otp_pepper: str = "change-me-otp-pepper-32chars-min"
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_per_hour: int = 5
    otp_max_attempts: int = 5

    # Email (SMTP)
    email_provider: str = "smtp"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "yuoyuo <no-reply@yuoyuo.app>"

    # Credits / Billing
    signup_grant_credits: int = 100
    credits_per_text_turn: int = 1
    credits_per_voice_turn: int = 5
    afdian_user_id: str = ""
    afdian_webhook_token: str = ""
    afdian_sponsor_url: str = "https://afdian.com/a/yuoyuo"

    # Push Notifications (V1)
    fcm_credentials_path: str = ""
    apns_credentials_path: str = ""

    # Payment (V1)
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # MiniMax TTS
    minimax_api_key: str | None = None
    minimax_group_id: str | None = None
    minimax_base_url: str = "https://api.minimax.io/v1"
    minimax_rin_clone_voice_id: str | None = None
    minimax_dorothy_voice_id: str | None = None
    minimax_tts_model: str = "speech-2.8-hd"
    minimax_language_boost: str | None = "Chinese"
    voice_profiles: str | None = None

    # MiMo TTS (voiceclone v2.5)
    mimo_api_key: str | None = None
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    mimo_reference_audio_path: str = "assets/reference_voices/rin.wav"
    mimo_model: str = "mimo-v2.5-tts-voiceclone"
    voice_provider: str = "minimax"  # "mimo" | "minimax"
    voice_fallback_enabled: bool = True

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
