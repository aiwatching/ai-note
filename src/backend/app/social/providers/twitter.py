"""
Twitter/X Data Provider

Fetches tweets from Twitter/X.

Options:
1. Official Twitter API v2 (requires paid access: $100+/month)
2. snscrape (free but may break)
3. Nitter instances (free but unreliable)

This implementation supports the official API when available,
with snscrape as fallback.
"""
import os
import re
import asyncio
from datetime import datetime, timedelta
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


# Stock ticker pattern (cashtag)
CASHTAG_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')

# Common exclusions
CASHTAG_EXCLUSIONS = {"USD", "EUR", "GBP", "JPY", "BTC", "ETH", "USDT"}


@ProviderRegistry.register(SocialPlatform.TWITTER)
class TwitterProvider(BaseSocialProvider):
    """
    Twitter/X data provider.

    Environment variables:
    - TWITTER_BEARER_TOKEN (for official API v2)
    - TWITTER_USE_SNSCRAPE (set to "true" to use snscrape fallback)
    """

    platform = SocialPlatform.TWITTER
    name = "twitter"

    def __init__(self):
        super().__init__()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.use_snscrape = os.getenv("TWITTER_USE_SNSCRAPE", "").lower() == "true"
        self.client = None
        self._use_official_api = False

    def check_availability(self) -> bool:
        """Check if Twitter API is available"""
        # Check for official API
        if self.bearer_token:
            try:
                import tweepy
                self._available = True
                self._use_official_api = True
                return True
            except ImportError:
                logger.warning("tweepy not installed. Run: pip install tweepy")

        # Check for snscrape fallback
        if self.use_snscrape:
            try:
                import snscrape.modules.twitter as sntwitter
                self._available = True
                self._use_official_api = False
                logger.info("Using snscrape for Twitter (unofficial)")
                return True
            except ImportError:
                logger.warning("snscrape not installed. Run: pip install snscrape")

        # Neither available
        logger.warning(
            "Twitter provider requires either:\n"
            "  1. TWITTER_BEARER_TOKEN (official API) + pip install tweepy\n"
            "  2. TWITTER_USE_SNSCRAPE=true + pip install snscrape"
        )
        self._available = False
        return False

    async def initialize(self) -> bool:
        """Initialize Twitter client"""
        if self._initialized:
            return True

        try:
            if self._use_official_api:
                import tweepy

                self.client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    wait_on_rate_limit=True,
                )
                logger.info("Twitter provider initialized (official API)")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Twitter provider: {e}")
            return False

    def _extract_cashtags(self, text: str) -> List[str]:
        """Extract stock cashtags from text"""
        if not text:
            return []

        matches = CASHTAG_PATTERN.findall(text.upper())
        return [m for m in matches if m not in CASHTAG_EXCLUSIONS]

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        return re.findall(r'#(\w+)', text)

    async def get_posts_for_symbol(
        self,
        symbol: str,
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Get tweets mentioning a stock symbol"""
        if not self._initialized:
            await self.initialize()

        if self._use_official_api:
            return await self._get_posts_official(symbol, limit, max_age_hours)
        else:
            return await self._get_posts_snscrape(symbol, limit, max_age_hours)

    async def _get_posts_official(
        self,
        symbol: str,
        limit: int,
        max_age_hours: int,
    ) -> List[SocialPost]:
        """Get tweets using official API"""
        posts = []
        query = f"${symbol} -is:retweet lang:en"

        try:
            def fetch():
                nonlocal posts
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(limit, 100),
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    user_fields=["username"],
                    expansions=["author_id"],
                )

                if not response.data:
                    return

                # Map user IDs to usernames
                users = {u.id: u for u in (response.includes.get("users", []) or [])}

                for tweet in response.data:
                    author = users.get(tweet.author_id)
                    username = author.username if author else "unknown"
                    metrics = tweet.public_metrics or {}

                    posts.append(SocialPost(
                        platform=SocialPlatform.TWITTER,
                        platform_id=str(tweet.id),
                        post_type=PostType.POST,
                        title=None,
                        content=tweet.text,
                        author=username,
                        url=f"https://twitter.com/{username}/status/{tweet.id}",
                        symbols=self._extract_cashtags(tweet.text),
                        upvotes=metrics.get("like_count", 0),
                        downvotes=0,
                        comments_count=metrics.get("reply_count", 0),
                        shares=metrics.get("retweet_count", 0),
                        hashtags=self._extract_hashtags(tweet.text),
                        posted_at=tweet.created_at or datetime.now(),
                    ))

            await asyncio.get_event_loop().run_in_executor(None, fetch)

        except Exception as e:
            logger.error(f"Twitter API error: {e}")

        return posts

    async def _get_posts_snscrape(
        self,
        symbol: str,
        limit: int,
        max_age_hours: int,
    ) -> List[SocialPost]:
        """Get tweets using snscrape"""
        posts = []

        def fetch():
            nonlocal posts
            try:
                import snscrape.modules.twitter as sntwitter

                query = f"${symbol} since:{datetime.now().strftime('%Y-%m-%d')}"
                scraper = sntwitter.TwitterSearchScraper(query)

                count = 0
                for tweet in scraper.get_items():
                    if count >= limit:
                        break

                    posts.append(SocialPost(
                        platform=SocialPlatform.TWITTER,
                        platform_id=str(tweet.id),
                        post_type=PostType.POST,
                        title=None,
                        content=tweet.rawContent,
                        author=tweet.user.username,
                        url=tweet.url,
                        symbols=self._extract_cashtags(tweet.rawContent),
                        upvotes=tweet.likeCount or 0,
                        downvotes=0,
                        comments_count=tweet.replyCount or 0,
                        shares=tweet.retweetCount or 0,
                        hashtags=self._extract_hashtags(tweet.rawContent),
                        posted_at=tweet.date,
                    ))
                    count += 1

            except Exception as e:
                logger.error(f"snscrape error: {e}")

        await asyncio.get_event_loop().run_in_executor(None, fetch)
        return posts

    async def get_trending(self, limit: int = 20) -> List[TrendingStock]:
        """Get trending stocks on Twitter"""
        # Twitter trending topics API requires elevated access
        # Return empty for now - would need to aggregate from cashtag searches
        logger.info("Twitter trending requires elevated API access")
        return []

    async def search(
        self,
        keywords: List[str],
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Search tweets by keywords"""
        if not self._initialized:
            await self.initialize()

        all_posts = []
        for keyword in keywords:
            # Treat keywords that look like tickers as cashtags
            if keyword.isupper() and len(keyword) <= 5:
                posts = await self.get_posts_for_symbol(keyword, limit // len(keywords))
            else:
                # General keyword search
                if self._use_official_api:
                    posts = await self._search_keyword_official(keyword, limit // len(keywords))
                else:
                    posts = await self._search_keyword_snscrape(keyword, limit // len(keywords))
            all_posts.extend(posts)

        # Deduplicate
        seen_ids = set()
        unique_posts = []
        for post in sorted(all_posts, key=lambda p: p.posted_at, reverse=True):
            if post.platform_id not in seen_ids:
                seen_ids.add(post.platform_id)
                unique_posts.append(post)

        return unique_posts[:limit]

    async def _search_keyword_official(self, keyword: str, limit: int) -> List[SocialPost]:
        """Search by keyword using official API"""
        posts = []
        query = f"{keyword} -is:retweet lang:en"

        try:
            def fetch():
                nonlocal posts
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(limit, 100),
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    user_fields=["username"],
                    expansions=["author_id"],
                )

                if not response.data:
                    return

                users = {u.id: u for u in (response.includes.get("users", []) or [])}

                for tweet in response.data:
                    author = users.get(tweet.author_id)
                    username = author.username if author else "unknown"
                    metrics = tweet.public_metrics or {}

                    posts.append(SocialPost(
                        platform=SocialPlatform.TWITTER,
                        platform_id=str(tweet.id),
                        post_type=PostType.POST,
                        title=None,
                        content=tweet.text,
                        author=username,
                        url=f"https://twitter.com/{username}/status/{tweet.id}",
                        symbols=self._extract_cashtags(tweet.text),
                        upvotes=metrics.get("like_count", 0),
                        downvotes=0,
                        comments_count=metrics.get("reply_count", 0),
                        shares=metrics.get("retweet_count", 0),
                        hashtags=self._extract_hashtags(tweet.text),
                        posted_at=tweet.created_at or datetime.now(),
                    ))

            await asyncio.get_event_loop().run_in_executor(None, fetch)

        except Exception as e:
            logger.error(f"Twitter search error: {e}")

        return posts

    async def _search_keyword_snscrape(self, keyword: str, limit: int) -> List[SocialPost]:
        """Search by keyword using snscrape"""
        posts = []

        def fetch():
            nonlocal posts
            try:
                import snscrape.modules.twitter as sntwitter

                query = f"{keyword} since:{datetime.now().strftime('%Y-%m-%d')}"
                scraper = sntwitter.TwitterSearchScraper(query)

                count = 0
                for tweet in scraper.get_items():
                    if count >= limit:
                        break

                    posts.append(SocialPost(
                        platform=SocialPlatform.TWITTER,
                        platform_id=str(tweet.id),
                        post_type=PostType.POST,
                        title=None,
                        content=tweet.rawContent,
                        author=tweet.user.username,
                        url=tweet.url,
                        symbols=self._extract_cashtags(tweet.rawContent),
                        upvotes=tweet.likeCount or 0,
                        downvotes=0,
                        comments_count=tweet.replyCount or 0,
                        shares=tweet.retweetCount or 0,
                        hashtags=self._extract_hashtags(tweet.rawContent),
                        posted_at=tweet.date,
                    ))
                    count += 1

            except Exception as e:
                logger.error(f"snscrape search error: {e}")

        await asyncio.get_event_loop().run_in_executor(None, fetch)
        return posts
