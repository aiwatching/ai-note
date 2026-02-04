"""
Social Media Data Providers

Each provider implements the BaseSocialProvider interface for
fetching data from a specific platform.
"""
from .base import BaseSocialProvider, ProviderRegistry
from .reddit import RedditProvider
from .stocktwits import StockTwitsProvider
from .twitter import TwitterProvider

__all__ = [
    "BaseSocialProvider",
    "ProviderRegistry",
    "RedditProvider",
    "StockTwitsProvider",
    "TwitterProvider",
]
