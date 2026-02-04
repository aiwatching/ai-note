"""
Social Media Service

Unified interface for collecting and analyzing social media data.
Coordinates between providers, store, and analyzer.
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from .models import (
    SocialPlatform,
    SocialPost,
    SocialSentiment,
    TrendingStock,
    CollectionTask,
)
from .store import SocialStore
from .analyzer import SocialAnalyzer
from .providers import ProviderRegistry, BaseSocialProvider


logger = logging.getLogger(__name__)


# Global service instance
_social_service: Optional["SocialService"] = None


class SocialService:
    """
    Social media data service.

    Provides a unified interface for:
    - Collecting posts from multiple platforms
    - Storing and retrieving posts
    - Computing sentiment analysis
    - Getting trending stocks
    """

    def __init__(
        self,
        db_path: str = "data/social.db",
        llm_service=None,
    ):
        self.store = SocialStore(db_path)
        self.analyzer = SocialAnalyzer(self.store, llm_service)
        self.llm = llm_service
        self._initialized_providers: Dict[SocialPlatform, bool] = {}

    async def _get_provider(self, platform: SocialPlatform) -> Optional[BaseSocialProvider]:
        """Get and initialize a provider"""
        provider = await ProviderRegistry.get_initialized(platform)
        if provider:
            self._initialized_providers[platform] = True
        return provider

    # ==================== Collection ====================

    async def collect_for_symbol(
        self,
        symbol: str,
        platforms: Optional[List[SocialPlatform]] = None,
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> Dict[str, int]:
        """
        Collect posts for a symbol from specified platforms.

        Args:
            symbol: Stock ticker symbol
            platforms: Platforms to collect from (default: all available)
            limit: Max posts per platform
            max_age_hours: Maximum age of posts

        Returns:
            Dict mapping platform to posts collected count
        """
        if platforms is None:
            platforms = ProviderRegistry.get_available()

        results = {}

        for platform in platforms:
            try:
                provider = await self._get_provider(platform)
                if not provider:
                    results[platform.value] = 0
                    continue

                posts = await provider.get_posts_for_symbol(
                    symbol, limit=limit, max_age_hours=max_age_hours
                )

                # Analyze sentiment
                analyzed_posts = self.analyzer.analyze_posts(posts)

                # Save to store
                saved = self.store.save_posts(analyzed_posts)
                results[platform.value] = saved

                logger.info(f"Collected {saved} posts for {symbol} from {platform.value}")

            except Exception as e:
                logger.error(f"Failed to collect from {platform.value}: {e}")
                results[platform.value] = 0

        return results

    async def collect_for_symbols(
        self,
        symbols: List[str],
        platforms: Optional[List[SocialPlatform]] = None,
        limit_per_symbol: int = 30,
    ) -> Dict[str, Dict[str, int]]:
        """
        Collect posts for multiple symbols.

        Args:
            symbols: List of stock symbols
            platforms: Platforms to use
            limit_per_symbol: Posts per symbol per platform

        Returns:
            Nested dict: symbol -> platform -> count
        """
        results = {}
        for symbol in symbols:
            results[symbol] = await self.collect_for_symbol(
                symbol, platforms, limit=limit_per_symbol
            )
        return results

    async def collect_trending(
        self,
        platforms: Optional[List[SocialPlatform]] = None,
        limit: int = 20,
    ) -> List[TrendingStock]:
        """
        Collect trending stocks from platforms.

        Args:
            platforms: Platforms to check
            limit: Max trending stocks to return

        Returns:
            Combined list of trending stocks
        """
        if platforms is None:
            platforms = ProviderRegistry.get_available()

        all_trending = []

        for platform in platforms:
            try:
                provider = await self._get_provider(platform)
                if not provider:
                    continue

                trending = await provider.get_trending(limit=limit)
                all_trending.extend(trending)

            except Exception as e:
                logger.error(f"Failed to get trending from {platform.value}: {e}")

        # Merge trending by symbol
        symbol_stats: Dict[str, Dict] = {}
        for stock in all_trending:
            if stock.symbol not in symbol_stats:
                symbol_stats[stock.symbol] = {
                    "mentions": 0,
                    "sentiment_sum": 0,
                    "platforms": set(),
                    "name": stock.name,
                    "subreddits": set(),
                }
            stats = symbol_stats[stock.symbol]
            stats["mentions"] += stock.mentions_count
            stats["sentiment_sum"] += stock.sentiment_score * stock.mentions_count
            stats["platforms"].update(stock.platforms)
            stats["subreddits"].update(stock.top_subreddits)

        # Create merged list
        merged = []
        for symbol, stats in symbol_stats.items():
            avg_sentiment = stats["sentiment_sum"] / max(stats["mentions"], 1)

            from .models import SentimentLabel
            if avg_sentiment > 0.2:
                label = SentimentLabel.BULLISH
            elif avg_sentiment < -0.2:
                label = SentimentLabel.BEARISH
            else:
                label = SentimentLabel.NEUTRAL

            merged.append(TrendingStock(
                rank=0,  # Will be set after sorting
                symbol=symbol,
                name=stats["name"],
                mentions_count=stats["mentions"],
                sentiment_score=avg_sentiment,
                sentiment_label=label,
                platforms=list(stats["platforms"]),
                top_subreddits=list(stats["subreddits"])[:3],
            ))

        # Sort and assign ranks
        merged.sort(key=lambda x: x.mentions_count, reverse=True)
        for i, stock in enumerate(merged[:limit]):
            stock.rank = i + 1

        # Save to store
        if merged:
            self.store.save_trending(merged[:limit])

        return merged[:limit]

    async def search(
        self,
        keywords: List[str],
        platforms: Optional[List[SocialPlatform]] = None,
        limit: int = 50,
    ) -> List[SocialPost]:
        """
        Search posts by keywords.

        Args:
            keywords: Keywords to search
            platforms: Platforms to search
            limit: Max posts to return

        Returns:
            List of matching posts
        """
        if platforms is None:
            platforms = ProviderRegistry.get_available()

        all_posts = []

        for platform in platforms:
            try:
                provider = await self._get_provider(platform)
                if not provider:
                    continue

                posts = await provider.search(keywords, limit=limit // len(platforms))
                analyzed = self.analyzer.analyze_posts(posts)
                all_posts.extend(analyzed)

                # Save to store
                self.store.save_posts(analyzed)

            except Exception as e:
                logger.error(f"Search failed on {platform.value}: {e}")

        # Sort by engagement and limit
        all_posts.sort(key=lambda p: p.engagement_score, reverse=True)
        return all_posts[:limit]

    # ==================== Query ====================

    def get_posts(
        self,
        symbol: Optional[str] = None,
        platform: Optional[SocialPlatform] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[SocialPost]:
        """
        Get stored posts.

        Args:
            symbol: Filter by symbol
            platform: Filter by platform
            hours: Time window
            limit: Max posts

        Returns:
            List of posts
        """
        if symbol:
            return self.store.get_posts_for_symbol(symbol, platform, hours, limit)
        else:
            return self.store.get_recent_posts(platform, hours, limit)

    def search_stored(
        self,
        query: str,
        hours: int = 24,
        limit: int = 50,
    ) -> List[SocialPost]:
        """Search stored posts by content"""
        return self.store.search_posts(query, hours, limit)

    # ==================== Sentiment ====================

    def get_sentiment(
        self,
        symbol: str,
        hours: int = 24,
        platform: Optional[str] = None,
    ) -> SocialSentiment:
        """
        Get sentiment for a symbol.

        First checks for recent cached sentiment, otherwise computes fresh.

        Args:
            symbol: Stock symbol
            hours: Time period
            platform: Optional platform filter

        Returns:
            SocialSentiment with metrics
        """
        from .models import SocialPlatform

        platform_enum = SocialPlatform(platform) if platform else None

        # Check for cached sentiment
        cached = self.store.get_latest_sentiment(symbol, platform_enum)
        if cached:
            # Use cached if less than 1 hour old
            age = (datetime.now() - cached.computed_at).total_seconds()
            if age < 3600:
                return cached

        # Compute fresh sentiment
        return self.analyzer.compute_sentiment(symbol, hours, platform)

    async def get_sentiment_with_llm(
        self,
        symbol: str,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get enhanced sentiment analysis using LLM.

        Args:
            symbol: Stock symbol
            hours: Time period

        Returns:
            Dict with sentiment and LLM analysis
        """
        # Get basic sentiment
        sentiment = self.get_sentiment(symbol, hours)

        # Get LLM analysis
        posts = self.store.get_posts_for_symbol(symbol, hours=hours, limit=50)
        llm_analysis = await self.analyzer.analyze_with_llm(symbol, posts)

        return {
            "sentiment": sentiment,
            "llm_analysis": llm_analysis,
        }

    # ==================== Trending ====================

    def get_trending(self, limit: int = 20) -> List[TrendingStock]:
        """Get cached trending stocks"""
        return self.store.get_latest_trending(limit)

    # ==================== Stats ====================

    def get_available_platforms(self) -> List[str]:
        """Get list of available platforms"""
        return [p.value for p in ProviderRegistry.get_available()]

    def get_stats(self) -> Dict:
        """Get service statistics"""
        store_stats = self.store.get_stats()
        return {
            **store_stats,
            "available_platforms": self.get_available_platforms(),
            "initialized_providers": list(self._initialized_providers.keys()),
        }

    # ==================== Cleanup ====================

    def cleanup(self, days: int = 7):
        """Clean up old data"""
        posts_deleted = self.store.cleanup_old_posts(days)
        sentiments_deleted = self.store.cleanup_old_sentiments(days * 4)
        return {
            "posts_deleted": posts_deleted,
            "sentiments_deleted": sentiments_deleted,
        }


# ==================== Global Instance ====================

def get_social_service() -> SocialService:
    """Get global social service instance"""
    global _social_service
    if _social_service is None:
        _social_service = SocialService()
    return _social_service


def init_social_service(
    db_path: str = "data/social.db",
    llm_service=None,
) -> SocialService:
    """Initialize global social service"""
    global _social_service
    _social_service = SocialService(db_path, llm_service)
    return _social_service
