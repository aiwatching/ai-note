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

    # Notion
    notion_token: Optional[str] = None

    # 股票 API
    alpha_vantage_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# 确保数据目录存在
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)
