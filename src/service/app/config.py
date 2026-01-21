"""Application configuration management."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "AI Notes"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./data/database/notes.db"

    # AI Service (choose: 'claude' or 'deepseek')
    ai_service: str = "claude"

    # Claude settings
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # DeepSeek settings (cheaper, good for debugging)
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # OpenAI settings (optional, for future use)
    openai_api_key: str = ""

    # Storage paths
    notes_base_path: str = "./data/notes"
    backup_path: str = "./data/backups"
    log_path: str = "./data/logs"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Agent System
    auto_start_agents: bool = False  # Set to True to auto-start agents on app startup
    agent_schedule_interval: int = 60  # Schedule agent check interval in seconds
    agent_content_interval: int = 300  # Content agent analysis interval in seconds

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def notes_raw_path(self) -> Path:
        """Path to raw notes directory."""
        return Path(self.notes_base_path) / "raw"

    @property
    def notes_organized_path(self) -> Path:
        """Path to organized notes directory."""
        return Path(self.notes_base_path) / "organized"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
