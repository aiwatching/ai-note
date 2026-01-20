"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .api import notes, search, todos

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup if needed


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
    return {"status": "healthy"}
