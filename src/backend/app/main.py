"""
FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api import chat_router, conversations_router
from .api.notifications import router as notifications_router
from .api.stock import router as stock_router
from .api.memory import router as memory_router
from .api.tasks import router as tasks_router
from .api.social import router as social_router
from .channels import notification_service
from .tasks import init_task_service
from .social import init_social_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup: Configure notification channels from environment
    configured = notification_service.configure_from_env()
    print(f"[App] Notification channels ready: {[c.value for c in configured]}")

    # Initialize memory index
    memory_index = None
    try:
        from .core.deps import get_memory_index
        memory_index = await get_memory_index()
        if memory_index:
            stats = memory_index.get_stats()
            print(f"[App] Memory index ready: {stats['chunks']} chunks, {stats['embedding_provider']} provider")
    except Exception as e:
        print(f"[App] Memory index initialization failed (non-fatal): {e}")

    # Initialize social service
    try:
        social_service = init_social_service(db_path="./data/social.db")
        platforms = social_service.get_available_platforms()
        print(f"[App] Social service ready: platforms={platforms}")
    except Exception as e:
        print(f"[App] Social service initialization failed (non-fatal): {e}")

    # Initialize task service
    try:
        from .api.stock import get_stock_service
        stock_service = await get_stock_service()

        task_service = init_task_service(
            db_path="./data/tasks.db",
            stock_service=stock_service,
            notification_service=notification_service,
            memory_index=memory_index,
        )
        task_service.start_scheduler()
        print("[App] Task scheduler started")
    except Exception as e:
        print(f"[App] Task service initialization failed (non-fatal): {e}")

    yield

    # Shutdown: Stop task scheduler
    try:
        from .tasks import get_task_service
        task_service = get_task_service()
        await task_service.stop_scheduler()
        print("[App] Task scheduler stopped")
    except Exception:
        pass

    print("[App] Shutting down...")


# Create application
app = FastAPI(
    title=settings.app_name,
    description="Personal AI Assistant API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(stock_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(social_router, prefix="/api")


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
