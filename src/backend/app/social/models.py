"""
Social Media Data Models

Defines data structures for social media posts, sentiments, and trending data.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class SocialPlatform(str, Enum):
    """Supported social media platforms"""
    REDDIT = "reddit"
    STOCKTWITS = "stocktwits"
    TWITTER = "twitter"
    DISCORD = "discord"


class PostType(str, Enum):
    """Type of social post"""
    POST = "post"           # Original post
    COMMENT = "comment"     # Comment/reply
    RETWEET = "retweet"     # Repost/retweet


class SentimentLabel(str, Enum):
    """Sentiment classification"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


# ==================== Core Models ====================

class SocialPost(BaseModel):
    """A social media post/comment"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: SocialPlatform
    platform_id: str  # Original ID from the platform
    post_type: PostType = PostType.POST

    # Content
    title: Optional[str] = None  # For Reddit posts
    content: str
    author: str
    url: Optional[str] = None

    # Symbols mentioned
    symbols: List[str] = []  # e.g., ["TSLA", "AAPL"]

    # Engagement metrics
    upvotes: int = 0
    downvotes: int = 0
    comments_count: int = 0
    shares: int = 0

    # Sentiment (computed)
    sentiment_score: float = 0.0  # -1 to 1
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL

    # Metadata
    subreddit: Optional[str] = None  # For Reddit
    hashtags: List[str] = []  # For Twitter

    # Timestamps
    posted_at: datetime
    collected_at: datetime = Field(default_factory=datetime.now)

    @property
    def engagement_score(self) -> int:
        """Calculate overall engagement score"""
        return self.upvotes + self.comments_count * 2 + self.shares * 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "platform": self.platform.value,
            "platform_id": self.platform_id,
            "post_type": self.post_type.value,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "url": self.url,
            "symbols": ",".join(self.symbols),
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "comments_count": self.comments_count,
            "shares": self.shares,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label.value,
            "subreddit": self.subreddit,
            "hashtags": ",".join(self.hashtags),
            "posted_at": self.posted_at.isoformat(),
            "collected_at": self.collected_at.isoformat(),
        }


class SocialSentiment(BaseModel):
    """Aggregated sentiment for a symbol"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    platform: Optional[SocialPlatform] = None  # None = all platforms

    # Counts
    total_posts: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0

    # Scores
    sentiment_score: float = 0.0  # -1 to 1, weighted by engagement
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    confidence: float = 0.0  # 0 to 1

    # Trends
    mentions_1h: int = 0
    mentions_24h: int = 0
    mentions_7d: int = 0
    mention_change_pct: float = 0.0  # vs previous period

    # Engagement
    total_engagement: int = 0
    avg_engagement: float = 0.0

    # Top content
    top_posts: List[SocialPost] = []
    key_themes: List[str] = []  # Extracted themes/keywords

    # Timestamps
    period_start: datetime = Field(default_factory=datetime.now)
    period_end: datetime = Field(default_factory=datetime.now)
    computed_at: datetime = Field(default_factory=datetime.now)


class TrendingStock(BaseModel):
    """A trending stock on social media"""
    rank: int
    symbol: str
    name: Optional[str] = None

    # Metrics
    mentions_count: int = 0
    mentions_change_pct: float = 0.0
    sentiment_score: float = 0.0
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL

    # Sources
    platforms: List[SocialPlatform] = []
    top_subreddits: List[str] = []

    # Timestamp
    computed_at: datetime = Field(default_factory=datetime.now)


class CollectionTask(BaseModel):
    """Task for collecting social media data"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: SocialPlatform

    # What to collect
    symbols: List[str] = []  # Empty = trending/general
    subreddits: List[str] = []  # For Reddit
    keywords: List[str] = []

    # Limits
    max_posts: int = 100
    max_age_hours: int = 24

    # Status
    status: str = "pending"  # pending, running, completed, failed
    posts_collected: int = 0
    error: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ==================== API Models ====================

class CollectRequest(BaseModel):
    """Request to collect social data"""
    platforms: List[SocialPlatform] = [SocialPlatform.REDDIT]
    symbols: List[str] = []
    subreddits: List[str] = []
    keywords: List[str] = []
    max_posts: int = 100


class SentimentRequest(BaseModel):
    """Request for sentiment analysis"""
    symbol: str
    platforms: Optional[List[SocialPlatform]] = None
    hours: int = 24


class TrendingRequest(BaseModel):
    """Request for trending stocks"""
    platforms: Optional[List[SocialPlatform]] = None
    limit: int = 20
