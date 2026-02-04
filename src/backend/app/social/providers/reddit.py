"""
Reddit Data Provider

Fetches posts and comments from Reddit using PRAW (Python Reddit API Wrapper).
Focuses on finance-related subreddits like r/wallstreetbets, r/stocks, etc.
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


# Default subreddits for stock-related content
DEFAULT_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "stockmarket",
    "options",
    "SecurityAnalysis",
]

# Stock ticker pattern (1-5 uppercase letters, optionally with $)
TICKER_PATTERN = re.compile(r'\$?([A-Z]{1,5})\b')

# Common words to exclude from ticker detection
TICKER_EXCLUSIONS = {
    "I", "A", "THE", "AND", "FOR", "TO", "IN", "ON", "AT", "IS", "IT",
    "BE", "AS", "SO", "OR", "IF", "MY", "BY", "UP", "GO", "DO", "NO",
    "ALL", "ARE", "BUT", "NOT", "YOU", "CAN", "HAD", "HER", "WAS", "ONE",
    "OUR", "OUT", "HAS", "HIS", "HOW", "MAN", "NEW", "NOW", "OLD", "SEE",
    "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO",
    "USE", "DAY", "GET", "HIM", "MAY", "BIG", "HIGH", "LOW", "LONG",
    "CEO", "CFO", "IPO", "ETF", "SEC", "FDA", "USA", "USD", "EUR", "GDP",
    "PE", "EPS", "RSI", "ATH", "ATL", "DD", "YOLO", "FOMO", "FUD", "IMO",
    "TL", "DR", "EDIT", "TLDR", "OP", "OC", "NSFW", "AMA", "TIL", "ELI",
    "PM", "AM", "EST", "PST", "UTC", "EOD", "AH", "PM", "CALLS", "PUTS",
}


@ProviderRegistry.register(SocialPlatform.REDDIT)
class RedditProvider(BaseSocialProvider):
    """
    Reddit data provider using PRAW.

    Requires environment variables:
    - REDDIT_CLIENT_ID
    - REDDIT_CLIENT_SECRET
    - REDDIT_USER_AGENT (optional, has default)
    """

    platform = SocialPlatform.REDDIT
    name = "reddit"

    def __init__(self):
        super().__init__()
        self.reddit = None
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = os.getenv(
            "REDDIT_USER_AGENT",
            "python:ai-note-stock-analyzer:v1.0 (by /u/your_username)"
        )

    def check_availability(self) -> bool:
        """Check if Reddit API credentials are available"""
        try:
            import praw
            self._available = bool(self.client_id and self.client_secret)
            if not self._available:
                logger.warning("Reddit credentials not configured. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
            return self._available
        except ImportError:
            logger.warning("praw not installed. Run: pip install praw")
            self._available = False
            return False

    async def initialize(self) -> bool:
        """Initialize Reddit client"""
        if self._initialized:
            return True

        try:
            import praw

            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )

            # Test connection (read-only)
            self.reddit.read_only = True
            _ = self.reddit.user.me()  # This will be None for read-only

            self._initialized = True
            logger.info("Reddit provider initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Reddit provider: {e}")
            return False

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text"""
        if not text:
            return []

        matches = TICKER_PATTERN.findall(text.upper())
        tickers = [m for m in matches if m not in TICKER_EXCLUSIONS and len(m) >= 2]

        # Deduplicate while preserving order
        seen = set()
        return [t for t in tickers if not (t in seen or seen.add(t))]

    def _submission_to_post(self, submission, subreddit: str) -> SocialPost:
        """Convert Reddit submission to SocialPost"""
        content = submission.selftext or ""
        title = submission.title or ""
        full_text = f"{title} {content}"

        symbols = self._extract_tickers(full_text)

        return SocialPost(
            platform=SocialPlatform.REDDIT,
            platform_id=submission.id,
            post_type=PostType.POST,
            title=title,
            content=content[:5000],  # Limit content length
            author=str(submission.author) if submission.author else "[deleted]",
            url=f"https://reddit.com{submission.permalink}",
            symbols=symbols,
            upvotes=submission.score,
            downvotes=0,  # Reddit doesn't expose downvotes directly
            comments_count=submission.num_comments,
            shares=0,
            subreddit=subreddit,
            posted_at=datetime.fromtimestamp(submission.created_utc),
        )

    def _comment_to_post(self, comment, subreddit: str) -> SocialPost:
        """Convert Reddit comment to SocialPost"""
        content = comment.body or ""
        symbols = self._extract_tickers(content)

        return SocialPost(
            platform=SocialPlatform.REDDIT,
            platform_id=comment.id,
            post_type=PostType.COMMENT,
            title=None,
            content=content[:5000],
            author=str(comment.author) if comment.author else "[deleted]",
            url=f"https://reddit.com{comment.permalink}",
            symbols=symbols,
            upvotes=comment.score,
            downvotes=0,
            comments_count=0,
            shares=0,
            subreddit=subreddit,
            posted_at=datetime.fromtimestamp(comment.created_utc),
        )

    async def get_posts_for_symbol(
        self,
        symbol: str,
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Get posts mentioning a stock symbol"""
        if not self._initialized:
            await self.initialize()

        posts = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        def fetch():
            nonlocal posts
            for subreddit_name in DEFAULT_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Search for symbol mentions
                    search_queries = [f"${symbol}", symbol]
                    for query in search_queries:
                        for submission in subreddit.search(
                            query,
                            sort="new",
                            time_filter="day" if max_age_hours <= 24 else "week",
                            limit=limit // len(DEFAULT_SUBREDDITS),
                        ):
                            post_time = datetime.fromtimestamp(submission.created_utc)
                            if post_time < cutoff_time:
                                continue

                            post = self._submission_to_post(submission, subreddit_name)
                            if symbol.upper() in post.symbols:
                                posts.append(post)

                except Exception as e:
                    logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                    continue

        # Run in thread pool (PRAW is synchronous)
        await asyncio.get_event_loop().run_in_executor(None, fetch)

        # Deduplicate by platform_id
        seen_ids = set()
        unique_posts = []
        for post in posts:
            if post.platform_id not in seen_ids:
                seen_ids.add(post.platform_id)
                unique_posts.append(post)

        # Sort by engagement and limit
        unique_posts.sort(key=lambda p: p.engagement_score, reverse=True)
        return unique_posts[:limit]

    async def get_trending(self, limit: int = 20) -> List[TrendingStock]:
        """Get trending stocks on Reddit"""
        if not self._initialized:
            await self.initialize()

        # Collect all posts from hot submissions
        all_posts = []

        def fetch():
            nonlocal all_posts
            for subreddit_name in DEFAULT_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    for submission in subreddit.hot(limit=50):
                        post = self._submission_to_post(submission, subreddit_name)
                        all_posts.append(post)
                except Exception as e:
                    logger.error(f"Error fetching hot from r/{subreddit_name}: {e}")

        await asyncio.get_event_loop().run_in_executor(None, fetch)

        # Count symbol mentions and engagement
        symbol_stats = {}
        for post in all_posts:
            for symbol in post.symbols:
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        "mentions": 0,
                        "engagement": 0,
                        "bullish": 0,
                        "bearish": 0,
                        "subreddits": set(),
                    }
                symbol_stats[symbol]["mentions"] += 1
                symbol_stats[symbol]["engagement"] += post.engagement_score
                symbol_stats[symbol]["subreddits"].add(post.subreddit)

                # Simple sentiment from upvotes
                if post.upvotes > 50:
                    symbol_stats[symbol]["bullish"] += 1
                elif post.upvotes < 0:
                    symbol_stats[symbol]["bearish"] += 1

        # Sort by mentions and create trending list
        sorted_symbols = sorted(
            symbol_stats.items(),
            key=lambda x: (x[1]["mentions"], x[1]["engagement"]),
            reverse=True,
        )

        trending = []
        for rank, (symbol, stats) in enumerate(sorted_symbols[:limit], 1):
            bullish = stats["bullish"]
            bearish = stats["bearish"]
            total = bullish + bearish + 1  # Avoid division by zero

            sentiment_score = (bullish - bearish) / total
            if sentiment_score > 0.3:
                label = SentimentLabel.BULLISH
            elif sentiment_score < -0.3:
                label = SentimentLabel.BEARISH
            else:
                label = SentimentLabel.NEUTRAL

            trending.append(TrendingStock(
                rank=rank,
                symbol=symbol,
                mentions_count=stats["mentions"],
                mentions_change_pct=0.0,  # Would need historical data
                sentiment_score=sentiment_score,
                sentiment_label=label,
                platforms=[SocialPlatform.REDDIT],
                top_subreddits=list(stats["subreddits"])[:3],
            ))

        return trending

    async def search(
        self,
        keywords: List[str],
        limit: int = 50,
        max_age_hours: int = 24,
    ) -> List[SocialPost]:
        """Search posts by keywords"""
        if not self._initialized:
            await self.initialize()

        posts = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        query = " OR ".join(keywords)

        def fetch():
            nonlocal posts
            for subreddit_name in DEFAULT_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    for submission in subreddit.search(
                        query,
                        sort="new",
                        time_filter="day" if max_age_hours <= 24 else "week",
                        limit=limit // len(DEFAULT_SUBREDDITS),
                    ):
                        post_time = datetime.fromtimestamp(submission.created_utc)
                        if post_time < cutoff_time:
                            continue
                        posts.append(self._submission_to_post(submission, subreddit_name))
                except Exception as e:
                    logger.error(f"Error searching r/{subreddit_name}: {e}")

        await asyncio.get_event_loop().run_in_executor(None, fetch)

        # Sort by time and limit
        posts.sort(key=lambda p: p.posted_at, reverse=True)
        return posts[:limit]

    async def get_subreddit_posts(
        self,
        subreddit_name: str,
        sort: str = "hot",
        limit: int = 50,
    ) -> List[SocialPost]:
        """Get posts from a specific subreddit"""
        if not self._initialized:
            await self.initialize()

        posts = []

        def fetch():
            nonlocal posts
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                if sort == "hot":
                    submissions = subreddit.hot(limit=limit)
                elif sort == "new":
                    submissions = subreddit.new(limit=limit)
                elif sort == "top":
                    submissions = subreddit.top(limit=limit, time_filter="day")
                else:
                    submissions = subreddit.hot(limit=limit)

                for submission in submissions:
                    posts.append(self._submission_to_post(submission, subreddit_name))
            except Exception as e:
                logger.error(f"Error fetching r/{subreddit_name}: {e}")

        await asyncio.get_event_loop().run_in_executor(None, fetch)
        return posts
