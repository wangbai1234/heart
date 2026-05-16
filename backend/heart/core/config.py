"""应用全局配置"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置（从环境变量读取）"""

    # Application
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://heart:heartdev@localhost:5432/heart",
    )
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    database_max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # LLM Providers - DeepSeek
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # LLM Model Configuration
    main_llm_model: str = os.getenv("MAIN_LLM_MODEL", "deepseek-reasoner")
    cheap_llm_model: str = os.getenv("CHEAP_LLM_MODEL", "deepseek-chat")

    # Feature Flags
    enable_voice: bool = os.getenv("ENABLE_VOICE", "false").lower() == "true"
    enable_video: bool = os.getenv("ENABLE_VIDEO", "false").lower() == "true"
    enable_critic_agent: bool = os.getenv("ENABLE_CRITIC_AGENT", "true").lower() == "true"
    critic_sampling_rate: float = float(os.getenv("CRITIC_SAMPLING_RATE", "0.3"))
    enable_wellbeing_monitor: bool = (
        os.getenv("ENABLE_WELLBEING_MONITOR", "true").lower() == "true"
    )

    # Cost Limits
    user_daily_cost_limit: float = float(os.getenv("USER_DAILY_COST_LIMIT", "10.0"))
    alert_cost_threshold: float = float(os.getenv("ALERT_COST_THRESHOLD", "5.0"))

    # Security
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200")
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()
