"""
Base Social Media Provider

Defines the interface that all social media providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
import logging

from ..models import SocialPlatform, SocialPost, TrendingStock


logger = logging.getLogger(__name__)


class BaseSocialProvider(ABC):
    """
    Abstract base class for social media data providers.

    Each provider must implement methods for:
    - Checking availability (API keys, dependencies)
    - Fetching posts for symbols
    - Fetching trending stocks
    - Searching by keywords
    """

    # Platform identifier
    platform: SocialPlatform

    # Provider name for logging
    name: str = "base"

    def __init__(self):
        self._initialized = False
        self._available = False

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if the provider is available (API keys, dependencies).

        Returns:
            True if provider can be used
        """
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider (authenticate, setup connections).

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def get_posts_for_symbol(
        self,
        symbol: str,
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """
        Get posts mentioning a stock symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "TSLA")
            limit: Maximum posts to return
            max_age_hours: Maximum age of posts in hours

        Returns:
            List of SocialPost objects
        """
        pass

    @abstractmethod
    async def get_trending(self, limit: int = 20) -> List[TrendingStock]:
        """
        Get trending stocks on this platform.

        Args:
            limit: Maximum stocks to return

        Returns:
            List of TrendingStock objects
        """
        pass

    @abstractmethod
    async def search(
        self,
        keywords: List[str],
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """
        Search posts by keywords.

        Args:
            keywords: Keywords to search for
            limit: Maximum posts to return
            max_age_hours: Maximum age of posts

        Returns:
            List of SocialPost objects
        """
        pass

    async def get_posts_for_symbols(
        self,
        symbols: List[str],
        limit_per_symbol: int = 20,
        max_age_hours: int = 24,
    ) -> Dict[str, List[SocialPost]]:
        """
        Get posts for multiple symbols.

        Args:
            symbols: List of stock symbols
            limit_per_symbol: Maximum posts per symbol
            max_age_hours: Maximum age of posts

        Returns:
            Dict mapping symbol to list of posts
        """
        results = {}
        for symbol in symbols:
            try:
                posts = await self.get_posts_for_symbol(
                    symbol, limit_per_symbol, max_age_hours
                )
                results[symbol] = posts
            except Exception as e:
                logger.error(f"Failed to get posts for {symbol}: {e}")
                results[symbol] = []
        return results

    @property
    def is_available(self) -> bool:
        """Check if provider is available"""
        return self._available

    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized"""
        return self._initialized


class ProviderRegistry:
    """
    Registry for social media providers.

    Manages provider registration, initialization, and access.
    """

    _providers: Dict[SocialPlatform, Type[BaseSocialProvider]] = {}
    _instances: Dict[SocialPlatform, BaseSocialProvider] = {}

    @classmethod
    def register(cls, platform: SocialPlatform):
        """
        Decorator to register a provider class.

        Usage:
            @ProviderRegistry.register(SocialPlatform.REDDIT)
            class RedditProvider(BaseSocialProvider):
                ...
        """
        def decorator(provider_class: Type[BaseSocialProvider]):
            cls._providers[platform] = provider_class
            logger.debug(f"Registered provider: {platform.value}")
            return provider_class
        return decorator

    @classmethod
    def get(cls, platform: SocialPlatform) -> Optional[BaseSocialProvider]:
        """
        Get a provider instance by platform.

        Args:
            platform: The social platform

        Returns:
            Provider instance or None if not available
        """
        if platform in cls._instances:
            return cls._instances[platform]

        if platform not in cls._providers:
            logger.warning(f"No provider registered for {platform.value}")
            return None

        # Create instance
        provider_class = cls._providers[platform]
        instance = provider_class()

        # Check availability
        if not instance.check_availability():
            logger.warning(f"Provider {platform.value} not available")
            return None

        cls._instances[platform] = instance
        return instance

    @classmethod
    async def get_initialized(cls, platform: SocialPlatform) -> Optional[BaseSocialProvider]:
        """
        Get an initialized provider instance.

        Args:
            platform: The social platform

        Returns:
            Initialized provider instance or None
        """
        provider = cls.get(platform)
        if not provider:
            return None

        if not provider.is_initialized:
            success = await provider.initialize()
            if not success:
                logger.error(f"Failed to initialize {platform.value}")
                return None

        return provider

    @classmethod
    def get_available(cls) -> List[SocialPlatform]:
        """
        Get list of available platforms.

        Returns:
            List of available platform identifiers
        """
        available = []
        for platform in cls._providers:
            provider = cls.get(platform)
            if provider and provider.is_available:
                available.append(platform)
        return available

    @classmethod
    def get_all_providers(cls) -> Dict[SocialPlatform, BaseSocialProvider]:
        """
        Get all available provider instances.

        Returns:
            Dict mapping platform to provider instance
        """
        result = {}
        for platform in cls._providers:
            provider = cls.get(platform)
            if provider:
                result[platform] = provider
        return result

    @classmethod
    def clear(cls):
        """Clear all provider instances (for testing)"""
        cls._instances.clear()
