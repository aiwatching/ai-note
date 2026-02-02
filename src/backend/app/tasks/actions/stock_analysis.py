"""
Stock Analysis Action

Performs scheduled stock analysis (technical, fundamental, sentiment).
"""
from typing import Dict, Any, List
import logging

from ..models import Task, ActionType, StockAnalysisConfig
from .base import BaseAction, ActionResult, ActionRegistry


logger = logging.getLogger(__name__)


@ActionRegistry.register(ActionType.STOCK_ANALYSIS)
class StockAnalysisAction(BaseAction):
    """Scheduled stock analysis action"""

    description = "Perform comprehensive stock analysis on schedule"

    async def execute(self, task: Task) -> ActionResult:
        """Execute stock analysis"""
        if not self.stock_service:
            return ActionResult(
                success=False,
                message="Stock service not available",
            )

        config = StockAnalysisConfig(**task.action_config)

        try:
            results = {
                "symbol": config.symbol,
                "analyses": {},
            }
            summary_parts = []

            # Run requested analysis types
            if "technical" in config.analysis_types:
                tech = await self.stock_service.analyze_technical(config.symbol)
                results["analyses"]["technical"] = tech
                if "error" not in tech:
                    trend = tech.get("trend", "neutral")
                    summary_parts.append(f"Technical: {trend}")

            if "fundamental" in config.analysis_types:
                fund = await self.stock_service.analyze_fundamental(config.symbol)
                results["analyses"]["fundamental"] = fund
                if "error" not in fund:
                    rating = fund.get("rating", "hold")
                    score = fund.get("score", 0)
                    summary_parts.append(f"Fundamental: {rating} ({score:.0f})")

            if "sentiment" in config.analysis_types:
                sent = await self.stock_service.analyze_sentiment(config.symbol)
                results["analyses"]["sentiment"] = sent
                if "error" not in sent:
                    sentiment = sent.get("overall_sentiment", "neutral")
                    summary_parts.append(f"Sentiment: {sentiment}")

            # Get current price
            try:
                quote = await self.stock_service.get_quote(config.symbol)
                results["current_price"] = quote.price
                results["change_percent"] = quote.change_percent
            except Exception:
                pass

            # Build summary message
            summary = f"{config.symbol} Analysis:\n" + "\n".join(summary_parts)

            result = ActionResult(
                success=True,
                data=results,
                message=summary,
                should_notify=bool(config.notify_channels),
                notification_title=f"Analysis: {config.symbol}",
                notification_message=summary,
            )

            # Send notification if configured
            if config.notify_channels:
                await self.send_notification(task, result, config.notify_channels)

            # Index to memory if configured
            if config.save_to_memory:
                chunk_ids = await self.index_to_memory(task, result)
                result.data["memory_chunk_ids"] = chunk_ids

            return result

        except Exception as e:
            logger.error(f"Stock analysis error for {config.symbol}: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to analyze {config.symbol}: {str(e)}",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate stock analysis configuration"""
        errors = []

        if not config.get("symbol"):
            errors.append("symbol is required")

        analysis_types = config.get("analysis_types", [])
        valid_types = ["technical", "fundamental", "sentiment"]
        for t in analysis_types:
            if t not in valid_types:
                errors.append(f"invalid analysis_type: {t}")

        return errors
