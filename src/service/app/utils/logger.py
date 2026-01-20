"""Logging configuration."""
import sys
from pathlib import Path

from loguru import logger

from ..config import get_settings


def setup_logger():
    """Configure application logging."""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Add stdout handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.debug else "INFO",
    )

    # Add file handler
    log_path = Path(settings.log_path)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path / "app.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG" if settings.debug else "INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    return logger
