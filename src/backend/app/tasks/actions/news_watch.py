"""
News Watch Action

Monitors news for specific keywords or symbols.
"""
from typing import Dict, Any, List, Set
import logging
from datetime import datetime, timedelta

from ..models import Task, ActionType, NewsWatchConfig
from .base import BaseAction, ActionResult, ActionRegistry


logger = logging.getLogger(__name__)


@ActionRegistry.register(ActionType.NEWS_WATCH)
class NewsWatchAction(BaseAction):
    """News monitoring action"""

    description = "Monitor news for keywords and symbols"

    # Track seen news to avoid duplicates
    _seen_news: Set[str] = set()
    _max_seen = 1000  # Max entries to keep in seen set

    async def execute(self, task: Task) -> ActionResult:
        """Execute news watching"""
        if not self.stock_service:
            return ActionResult(
                success=False,
                message="Stock service not available",
            )

        config = NewsWatchConfig(**task.action_config)

        if not config.keywords and not config.symbols:
            return ActionResult(
                success=False,
                message="At least one keyword or symbol is required",
            )

        try:
            all_news = []
            matched_news = []

            # Fetch news for each symbol
            for symbol in config.symbols:
                try:
                    news_items = await self.stock_service.get_news(symbol, limit=20)
                    all_news.extend(news_items)
                except Exception as e:
                    logger.warning(f"Could not get news for {symbol}: {e}")

            # Filter by keywords if specified
            for news in all_news:
                # Skip if already seen
                news_key = f"{news.title}_{news.source}"
                if news_key in self._seen_news:
                    continue

                # Check keywords
                text_to_search = f"{news.title} {news.summary or ''}".lower()
                keyword_match = False

                if config.keywords:
                    for keyword in config.keywords:
                        if keyword.lower() in text_to_search:
                            keyword_match = True
                            break
                else:
                    keyword_match = True  # No keywords = match all

                if keyword_match:
                    # Check sentiment filter if specified
                    if config.sentiment_filter:
                        # Simple sentiment detection based on keywords
                        bullish_words = ["up", "gain", "surge", "rally", "rise", "bullish", "positive", "growth"]
                        bearish_words = ["down", "drop", "fall", "decline", "bearish", "negative", "loss", "crash"]

                        bullish_count = sum(1 for w in bullish_words if w in text_to_search)
                        bearish_count = sum(1 for w in bearish_words if w in text_to_search)

                        if config.sentiment_filter == "bullish" and bullish_count <= bearish_count:
                            continue
                        elif config.sentiment_filter == "bearish" and bearish_count <= bullish_count:
                            continue

                    matched_news.append({
                        "title": news.title,
                        "summary": news.summary,
                        "source": news.source,
                        "published": news.published.isoformat() if news.published else None,
                        "url": news.url,
                    })

                    # Mark as seen
                    self._seen_news.add(news_key)

            # Clean up seen set if too large
            if len(self._seen_news) > self._max_seen:
                # Keep only the most recent half
                self._seen_news = set(list(self._seen_news)[-self._max_seen // 2:])

            # Build summary
            new_count = len(matched_news)
            symbols_str = ", ".join(config.symbols) if config.symbols else "N/A"
            keywords_str = ", ".join(config.keywords) if config.keywords else "N/A"

            if new_count > 0:
                summary = f"Found {new_count} new news items\n"
                summary += f"Symbols: {symbols_str}\n"
                if config.keywords:
                    summary += f"Keywords: {keywords_str}\n"
                summary += "\n"
                for i, news in enumerate(matched_news[:5], 1):
                    summary += f"{i}. {news['title']}\n"
                if new_count > 5:
                    summary += f"... and {new_count - 5} more"
            else:
                summary = f"No new news matching criteria\nSymbols: {symbols_str}, Keywords: {keywords_str}"

            result = ActionResult(
                success=True,
                data={
                    "symbols": config.symbols,
                    "keywords": config.keywords,
                    "news_count": new_count,
                    "news": matched_news[:10],  # Limit to 10 in result
                },
                message=summary,
                should_notify=new_count > 0,
                notification_title=f"News Alert: {new_count} new items",
                notification_message=summary,
            )

            # Send notification if there are new matching news
            if new_count > 0 and config.notify_channels:
                await self.send_notification(task, result, config.notify_channels)

            return result

        except Exception as e:
            logger.error(f"News watch error: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to watch news: {str(e)}",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate news watch configuration"""
        errors = []

        keywords = config.get("keywords", [])
        symbols = config.get("symbols", [])

        if not keywords and not symbols:
            errors.append("at least one keyword or symbol is required")

        sentiment_filter = config.get("sentiment_filter")
        if sentiment_filter and sentiment_filter not in ["bullish", "bearish"]:
            errors.append(f"invalid sentiment_filter: {sentiment_filter}")

        return errors
