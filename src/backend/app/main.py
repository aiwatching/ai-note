"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api import chat_router, conversations_router

# 创建应用
app = FastAPI(
    title=settings.app_name,
    description="Personal AI Assistant API",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")


@app.get("/")
async def root():
    """根路由"""
    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/info")
async def info():
    """获取应用信息"""
    from .core.deps import get_agent
    agent = get_agent()

    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "available_models": agent.llm.available_providers,
        "available_tools": agent.tools.list_tools(),
        "default_model": agent.default_provider
    }
