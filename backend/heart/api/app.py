"""FastAPI 应用主入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from heart.core.config import settings
from heart.infra.llm import LLMProviderConfig, DeepSeekConfig, initialize_router, shutdown_router

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """创建和配置 FastAPI 应用"""

    app = FastAPI(
        title="Heart AI Companion",
        description="AI companion system with 8 specialized subsystems",
        version="0.1.0",
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动时初始化"""
        logger.info("🚀 Heart AI Companion starting up...")

        # 初始化 LLM 路由器
        llm_config = LLMProviderConfig(
            deepseek=DeepSeekConfig(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            ),
        )
        await initialize_router(llm_config)
        logger.info("✅ LLM Router initialized")

    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时清理"""
        logger.info("🛑 Heart AI Companion shutting down...")
        await shutdown_router()
        logger.info("✅ Cleanup completed")

    # 健康检查端点
    @app.get("/health/live")
    async def health_check():
        """健康检查"""
        return {"status": "alive", "service": "heart-api"}

    @app.get("/api/docs", include_in_schema=False)
    async def swagger_ui():
        """API 文档重定向"""
        from fastapi.openapi.docs import get_swagger_ui_html

        return get_swagger_ui_html(openapi_url="/openapi.json", title="Heart API")

    return app


# 应用实例
app = create_app()
