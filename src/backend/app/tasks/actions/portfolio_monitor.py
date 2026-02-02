"""
Portfolio Monitor Action

Monitors portfolio performance and alerts on significant changes.
"""
from typing import Dict, Any, List
import logging

from ..models import Task, ActionType, PortfolioMonitorConfig
from .base import BaseAction, ActionResult, ActionRegistry


logger = logging.getLogger(__name__)


@ActionRegistry.register(ActionType.PORTFOLIO_MONITOR)
class PortfolioMonitorAction(BaseAction):
    """Portfolio monitoring action"""

    description = "Monitor portfolio performance and alert on changes"

    # Store last known values for change detection
    _last_values: Dict[str, float] = {}

    async def execute(self, task: Task) -> ActionResult:
        """Execute portfolio monitoring"""
        if not self.stock_service:
            return ActionResult(
                success=False,
                message="Stock service not available",
            )

        config = PortfolioMonitorConfig(**task.action_config)

        try:
            # Get portfolio
            portfolio = self.stock_service.get_portfolio(config.portfolio_name)

            if not portfolio.holdings:
                return ActionResult(
                    success=True,
                    data={"portfolio_name": config.portfolio_name, "holdings_count": 0},
                    message=f"Portfolio '{config.portfolio_name}' has no holdings",
                )

            # Get current prices for all holdings
            prices = {}
            for symbol in portfolio.holdings:
                try:
                    quote = await self.stock_service.get_quote(symbol)
                    prices[symbol] = quote.price
                except Exception as e:
                    logger.warning(f"Could not get price for {symbol}: {e}")

            # Calculate portfolio value
            summary = portfolio.get_summary(prices)
            current_value = summary.total_value

            # Check for significant change
            cache_key = f"portfolio_{config.portfolio_name}"
            last_value = self._last_values.get(cache_key)

            triggered = False
            change_pct = 0.0
            alert_message = ""

            if last_value and last_value > 0:
                change_pct = ((current_value - last_value) / last_value) * 100

                if abs(change_pct) >= config.alert_on_change_pct:
                    triggered = True
                    direction = "up" if change_pct > 0 else "down"
                    alert_message = f"Portfolio '{config.portfolio_name}' is {direction} {abs(change_pct):.2f}% (${current_value:,.2f})"

            # Update cached value
            self._last_values[cache_key] = current_value

            # Build holdings summary
            holdings_summary = []
            for h in portfolio.holdings.values():
                price = prices.get(h.symbol, 0)
                if price:
                    value = h.quantity * price
                    pnl_pct = ((price - h.avg_cost) / h.avg_cost * 100) if h.avg_cost else 0
                    holdings_summary.append({
                        "symbol": h.symbol,
                        "quantity": h.quantity,
                        "price": price,
                        "value": value,
                        "pnl_pct": pnl_pct,
                    })

            result = ActionResult(
                success=True,
                data={
                    "portfolio_name": config.portfolio_name,
                    "total_value": current_value,
                    "cash": summary.cash,
                    "invested_value": summary.invested_value,
                    "total_pnl": summary.total_pnl,
                    "total_pnl_pct": summary.total_pnl_pct,
                    "change_pct": change_pct,
                    "triggered": triggered,
                    "holdings": holdings_summary,
                },
                message=alert_message if triggered else f"Portfolio '{config.portfolio_name}': ${current_value:,.2f} ({change_pct:+.2f}%)",
                should_notify=triggered,
                notification_title=f"Portfolio Alert: {config.portfolio_name}",
                notification_message=alert_message,
                notification_priority="high" if triggered else "normal",
            )

            # Send notification if triggered
            if triggered:
                await self.send_notification(task, result, config.notify_channels)

            return result

        except Exception as e:
            logger.error(f"Portfolio monitor error: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to monitor portfolio: {str(e)}",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate portfolio monitor configuration"""
        errors = []

        alert_pct = config.get("alert_on_change_pct")
        if alert_pct is not None and alert_pct <= 0:
            errors.append("alert_on_change_pct must be positive")

        return errors
