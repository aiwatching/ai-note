"""
Social Media Data Store

SQLite-based persistence for social media posts and sentiment data.
Allows Stock Agent to query collected data without re-fetching.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from contextlib import contextmanager

from .models import (
    SocialPlatform,
    SocialPost,
    PostType,
    SocialSentiment,
    SentimentLabel,
    TrendingStock,
)


logger = logging.getLogger(__name__)


class SocialStore:
    """
    SQLite store for social media data.

    Tables:
    - social_posts: Individual posts/tweets/comments
    - social_sentiments: Aggregated sentiment snapshots
    - trending_stocks: Trending stock snapshots
    """

    def __init__(self, db_path: str = "data/social.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # Posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_posts (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    platform_id TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    url TEXT,
                    symbols TEXT,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    sentiment_score REAL DEFAULT 0,
                    sentiment_label TEXT DEFAULT 'neutral',
                    subreddit TEXT,
                    hashtags TEXT,
                    posted_at TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    UNIQUE(platform, platform_id)
                )
            """)

            # Sentiments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_sentiments (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    platform TEXT,
                    total_posts INTEGER DEFAULT 0,
                    bullish_count INTEGER DEFAULT 0,
                    bearish_count INTEGER DEFAULT 0,
                    neutral_count INTEGER DEFAULT 0,
                    sentiment_score REAL DEFAULT 0,
                    sentiment_label TEXT DEFAULT 'neutral',
                    confidence REAL DEFAULT 0,
                    mentions_1h INTEGER DEFAULT 0,
                    mentions_24h INTEGER DEFAULT 0,
                    mentions_7d INTEGER DEFAULT 0,
                    mention_change_pct REAL DEFAULT 0,
                    total_engagement INTEGER DEFAULT 0,
                    avg_engagement REAL DEFAULT 0,
                    key_themes TEXT,
                    period_start TEXT,
                    period_end TEXT,
                    computed_at TEXT NOT NULL
                )
            """)

            # Trending table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trending_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rank INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    mentions_count INTEGER DEFAULT 0,
                    mentions_change_pct REAL DEFAULT 0,
                    sentiment_score REAL DEFAULT 0,
                    sentiment_label TEXT DEFAULT 'neutral',
                    platforms TEXT,
                    top_subreddits TEXT,
                    computed_at TEXT NOT NULL
                )
            """)

            # Indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_symbol
                ON social_posts(symbols)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_platform_time
                ON social_posts(platform, posted_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiments_symbol
                ON social_sentiments(symbol, computed_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trending_time
                ON trending_stocks(computed_at DESC)
            """)

            conn.commit()
            logger.info("Social store initialized")

    # ==================== Posts ====================

    def save_post(self, post: SocialPost) -> bool:
        """Save a single post"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO social_posts (
                        id, platform, platform_id, post_type, title, content,
                        author, url, symbols, upvotes, downvotes, comments_count,
                        shares, sentiment_score, sentiment_label, subreddit,
                        hashtags, posted_at, collected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post.id,
                    post.platform.value,
                    post.platform_id,
                    post.post_type.value,
                    post.title,
                    post.content,
                    post.author,
                    post.url,
                    ",".join(post.symbols),
                    post.upvotes,
                    post.downvotes,
                    post.comments_count,
                    post.shares,
                    post.sentiment_score,
                    post.sentiment_label.value,
                    post.subreddit,
                    ",".join(post.hashtags),
                    post.posted_at.isoformat(),
                    post.collected_at.isoformat(),
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save post: {e}")
                return False

    def save_posts(self, posts: List[SocialPost]) -> int:
        """Save multiple posts, return count saved"""
        saved = 0
        for post in posts:
            if self.save_post(post):
                saved += 1
        return saved

    def _row_to_post(self, row: sqlite3.Row) -> SocialPost:
        """Convert database row to SocialPost"""
        return SocialPost(
            id=row["id"],
            platform=SocialPlatform(row["platform"]),
            platform_id=row["platform_id"],
            post_type=PostType(row["post_type"]),
            title=row["title"],
            content=row["content"],
            author=row["author"],
            url=row["url"],
            symbols=row["symbols"].split(",") if row["symbols"] else [],
            upvotes=row["upvotes"],
            downvotes=row["downvotes"],
            comments_count=row["comments_count"],
            shares=row["shares"],
            sentiment_score=row["sentiment_score"],
            sentiment_label=SentimentLabel(row["sentiment_label"]),
            subreddit=row["subreddit"],
            hashtags=row["hashtags"].split(",") if row["hashtags"] else [],
            posted_at=datetime.fromisoformat(row["posted_at"]),
            collected_at=datetime.fromisoformat(row["collected_at"]),
        )

    def get_posts_for_symbol(
        self,
        symbol: str,
        platform: Optional[SocialPlatform] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[SocialPost]:
        """Get posts mentioning a symbol"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = """
                SELECT * FROM social_posts
                WHERE symbols LIKE ? AND posted_at > ?
            """
            params = [f"%{symbol}%", cutoff]

            if platform:
                query += " AND platform = ?"
                params.append(platform.value)

            query += " ORDER BY posted_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_recent_posts(
        self,
        platform: Optional[SocialPlatform] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[SocialPost]:
        """Get recent posts across all symbols"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = "SELECT * FROM social_posts WHERE posted_at > ?"
            params = [cutoff]

            if platform:
                query += " AND platform = ?"
                params.append(platform.value)

            query += " ORDER BY posted_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_post(row) for row in cursor.fetchall()]

    def search_posts(
        self,
        query: str,
        hours: int = 24,
        limit: int = 50,
    ) -> List[SocialPost]:
        """Search posts by content"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT * FROM social_posts
                WHERE (content LIKE ? OR title LIKE ?) AND posted_at > ?
                ORDER BY upvotes DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", cutoff, limit))

            return [self._row_to_post(row) for row in cursor.fetchall()]

    def get_post_count(
        self,
        symbol: Optional[str] = None,
        platform: Optional[SocialPlatform] = None,
        hours: int = 24,
    ) -> int:
        """Get post count"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = "SELECT COUNT(*) FROM social_posts WHERE posted_at > ?"
            params = [cutoff]

            if symbol:
                query += " AND symbols LIKE ?"
                params.append(f"%{symbol}%")

            if platform:
                query += " AND platform = ?"
                params.append(platform.value)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

    # ==================== Sentiments ====================

    def save_sentiment(self, sentiment: SocialSentiment) -> bool:
        """Save sentiment snapshot"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO social_sentiments (
                        id, symbol, platform, total_posts, bullish_count,
                        bearish_count, neutral_count, sentiment_score,
                        sentiment_label, confidence, mentions_1h, mentions_24h,
                        mentions_7d, mention_change_pct, total_engagement,
                        avg_engagement, key_themes, period_start, period_end,
                        computed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sentiment.id,
                    sentiment.symbol,
                    sentiment.platform.value if sentiment.platform else None,
                    sentiment.total_posts,
                    sentiment.bullish_count,
                    sentiment.bearish_count,
                    sentiment.neutral_count,
                    sentiment.sentiment_score,
                    sentiment.sentiment_label.value,
                    sentiment.confidence,
                    sentiment.mentions_1h,
                    sentiment.mentions_24h,
                    sentiment.mentions_7d,
                    sentiment.mention_change_pct,
                    sentiment.total_engagement,
                    sentiment.avg_engagement,
                    ",".join(sentiment.key_themes),
                    sentiment.period_start.isoformat(),
                    sentiment.period_end.isoformat(),
                    sentiment.computed_at.isoformat(),
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save sentiment: {e}")
                return False

    def get_latest_sentiment(
        self,
        symbol: str,
        platform: Optional[SocialPlatform] = None,
    ) -> Optional[SocialSentiment]:
        """Get latest sentiment for a symbol"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM social_sentiments
                WHERE symbol = ?
            """
            params = [symbol]

            if platform:
                query += " AND platform = ?"
                params.append(platform.value)
            else:
                query += " AND platform IS NULL"

            query += " ORDER BY computed_at DESC LIMIT 1"

            cursor.execute(query, params)
            row = cursor.fetchone()

            if not row:
                return None

            return SocialSentiment(
                id=row["id"],
                symbol=row["symbol"],
                platform=SocialPlatform(row["platform"]) if row["platform"] else None,
                total_posts=row["total_posts"],
                bullish_count=row["bullish_count"],
                bearish_count=row["bearish_count"],
                neutral_count=row["neutral_count"],
                sentiment_score=row["sentiment_score"],
                sentiment_label=SentimentLabel(row["sentiment_label"]),
                confidence=row["confidence"],
                mentions_1h=row["mentions_1h"],
                mentions_24h=row["mentions_24h"],
                mentions_7d=row["mentions_7d"],
                mention_change_pct=row["mention_change_pct"],
                total_engagement=row["total_engagement"],
                avg_engagement=row["avg_engagement"],
                key_themes=row["key_themes"].split(",") if row["key_themes"] else [],
                period_start=datetime.fromisoformat(row["period_start"]),
                period_end=datetime.fromisoformat(row["period_end"]),
                computed_at=datetime.fromisoformat(row["computed_at"]),
            )

    # ==================== Trending ====================

    def save_trending(self, trending: List[TrendingStock]) -> int:
        """Save trending stocks snapshot"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            saved = 0

            for stock in trending:
                try:
                    cursor.execute("""
                        INSERT INTO trending_stocks (
                            rank, symbol, name, mentions_count, mentions_change_pct,
                            sentiment_score, sentiment_label, platforms,
                            top_subreddits, computed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        stock.rank,
                        stock.symbol,
                        stock.name,
                        stock.mentions_count,
                        stock.mentions_change_pct,
                        stock.sentiment_score,
                        stock.sentiment_label.value,
                        ",".join([p.value for p in stock.platforms]),
                        ",".join(stock.top_subreddits),
                        stock.computed_at.isoformat(),
                    ))
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save trending stock: {e}")

            conn.commit()
            return saved

    def get_latest_trending(self, limit: int = 20) -> List[TrendingStock]:
        """Get latest trending stocks"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # Get the most recent snapshot time
            cursor.execute("""
                SELECT computed_at FROM trending_stocks
                ORDER BY computed_at DESC LIMIT 1
            """)
            row = cursor.fetchone()

            if not row:
                return []

            latest_time = row["computed_at"]

            cursor.execute("""
                SELECT * FROM trending_stocks
                WHERE computed_at = ?
                ORDER BY rank
                LIMIT ?
            """, (latest_time, limit))

            trending = []
            for row in cursor.fetchall():
                trending.append(TrendingStock(
                    rank=row["rank"],
                    symbol=row["symbol"],
                    name=row["name"],
                    mentions_count=row["mentions_count"],
                    mentions_change_pct=row["mentions_change_pct"],
                    sentiment_score=row["sentiment_score"],
                    sentiment_label=SentimentLabel(row["sentiment_label"]),
                    platforms=[SocialPlatform(p) for p in row["platforms"].split(",") if p],
                    top_subreddits=row["top_subreddits"].split(",") if row["top_subreddits"] else [],
                    computed_at=datetime.fromisoformat(row["computed_at"]),
                ))

            return trending

    # ==================== Cleanup ====================

    def cleanup_old_posts(self, days: int = 7) -> int:
        """Delete posts older than specified days"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("DELETE FROM social_posts WHERE posted_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted} old posts")
            return deleted

    def cleanup_old_sentiments(self, days: int = 30) -> int:
        """Delete old sentiment snapshots"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("DELETE FROM social_sentiments WHERE computed_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()

            return deleted

    def get_stats(self) -> dict:
        """Get store statistics"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM social_posts")
            stats["total_posts"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT symbols) FROM social_posts WHERE symbols != ''")
            stats["unique_symbols"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM social_sentiments")
            stats["sentiment_snapshots"] = cursor.fetchone()[0]

            cursor.execute("""
                SELECT platform, COUNT(*) as count
                FROM social_posts
                GROUP BY platform
            """)
            stats["posts_by_platform"] = {row["platform"]: row["count"] for row in cursor.fetchall()}

            return stats
