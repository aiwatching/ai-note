"""
Social Media Collection Action

Scheduled task action for collecting social media data.
"""
import logging
from typing import Dict, Any, List

from .base import BaseAction, ActionResult, ActionRegistry
from ..models import Task


logger = logging.getLogger(__name__)


@ActionRegistry.register("social_collect")
class SocialCollectAction(BaseAction):
    """
    Action to collect social media data for symbols.

    Config:
    - symbols: List of stock symbols to collect
    - platforms: Optional list of platforms (default: all available)
    - limit_per_symbol: Max posts per symbol (default: 50)
    - max_age_hours: Max age of posts to collect (default: 24)
    - compute_sentiment: Whether to compute sentiment after collection (default: True)
    """

    name = "social_collect"
    description = "Collect social media data for stock symbols"

    def __init__(self, social_service=None, **kwargs):
        super().__init__(**kwargs)
        self.social_service = social_service

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate action config"""
        errors = []

        if not config.get("symbols"):
            errors.append("symbols is required")

        symbols = config.get("symbols", [])
        if not isinstance(symbols, list):
            errors.append("symbols must be a list")

        return errors

    async def execute(self, task: Task) -> ActionResult:
        """Execute social media collection"""
        config = task.action_config
        symbols = config.get("symbols", [])
        platforms = config.get("platforms")
        limit_per_symbol = config.get("limit_per_symbol", 50)
        compute_sentiment = config.get("compute_sentiment", True)

        if not self.social_service:
            from ...social import get_social_service
            self.social_service = get_social_service()

        try:
            # Convert platform strings to enums
            platform_enums = None
            if platforms:
                from ...social import SocialPlatform
                platform_enums = [SocialPlatform(p) for p in platforms]

            # Collect data
            results = await self.social_service.collect_for_symbols(
                symbols=symbols,
                platforms=platform_enums,
                limit_per_symbol=limit_per_symbol,
            )

            # Calculate totals
            total_collected = 0
            by_symbol = {}
            for symbol, platform_counts in results.items():
                symbol_total = sum(platform_counts.values())
                by_symbol[symbol] = symbol_total
                total_collected += symbol_total

            # Compute sentiment if requested
            sentiments = {}
            if compute_sentiment:
                for symbol in symbols:
                    sentiment = self.social_service.get_sentiment(symbol)
                    sentiments[symbol] = {
                        "score": sentiment.sentiment_score,
                        "label": sentiment.sentiment_label.value,
                        "total_posts": sentiment.total_posts,
                        "bullish": sentiment.bullish_count,
                        "bearish": sentiment.bearish_count,
                    }

            result_data = {
                "total_collected": total_collected,
                "by_symbol": by_symbol,
                "platforms_used": list(results.get(symbols[0], {}).keys()) if symbols else [],
                "sentiments": sentiments,
            }

            # Send notification if configured
            if config.get("notify_channels") and self.notification_service:
                # Build notification message
                lines = [f"📊 社交媒体数据采集完成"]
                lines.append(f"采集帖子: {total_collected} 条")
                for symbol, count in by_symbol.items():
                    sentiment_info = sentiments.get(symbol, {})
                    label = sentiment_info.get("label", "neutral")
                    emoji = "🐂" if label == "bullish" else "🐻" if label == "bearish" else "➖"
                    lines.append(f"  {symbol}: {count} 条 {emoji}")

                from ...channels import Notification
                await self.notification_service.notify(Notification(
                    title="社交媒体采集完成",
                    message="\n".join(lines),
                    channels=config["notify_channels"],
                ))

            return ActionResult(
                success=True,
                message=f"Collected {total_collected} posts for {len(symbols)} symbols",
                data=result_data,
            )

        except Exception as e:
            logger.error(f"Social collection failed: {e}")
            return ActionResult(
                success=False,
                message=str(e),
                data={"error": str(e)},
            )


@ActionRegistry.register("social_trending")
class SocialTrendingAction(BaseAction):
    """
    Action to collect trending stocks from social media.

    Config:
    - platforms: Optional list of platforms
    - limit: Max trending stocks (default: 20)
    - notify_channels: Channels to send notifications
    """

    name = "social_trending"
    description = "Collect trending stocks from social media"

    def __init__(self, social_service=None, **kwargs):
        super().__init__(**kwargs)
        self.social_service = social_service

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """No required config"""
        return []

    async def execute(self, task: Task) -> ActionResult:
        """Execute trending collection"""
        config = task.action_config
        limit = config.get("limit", 20)
        platforms = config.get("platforms")

        if not self.social_service:
            from ...social import get_social_service
            self.social_service = get_social_service()

        try:
            platform_enums = None
            if platforms:
                from ...social import SocialPlatform
                platform_enums = [SocialPlatform(p) for p in platforms]

            trending = await self.social_service.collect_trending(
                platforms=platform_enums,
                limit=limit,
            )

            result_data = {
                "trending_count": len(trending),
                "trending": [
                    {
                        "rank": t.rank,
                        "symbol": t.symbol,
                        "name": t.name,
                        "mentions": t.mentions_count,
                        "sentiment": t.sentiment_label.value,
                    }
                    for t in trending
                ],
            }

            # Send notification
            if config.get("notify_channels") and self.notification_service:
                lines = ["🔥 社交媒体热门股票"]
                for t in trending[:10]:
                    emoji = "🐂" if t.sentiment_label.value == "bullish" else "🐻" if t.sentiment_label.value == "bearish" else "➖"
                    lines.append(f"  {t.rank}. {t.symbol} - {t.mentions_count} 提及 {emoji}")

                from ...channels import Notification
                await self.notification_service.notify(Notification(
                    title="热门股票更新",
                    message="\n".join(lines),
                    channels=config["notify_channels"],
                ))

            return ActionResult(
                success=True,
                message=f"Found {len(trending)} trending stocks",
                data=result_data,
            )

        except Exception as e:
            logger.error(f"Trending collection failed: {e}")
            return ActionResult(
                success=False,
                message=str(e),
                data={"error": str(e)},
            )
