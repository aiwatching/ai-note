"""
Social Media Sentiment Analyzer

Analyzes social media posts to extract sentiment and key themes.
Uses both rule-based and optional LLM-based analysis.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter

from .models import (
    SocialPost,
    SocialSentiment,
    SentimentLabel,
)
from .store import SocialStore


logger = logging.getLogger(__name__)


# Sentiment keywords
BULLISH_KEYWORDS = {
    "buy", "long", "calls", "moon", "rocket", "bullish", "pump", "squeeze",
    "undervalued", "breakout", "upside", "growth", "strong", "hold",
    "accumulate", "diamond hands", "tendies", "gains", "profit", "rally",
    "all time high", "ath", "to the moon", "yolo", "🚀", "💎", "🐂",
    "beat", "crush", "surge", "soar", "boom", "explode",
}

BEARISH_KEYWORDS = {
    "sell", "short", "puts", "dump", "crash", "bearish", "overvalued",
    "downside", "weak", "avoid", "exit", "loss", "drop", "tank",
    "paper hands", "bag holder", "rip", "dead", "disaster", "bubble",
    "all time low", "atl", "going down", "🐻", "📉", "💀",
    "miss", "fail", "plunge", "sink", "collapse",
}

# Amplifiers
STRONG_AMPLIFIERS = {"very", "extremely", "absolutely", "definitely", "100%", "huge", "massive"}
WEAK_AMPLIFIERS = {"slightly", "maybe", "possibly", "might", "somewhat", "little"}


class SocialAnalyzer:
    """
    Analyzes social media data for sentiment and trends.

    Features:
    - Rule-based sentiment scoring
    - Engagement-weighted aggregation
    - Key theme extraction
    - Optional LLM-enhanced analysis
    """

    def __init__(self, store: SocialStore, llm_service=None):
        self.store = store
        self.llm = llm_service

    def analyze_post(self, post: SocialPost) -> SocialPost:
        """
        Analyze a single post for sentiment.

        Args:
            post: The post to analyze

        Returns:
            Post with sentiment_score and sentiment_label set
        """
        text = f"{post.title or ''} {post.content}".lower()

        # Count sentiment keywords
        bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text)
        bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text)

        # Check for amplifiers
        has_strong = any(amp in text for amp in STRONG_AMPLIFIERS)
        has_weak = any(amp in text for amp in WEAK_AMPLIFIERS)

        # Calculate base score
        total = bullish_count + bearish_count
        if total == 0:
            score = 0.0
        else:
            score = (bullish_count - bearish_count) / total

        # Apply amplifier modifiers
        if has_strong:
            score *= 1.3
        elif has_weak:
            score *= 0.7

        # Clamp to [-1, 1]
        score = max(-1.0, min(1.0, score))

        # Determine label
        if score > 0.2:
            label = SentimentLabel.BULLISH
        elif score < -0.2:
            label = SentimentLabel.BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        post.sentiment_score = score
        post.sentiment_label = label

        return post

    def analyze_posts(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Analyze multiple posts"""
        return [self.analyze_post(post) for post in posts]

    def compute_sentiment(
        self,
        symbol: str,
        hours: int = 24,
        platform: Optional[str] = None,
    ) -> SocialSentiment:
        """
        Compute aggregated sentiment for a symbol.

        Args:
            symbol: Stock symbol
            hours: Time period to analyze
            platform: Optional platform filter

        Returns:
            SocialSentiment with aggregated metrics
        """
        from .models import SocialPlatform

        # Get posts
        platform_enum = SocialPlatform(platform) if platform else None
        posts = self.store.get_posts_for_symbol(
            symbol, platform=platform_enum, hours=hours, limit=500
        )

        if not posts:
            return SocialSentiment(
                symbol=symbol,
                platform=platform_enum,
                total_posts=0,
                sentiment_label=SentimentLabel.NEUTRAL,
            )

        # Analyze posts if not already analyzed
        for post in posts:
            if post.sentiment_score == 0:
                self.analyze_post(post)

        # Count by sentiment
        bullish_count = sum(1 for p in posts if p.sentiment_label == SentimentLabel.BULLISH)
        bearish_count = sum(1 for p in posts if p.sentiment_label == SentimentLabel.BEARISH)
        neutral_count = sum(1 for p in posts if p.sentiment_label == SentimentLabel.NEUTRAL)

        # Engagement-weighted sentiment score
        total_engagement = sum(p.engagement_score for p in posts)
        if total_engagement > 0:
            weighted_score = sum(
                p.sentiment_score * p.engagement_score for p in posts
            ) / total_engagement
        else:
            weighted_score = sum(p.sentiment_score for p in posts) / len(posts)

        # Determine overall label
        if weighted_score > 0.15:
            label = SentimentLabel.BULLISH
        elif weighted_score < -0.15:
            label = SentimentLabel.BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        # Calculate confidence based on agreement
        if len(posts) < 5:
            confidence = 0.3
        elif len(posts) < 20:
            confidence = 0.5
        else:
            # Higher agreement = higher confidence
            max_count = max(bullish_count, bearish_count, neutral_count)
            confidence = min(0.9, max_count / len(posts) + 0.3)

        # Get mention counts for different periods
        now = datetime.now()
        mentions_1h = sum(1 for p in posts if p.posted_at > now - timedelta(hours=1))
        mentions_24h = len(posts) if hours >= 24 else sum(
            1 for p in posts if p.posted_at > now - timedelta(hours=24)
        )

        # Extract key themes
        key_themes = self._extract_themes(posts)

        # Get top posts by engagement
        top_posts = sorted(posts, key=lambda p: p.engagement_score, reverse=True)[:5]

        sentiment = SocialSentiment(
            symbol=symbol,
            platform=platform_enum,
            total_posts=len(posts),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            sentiment_score=weighted_score,
            sentiment_label=label,
            confidence=confidence,
            mentions_1h=mentions_1h,
            mentions_24h=mentions_24h,
            mentions_7d=0,  # Would need more data
            mention_change_pct=0.0,  # Would need historical comparison
            total_engagement=total_engagement,
            avg_engagement=total_engagement / len(posts) if posts else 0,
            top_posts=top_posts,
            key_themes=key_themes,
            period_start=min(p.posted_at for p in posts),
            period_end=max(p.posted_at for p in posts),
        )

        # Save to store
        self.store.save_sentiment(sentiment)

        return sentiment

    def _extract_themes(self, posts: List[SocialPost], top_n: int = 5) -> List[str]:
        """Extract common themes/keywords from posts"""
        # Common words to exclude
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "and",
            "but", "or", "if", "because", "as", "until", "while", "of",
            "at", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above",
            "below", "to", "from", "up", "down", "in", "out", "on",
            "off", "over", "under", "again", "then", "once", "here",
            "there", "when", "where", "why", "how", "stock", "stocks",
            "share", "shares", "market", "trading", "trade", "price",
            "buy", "sell", "hold", "money", "get", "got", "going", "go",
            "like", "think", "know", "see", "look", "want", "need",
            "make", "take", "come", "use", "find", "give", "tell",
            "work", "feel", "try", "leave", "call", "keep", "let",
            "begin", "seem", "help", "show", "hear", "play", "run",
            "move", "live", "believe", "bring", "happen", "write",
            "provide", "sit", "stand", "lose", "pay", "meet", "include",
            "continue", "set", "learn", "change", "lead", "understand",
            "watch", "follow", "stop", "create", "speak", "read",
            "allow", "add", "spend", "grow", "open", "walk", "win",
            "offer", "remember", "love", "consider", "appear", "wait",
            "serve", "die", "send", "expect", "build", "stay", "fall",
            "cut", "reach", "kill", "remain", "yall", "cant", "dont",
            "im", "ive", "thats", "its", "hes", "shes", "theyre",
        }

        # Extract words from all posts
        words = []
        for post in posts:
            text = f"{post.title or ''} {post.content}".lower()
            # Extract words (alphanumeric, 3+ chars)
            post_words = re.findall(r'\b[a-z]{3,}\b', text)
            words.extend(post_words)

        # Filter and count
        filtered = [w for w in words if w not in stopwords]
        counts = Counter(filtered)

        # Return top themes
        return [word for word, _ in counts.most_common(top_n)]

    async def analyze_with_llm(
        self,
        symbol: str,
        posts: List[SocialPost],
    ) -> Dict:
        """
        Use LLM to analyze posts for deeper insights.

        Args:
            symbol: Stock symbol
            posts: Posts to analyze

        Returns:
            Dict with analysis results
        """
        if not self.llm:
            logger.warning("LLM service not configured for deep analysis")
            return {}

        # Prepare context
        post_summaries = []
        for post in posts[:20]:  # Limit to top 20
            summary = f"- [{post.platform.value}] {post.upvotes}👍: "
            if post.title:
                summary += f"{post.title[:100]} | "
            summary += post.content[:200]
            post_summaries.append(summary)

        prompt = f"""Analyze the following social media posts about {symbol} stock:

{chr(10).join(post_summaries)}

Provide analysis in JSON format:
{{
    "overall_sentiment": "bullish/bearish/neutral",
    "confidence": 0.0-1.0,
    "key_arguments_bullish": ["argument1", "argument2"],
    "key_arguments_bearish": ["argument1", "argument2"],
    "catalysts_mentioned": ["catalyst1", "catalyst2"],
    "risks_mentioned": ["risk1", "risk2"],
    "notable_insights": "Brief summary of notable insights",
    "recommendation": "Brief investment consideration"
}}
"""

        try:
            response = await self.llm.chat(prompt, provider="deepseek")
            # Parse JSON from response
            import json
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        return {}
