"""
Sentiment Analysis Module

Analyzes market sentiment from news and social media.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class SentimentLevel(str, Enum):
    """Sentiment level"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class NewsSentiment:
    """Sentiment from a news article"""
    title: str
    source: str
    published: datetime
    sentiment_score: float  # -1 to 1
    relevance: float  # 0 to 1
    url: str = ""


@dataclass
class SentimentSummary:
    """Overall sentiment analysis summary"""
    symbol: str
    overall_sentiment: SentimentLevel
    sentiment_score: float  # -1 to 1
    news_count: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_bullish_news: List[NewsSentiment] = field(default_factory=list)
    top_bearish_news: List[NewsSentiment] = field(default_factory=list)
    keywords: Dict[str, int] = field(default_factory=dict)


class SentimentAnalyzer:
    """
    Sentiment Analysis Engine

    Analyzes sentiment from:
    - News articles
    - Headlines
    - Social media (if available)

    Uses keyword-based sentiment analysis.
    Can be enhanced with LLM-based analysis.

    Usage:
        analyzer = SentimentAnalyzer()
        sentiment = analyzer.analyze_news(news_items)
    """

    # Bullish keywords
    BULLISH_KEYWORDS = [
        "surge", "soar", "rally", "gain", "rise", "jump", "climb",
        "beat", "exceed", "outperform", "upgrade", "buy", "bullish",
        "growth", "profit", "strong", "positive", "optimistic",
        "breakthrough", "innovation", "record", "high", "best",
        "success", "win", "expand", "increase", "momentum",
    ]

    # Bearish keywords
    BEARISH_KEYWORDS = [
        "drop", "fall", "decline", "plunge", "crash", "sink", "tumble",
        "miss", "disappoint", "underperform", "downgrade", "sell", "bearish",
        "loss", "weak", "negative", "pessimistic", "concern", "worry",
        "risk", "warning", "low", "worst", "fail", "cut", "decrease",
        "slowdown", "recession", "layoff", "lawsuit",
    ]

    def _calculate_text_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score from text using keyword analysis.

        Returns:
            Score from -1 (bearish) to 1 (bullish)
        """
        text_lower = text.lower()

        bullish_count = sum(1 for word in self.BULLISH_KEYWORDS if word in text_lower)
        bearish_count = sum(1 for word in self.BEARISH_KEYWORDS if word in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        # Score from -1 to 1
        score = (bullish_count - bearish_count) / total
        return score

    def analyze_headline(self, headline: str) -> float:
        """Analyze a single headline"""
        return self._calculate_text_sentiment(headline)

    def analyze_news(
        self,
        news_items: List[Dict],
        symbol: str = "",
    ) -> SentimentSummary:
        """
        Analyze sentiment from news items.

        Args:
            news_items: List of news items with 'title', 'summary', 'source', 'published', 'url'
            symbol: Stock symbol

        Returns:
            SentimentSummary with overall analysis
        """
        sentiments = []
        keyword_counts: Dict[str, int] = {}

        for item in news_items:
            title = item.get("title", "")
            summary = item.get("summary", "")
            combined_text = f"{title} {summary}"

            # Calculate sentiment
            score = self._calculate_text_sentiment(combined_text)

            # Count keywords
            text_lower = combined_text.lower()
            for word in self.BULLISH_KEYWORDS + self.BEARISH_KEYWORDS:
                if word in text_lower:
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1

            # Parse published date
            published = item.get("published")
            if isinstance(published, str):
                try:
                    published = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except Exception:
                    published = datetime.now()
            elif not isinstance(published, datetime):
                published = datetime.now()

            sentiments.append(NewsSentiment(
                title=title,
                source=item.get("source", ""),
                published=published,
                sentiment_score=score,
                relevance=1.0,
                url=item.get("url", ""),
            ))

        if not sentiments:
            return SentimentSummary(
                symbol=symbol,
                overall_sentiment=SentimentLevel.NEUTRAL,
                sentiment_score=0.0,
                news_count=0,
                bullish_count=0,
                bearish_count=0,
                neutral_count=0,
            )

        # Calculate counts
        bullish_count = sum(1 for s in sentiments if s.sentiment_score > 0.2)
        bearish_count = sum(1 for s in sentiments if s.sentiment_score < -0.2)
        neutral_count = len(sentiments) - bullish_count - bearish_count

        # Calculate overall score (weighted by recency)
        total_score = sum(s.sentiment_score for s in sentiments)
        avg_score = total_score / len(sentiments)

        # Determine sentiment level
        if avg_score >= 0.4:
            level = SentimentLevel.VERY_BULLISH
        elif avg_score >= 0.15:
            level = SentimentLevel.BULLISH
        elif avg_score <= -0.4:
            level = SentimentLevel.VERY_BEARISH
        elif avg_score <= -0.15:
            level = SentimentLevel.BEARISH
        else:
            level = SentimentLevel.NEUTRAL

        # Get top bullish and bearish news
        sorted_sentiments = sorted(sentiments, key=lambda x: x.sentiment_score, reverse=True)
        top_bullish = [s for s in sorted_sentiments if s.sentiment_score > 0][:3]
        top_bearish = [s for s in reversed(sorted_sentiments) if s.sentiment_score < 0][:3]

        # Get top keywords
        top_keywords = dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        return SentimentSummary(
            symbol=symbol,
            overall_sentiment=level,
            sentiment_score=round(avg_score, 3),
            news_count=len(sentiments),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            top_bullish_news=top_bullish,
            top_bearish_news=top_bearish,
            keywords=top_keywords,
        )

    async def analyze_with_llm(
        self,
        news_items: List[Dict],
        llm_service: any,  # LLMService
        symbol: str = "",
    ) -> SentimentSummary:
        """
        Analyze sentiment using LLM for more accurate analysis.

        Falls back to keyword analysis if LLM fails.
        """
        # First, do keyword analysis
        base_summary = self.analyze_news(news_items, symbol)

        if not llm_service or not news_items:
            return base_summary

        # Prepare prompt for LLM
        headlines = "\n".join([
            f"- {item.get('title', '')}"
            for item in news_items[:10]
        ])

        prompt = f"""Analyze the sentiment of these news headlines for {symbol}:

{headlines}

Rate the overall sentiment on a scale from -1 (very bearish) to 1 (very bullish).
Reply with only a number between -1 and 1."""

        try:
            response = await llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                provider="deepseek",  # Use cheap model
            )

            # Parse LLM response
            try:
                llm_score = float(response.content.strip())
                llm_score = max(-1, min(1, llm_score))

                # Blend with keyword analysis
                blended_score = (base_summary.sentiment_score + llm_score) / 2
                base_summary.sentiment_score = round(blended_score, 3)

                # Update level based on blended score
                if blended_score >= 0.4:
                    base_summary.overall_sentiment = SentimentLevel.VERY_BULLISH
                elif blended_score >= 0.15:
                    base_summary.overall_sentiment = SentimentLevel.BULLISH
                elif blended_score <= -0.4:
                    base_summary.overall_sentiment = SentimentLevel.VERY_BEARISH
                elif blended_score <= -0.15:
                    base_summary.overall_sentiment = SentimentLevel.BEARISH
                else:
                    base_summary.overall_sentiment = SentimentLevel.NEUTRAL

            except ValueError:
                pass  # Keep keyword-based score

        except Exception:
            pass  # Keep keyword-based analysis

        return base_summary
