"""
Social Media Data Collection Module

Provides unified interface for collecting and analyzing social media data
from multiple platforms (Reddit, StockTwits, Twitter/X).

Architecture:
- providers/: Platform-specific data fetchers
- models.py: Data models
- store.py: SQLite persistence
- service.py: Unified service interface
- analyzer.py: Sentiment analysis
"""
from .models import (
    SocialPlatform,
    SocialPost,
    SocialSentiment,
    TrendingStock,
    CollectionTask,
)
from .store import SocialStore
from .service import SocialService, get_social_service, init_social_service

__all__ = [
    # Models
    "SocialPlatform",
    "SocialPost",
    "SocialSentiment",
    "TrendingStock",
    "CollectionTask",
    # Store
    "SocialStore",
    # Service
    "SocialService",
    "get_social_service",
    "init_social_service",
]
