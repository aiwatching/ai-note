"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import get_settings
from .database import init_db
from .api import notes, search, todos, schedule, agents, entities
from .agents.scheduler import get_scheduler
from .agents.schedule_agent import ScheduleAgent
from .agents.content_agent import ContentAgent

settings = get_settings()


def setup_agents():
    """Setup and register all agents with the scheduler."""
    scheduler = get_scheduler()

    # Create and register Schedule Agent
    schedule_agent = ScheduleAgent(
        interval_seconds=60,  # Check every minute
        reminder_window_minutes=15,  # Send reminders 15 minutes before
    )
    scheduler.register_agent(schedule_agent)

    # Create and register Content Agent
    content_agent = ContentAgent(
        interval_seconds=300,  # Run every 5 minutes
        similarity_threshold=0.3,
    )
    scheduler.register_agent(content_agent)

    logger.info(f"Registered {len(scheduler.list_agents())} agents")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    init_db()

    # Setup agents
    setup_agents()

    # Optionally auto-start agents (can be controlled via config)
    if settings.auto_start_agents:
        scheduler = get_scheduler()
        await scheduler.start()
        logger.info("Agent system auto-started")

    yield

    # Shutdown: Stop agents and cleanup
    scheduler = get_scheduler()
    if scheduler.is_running:
        await scheduler.stop()
        logger.info("Agent system stopped")


app = FastAPI(
    title=settings.app_name,
    description="An intelligent note-taking system with AI-powered analysis and search",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(todos.router, prefix="/api/v1/todos", tags=["todos"])
app.include_router(schedule.router, prefix="/api/v1", tags=["schedules"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(entities.router, prefix="/api/v1/entities", tags=["entities"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to AI Notes API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    scheduler = get_scheduler()
    return {
        "status": "healthy",
        "agents": {
            "running": scheduler.is_running,
            "count": len(scheduler.list_agents()),
        },
    }
