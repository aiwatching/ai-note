"""
Stock Price Alert Action

Monitors stock prices and triggers alerts when conditions are met.
"""
from typing import Dict, Any, List
import logging

from ..models import Task, ActionType, StockAlertConfig
from .base import BaseAction, ActionResult, ActionRegistry


logger = logging.getLogger(__name__)


@ActionRegistry.register(ActionType.STOCK_ALERT)
class StockAlertAction(BaseAction):
    """Stock price alert action"""

    description = "Monitor stock price and alert when conditions are met"

    async def execute(self, task: Task) -> ActionResult:
        """Execute price alert check"""
        if not self.stock_service:
            return ActionResult(
                success=False,
                message="Stock service not available",
            )

        config = StockAlertConfig(**task.action_config)

        try:
            # Get current quote
            quote = await self.stock_service.get_quote(config.symbol)
            current_price = quote.price
            change_pct = quote.change_percent

            # Check condition
            triggered = False
            alert_message = ""

            if config.condition == "above" and config.target_price:
                if current_price >= config.target_price:
                    triggered = True
                    alert_message = f"{config.symbol} price ${current_price:.2f} is above target ${config.target_price:.2f}"

            elif config.condition == "below" and config.target_price:
                if current_price <= config.target_price:
                    triggered = True
                    alert_message = f"{config.symbol} price ${current_price:.2f} is below target ${config.target_price:.2f}"

            elif config.condition == "change_pct_above" and config.target_change_pct:
                if change_pct >= config.target_change_pct:
                    triggered = True
                    alert_message = f"{config.symbol} up {change_pct:.2f}% (target: {config.target_change_pct:.2f}%)"

            elif config.condition == "change_pct_below" and config.target_change_pct:
                if change_pct <= config.target_change_pct:
                    triggered = True
                    alert_message = f"{config.symbol} down {change_pct:.2f}% (target: {config.target_change_pct:.2f}%)"

            result = ActionResult(
                success=True,
                data={
                    "symbol": config.symbol,
                    "current_price": current_price,
                    "change_percent": change_pct,
                    "condition": config.condition,
                    "triggered": triggered,
                },
                message=alert_message if triggered else f"{config.symbol}: ${current_price:.2f} ({change_pct:+.2f}%) - condition not met",
                should_notify=triggered,
                notification_title=f"Price Alert: {config.symbol}",
                notification_message=alert_message,
                notification_priority="high" if triggered else "normal",
            )

            # Send notification if triggered
            if triggered:
                await self.send_notification(task, result, config.notify_channels)

            return result

        except Exception as e:
            logger.error(f"Stock alert error for {config.symbol}: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to check {config.symbol}: {str(e)}",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate stock alert configuration"""
        errors = []

        if not config.get("symbol"):
            errors.append("symbol is required")

        condition = config.get("condition")
        if not condition:
            errors.append("condition is required")
        elif condition not in ["above", "below", "change_pct_above", "change_pct_below"]:
            errors.append(f"invalid condition: {condition}")

        # Check target values based on condition
        if condition in ["above", "below"]:
            if not config.get("target_price"):
                errors.append("target_price is required for above/below conditions")
        elif condition in ["change_pct_above", "change_pct_below"]:
            if config.get("target_change_pct") is None:
                errors.append("target_change_pct is required for change percentage conditions")

        return errors
