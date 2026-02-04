"""
StockTwits Data Provider

Fetches posts from StockTwits API.
StockTwits is a social network specifically for traders and investors.

API Documentation: https://api.stocktwits.com/developers/docs
"""
import os
import aiohttp
from datetime import datetime
from typing import List, Optional
import logging

from .base import BaseSocialProvider, ProviderRegistry
from ..models import (
    SocialPlatform,
    SocialPost,
    PostType,
    TrendingStock,
    SentimentLabel,
)


logger = logging.getLogger(__name__)


BASE_URL = "https://api.stocktwits.com/api/2"


@ProviderRegistry.register(SocialPlatform.STOCKTWITS)
class StockTwitsProvider(BaseSocialProvider):
    """
    StockTwits data provider.

    Uses the free StockTwits API. No authentication required for read-only access.
    Rate limit: 200 requests per hour for unauthenticated.

    Optional environment variables:
    - STOCKTWITS_ACCESS_TOKEN (for higher rate limits)
    """

    platform = SocialPlatform.STOCKTWITS
    name = "stocktwits"

    def __init__(self):
        super().__init__()
        self.access_token = os.getenv("STOCKTWITS_ACCESS_TOKEN")
        self.session: Optional[aiohttp.ClientSession] = None

    def check_availability(self) -> bool:
        """StockTwits API is available without auth"""
        self._available = True
        return True

    async def initialize(self) -> bool:
        """Initialize HTTP session"""
        if self._initialized:
            return True

        try:
            self.session = aiohttp.ClientSession()
            self._initialized = True
            logger.info("StockTwits provider initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize StockTwits provider: {e}")
            return False

    async def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request"""
        if not self.session:
            await self.initialize()

        url = f"{BASE_URL}/{endpoint}"
        if params is None:
            params = {}

        if self.access_token:
            params["access_token"] = self.access_token

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("StockTwits rate limit reached")
                    return None
                else:
                    logger.error(f"StockTwits API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"StockTwits request failed: {e}")
            return None

    def _message_to_post(self, message: dict) -> SocialPost:
        """Convert StockTwits message to SocialPost"""
        # Extract symbols from message
        symbols = []
        if "symbols" in message:
            symbols = [s.get("symbol", "") for s in message.get("symbols", [])]

        # Get sentiment if tagged
        sentiment_label = SentimentLabel.NEUTRAL
        sentiment_score = 0.0
        if message.get("entities", {}).get("sentiment"):
            sentiment = message["entities"]["sentiment"]["basic"]
            if sentiment == "Bullish":
                sentiment_label = SentimentLabel.BULLISH
                sentiment_score = 0.5
            elif sentiment == "Bearish":
                sentiment_label = SentimentLabel.BEARISH
                sentiment_score = -0.5

        # Parse timestamp
        posted_at = datetime.now()
        if message.get("created_at"):
            try:
                posted_at = datetime.strptime(
                    message["created_at"],
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            except:
                pass

        return SocialPost(
            platform=SocialPlatform.STOCKTWITS,
            platform_id=str(message.get("id", "")),
            post_type=PostType.POST,
            title=None,
            content=message.get("body", ""),
            author=message.get("user", {}).get("username", "unknown"),
            url=f"https://stocktwits.com/{message.get('user', {}).get('username', '')}/message/{message.get('id', '')}",
            symbols=symbols,
            upvotes=message.get("likes", {}).get("total", 0),
            downvotes=0,
            comments_count=message.get("conversation", {}).get("replies", 0) if message.get("conversation") else 0,
            shares=message.get("reshares", {}).get("total", 0) if message.get("reshares") else 0,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            posted_at=posted_at,
        )

    async def get_posts_for_symbol(
        self,
        symbol: str,
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Get posts for a stock symbol"""
        data = await self._request(f"streams/symbol/{symbol}.json", {"limit": min(limit, 30)})

        if not data or "messages" not in data:
            return []

        posts = []
        for message in data["messages"]:
            post = self._message_to_post(message)
            posts.append(post)

        return posts[:limit]

    async def get_trending(self, limit: int = 20) -> List[TrendingStock]:
        """Get trending stocks on StockTwits"""
        data = await self._request("trending/symbols.json")

        if not data or "symbols" not in data:
            return []

        trending = []
        for rank, symbol_data in enumerate(data["symbols"][:limit], 1):
            symbol = symbol_data.get("symbol", "")

            # Get sentiment from watchlist count changes
            watchlist_count = symbol_data.get("watchlist_count", 0)

            trending.append(TrendingStock(
                rank=rank,
                symbol=symbol,
                name=symbol_data.get("title", ""),
                mentions_count=watchlist_count,
                mentions_change_pct=0.0,
                sentiment_score=0.0,
                sentiment_label=SentimentLabel.NEUTRAL,
                platforms=[SocialPlatform.STOCKTWITS],
                top_subreddits=[],
            ))

        return trending

    async def search(
        self,
        keywords: List[str],
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Search posts by keywords"""
        # StockTwits search is limited, use symbol search for each keyword
        all_posts = []

        for keyword in keywords:
            # Try as symbol first
            symbol_posts = await self.get_posts_for_symbol(keyword, limit=limit // len(keywords))
            all_posts.extend(symbol_posts)

        # Sort by time and deduplicate
        seen_ids = set()
        unique_posts = []
        for post in sorted(all_posts, key=lambda p: p.posted_at, reverse=True):
            if post.platform_id not in seen_ids:
                seen_ids.add(post.platform_id)
                unique_posts.append(post)

        return unique_posts[:limit]

    async def get_symbol_sentiment(self, symbol: str) -> Optional[dict]:
        """Get sentiment summary for a symbol"""
        data = await self._request(f"streams/symbol/{symbol}.json", {"limit": 30})

        if not data or "symbol" not in data:
            return None

        symbol_info = data["symbol"]

        # Count sentiment from recent messages
        bullish = 0
        bearish = 0
        total = 0

        for message in data.get("messages", []):
            sentiment = message.get("entities", {}).get("sentiment")
            if sentiment:
                total += 1
                if sentiment.get("basic") == "Bullish":
                    bullish += 1
                elif sentiment.get("basic") == "Bearish":
                    bearish += 1

        return {
            "symbol": symbol,
            "watchlist_count": symbol_info.get("watchlist_count", 0),
            "total_messages": total,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "sentiment_score": (bullish - bearish) / max(total, 1),
        }

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
