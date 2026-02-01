"""
配置管理
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    app_name: str = "Personal AI Assistant"
    debug: bool = True

    # 数据库
    database_url: str = "sqlite:///./data/assistant.db"

    # LLM API Keys
    claude_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # 默认模型
    default_model: str = "claude"

    # Memory & Embedding 配置
    memory_index_path: str = "./data/memory_index.db"
    embedding_provider: str = "auto"  # auto, openai, local
    embedding_model: str = "text-embedding-3-small"
    embedding_fallback: str = "local"
    embedding_local_model: str = "all-MiniLM-L6-v2"
    embedding_cache_enabled: bool = True
    embedding_cache_max_entries: int = 10000

    # Hybrid Search 配置
    search_max_results: int = 10
    search_min_score: float = 0.3
    search_hybrid_enabled: bool = True
    search_vector_weight: float = 0.7
    search_text_weight: float = 0.3

    # Notion
    notion_token: Optional[str] = None

    # Stock API
    alpha_vantage_key: Optional[str] = None
    finnhub_key: Optional[str] = None

    # Notification Channels
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    discord_bot_token: Optional[str] = None
    discord_channel_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    notification_webhook_url: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore unknown env vars


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance for dependency injection"""
    return settings


# 确保数据目录存在
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)
