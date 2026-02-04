"""
Social Media API Endpoints

REST API for social media data collection and sentiment analysis.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..social import (
    SocialPlatform,
    SocialPost,
    SocialSentiment,
    TrendingStock,
    get_social_service,
)


router = APIRouter(prefix="/social", tags=["social"])


# ==================== Request/Response Models ====================

class CollectRequest(BaseModel):
    """Request to collect social data"""
    symbols: List[str]
    platforms: Optional[List[str]] = None
    limit_per_symbol: int = 50
    max_age_hours: int = 24


class CollectResponse(BaseModel):
    """Collection result"""
    success: bool
    results: dict
    message: str


class SentimentResponse(BaseModel):
    """Sentiment analysis response"""
    symbol: str
    platform: Optional[str]
    total_posts: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    sentiment_score: float
    sentiment_label: str
    confidence: float
    mentions_24h: int
    key_themes: List[str]


class PostResponse(BaseModel):
    """Social post response"""
    id: str
    platform: str
    content: str
    author: str
    url: Optional[str]
    symbols: List[str]
    upvotes: int
    comments_count: int
    sentiment_score: float
    sentiment_label: str
    posted_at: str


class TrendingResponse(BaseModel):
    """Trending stock response"""
    rank: int
    symbol: str
    name: Optional[str]
    mentions_count: int
    sentiment_score: float
    sentiment_label: str
    platforms: List[str]


class StatsResponse(BaseModel):
    """Service statistics"""
    total_posts: int
    unique_symbols: int
    sentiment_snapshots: int
    posts_by_platform: dict
    available_platforms: List[str]


# ==================== Helper Functions ====================

def get_service():
    """Get social service instance"""
    return get_social_service()


def post_to_response(post: SocialPost) -> PostResponse:
    """Convert SocialPost to response"""
    return PostResponse(
        id=post.id,
        platform=post.platform.value,
        content=post.content[:500],  # Limit content
        author=post.author,
        url=post.url,
        symbols=post.symbols,
        upvotes=post.upvotes,
        comments_count=post.comments_count,
        sentiment_score=post.sentiment_score,
        sentiment_label=post.sentiment_label.value,
        posted_at=post.posted_at.isoformat(),
    )


# ==================== Collection Endpoints ====================

@router.post("/collect", response_model=CollectResponse)
async def collect_data(request: CollectRequest):
    """
    Collect social media data for symbols.

    This triggers data collection from configured platforms.
    """
    service = get_service()

    platforms = None
    if request.platforms:
        try:
            platforms = [SocialPlatform(p) for p in request.platforms]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {e}")

    try:
        results = await service.collect_for_symbols(
            symbols=request.symbols,
            platforms=platforms,
            limit_per_symbol=request.limit_per_symbol,
        )

        total_collected = sum(
            sum(counts.values())
            for counts in results.values()
        )

        return CollectResponse(
            success=True,
            results=results,
            message=f"Collected {total_collected} posts for {len(request.symbols)} symbols",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/trending", response_model=List[TrendingResponse])
async def collect_trending(
    platforms: Optional[List[str]] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Collect and return trending stocks from social media.
    """
    service = get_service()

    platform_enums = None
    if platforms:
        try:
            platform_enums = [SocialPlatform(p) for p in platforms]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {e}")

    trending = await service.collect_trending(platforms=platform_enums, limit=limit)

    return [
        TrendingResponse(
            rank=t.rank,
            symbol=t.symbol,
            name=t.name,
            mentions_count=t.mentions_count,
            sentiment_score=t.sentiment_score,
            sentiment_label=t.sentiment_label.value,
            platforms=[p.value for p in t.platforms],
        )
        for t in trending
    ]


# ==================== Query Endpoints ====================

@router.get("/sentiment/{symbol}", response_model=SentimentResponse)
async def get_sentiment(
    symbol: str,
    platform: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
):
    """
    Get sentiment analysis for a symbol.

    Uses cached data if available, otherwise computes from stored posts.
    """
    service = get_service()

    sentiment = service.get_sentiment(
        symbol=symbol.upper(),
        hours=hours,
        platform=platform,
    )

    return SentimentResponse(
        symbol=sentiment.symbol,
        platform=sentiment.platform.value if sentiment.platform else None,
        total_posts=sentiment.total_posts,
        bullish_count=sentiment.bullish_count,
        bearish_count=sentiment.bearish_count,
        neutral_count=sentiment.neutral_count,
        sentiment_score=sentiment.sentiment_score,
        sentiment_label=sentiment.sentiment_label.value,
        confidence=sentiment.confidence,
        mentions_24h=sentiment.mentions_24h,
        key_themes=sentiment.key_themes,
    )


@router.get("/posts/{symbol}", response_model=List[PostResponse])
async def get_posts(
    symbol: str,
    platform: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Get stored posts for a symbol.
    """
    service = get_service()

    platform_enum = SocialPlatform(platform) if platform else None
    posts = service.get_posts(
        symbol=symbol.upper(),
        platform=platform_enum,
        hours=hours,
        limit=limit,
    )

    return [post_to_response(p) for p in posts]


@router.get("/posts", response_model=List[PostResponse])
async def get_recent_posts(
    platform: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Get recent posts across all symbols.
    """
    service = get_service()

    platform_enum = SocialPlatform(platform) if platform else None
    posts = service.get_posts(
        platform=platform_enum,
        hours=hours,
        limit=limit,
    )

    return [post_to_response(p) for p in posts]


@router.get("/search", response_model=List[PostResponse])
async def search_posts(
    q: str = Query(..., min_length=1, description="Search query"),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Search stored posts by content.
    """
    service = get_service()
    posts = service.search_stored(query=q, hours=hours, limit=limit)
    return [post_to_response(p) for p in posts]


@router.get("/trending", response_model=List[TrendingResponse])
async def get_trending(
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Get cached trending stocks.

    Returns the most recent trending snapshot.
    """
    service = get_service()
    trending = service.get_trending(limit=limit)

    return [
        TrendingResponse(
            rank=t.rank,
            symbol=t.symbol,
            name=t.name,
            mentions_count=t.mentions_count,
            sentiment_score=t.sentiment_score,
            sentiment_label=t.sentiment_label.value,
            platforms=[p.value for p in t.platforms],
        )
        for t in trending
    ]


# ==================== Stats Endpoints ====================

@router.get("/platforms")
async def get_platforms():
    """
    Get list of available platforms.
    """
    service = get_service()
    return {
        "available": service.get_available_platforms(),
        "all": [p.value for p in SocialPlatform],
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get service statistics.
    """
    service = get_service()
    stats = service.get_stats()

    return StatsResponse(
        total_posts=stats.get("total_posts", 0),
        unique_symbols=stats.get("unique_symbols", 0),
        sentiment_snapshots=stats.get("sentiment_snapshots", 0),
        posts_by_platform=stats.get("posts_by_platform", {}),
        available_platforms=stats.get("available_platforms", []),
    )


# ==================== Cleanup ====================

@router.post("/cleanup")
async def cleanup_old_data(days: int = Query(default=7, ge=1, le=30)):
    """
    Clean up old social data.
    """
    service = get_service()
    result = service.cleanup(days=days)
    return {
        "success": True,
        **result,
    }
