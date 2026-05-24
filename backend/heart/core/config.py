"""应用全局配置"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（从环境变量读取）"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: str = "development"
    heart_env: str = "dev"
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

    # Cost Limits
    user_daily_cost_limit: float = 10.0
    alert_cost_threshold: float = 5.0

    # Security
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200

    # Push Notifications (V1)
    fcm_credentials_path: str = ""
    apns_credentials_path: str = ""

    # Payment (V1)
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Enforce mandatory secrets in non-dev environments."""
        if self.heart_env.lower() not in ("dev", "development", "test"):
            if self.jwt_secret_key == "your-secret-key-here":
                raise ValueError(
                    "jwt_secret_key must be set in production. "
                    "Default value 'your-secret-key-here' is not allowed."
                )
        return self


# 全局配置实例
settings = Settings()
