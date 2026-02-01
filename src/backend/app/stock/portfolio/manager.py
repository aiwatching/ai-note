"""
Portfolio Manager

Tracks portfolio holdings, calculates performance, and manages positions.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from ..strategies.base import Trade


@dataclass
class Holding:
    """A portfolio holding"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    cost_basis: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    weight: float = 0.0  # Portfolio weight
    sector: str = ""

    def update_price(self, price: float, total_value: float = 0):
        """Update with current price"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.cost_basis = self.quantity * self.avg_cost
        self.unrealized_pnl = self.market_value - self.cost_basis
        self.unrealized_pnl_pct = (
            (self.unrealized_pnl / self.cost_basis * 100)
            if self.cost_basis != 0 else 0
        )
        if total_value > 0:
            self.weight = self.market_value / total_value


@dataclass
class PortfolioSummary:
    """Portfolio performance summary"""
    total_value: float
    cash: float
    invested_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    day_pnl: float
    day_pnl_pct: float
    num_positions: int
    top_gainers: List[Dict] = field(default_factory=list)
    top_losers: List[Dict] = field(default_factory=list)
    sector_allocation: Dict[str, float] = field(default_factory=dict)


class Portfolio:
    """
    Portfolio representation.

    Tracks holdings, cash, and calculates performance.
    """

    def __init__(
        self,
        name: str = "Main Portfolio",
        initial_cash: float = 100000.0,
    ):
        self.name = name
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.holdings: Dict[str, Holding] = {}
        self.trades: List[Trade] = []
        self.created_at = datetime.now()
        self.last_updated = datetime.now()

    def add_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        sector: str = "",
    ) -> Trade:
        """Add or increase a position"""
        commission = price * quantity * 0.001  # 0.1% commission estimate

        if symbol in self.holdings:
            holding = self.holdings[symbol]
            total_quantity = holding.quantity + quantity
            total_cost = (holding.quantity * holding.avg_cost) + (quantity * price)
            holding.avg_cost = total_cost / total_quantity
            holding.quantity = total_quantity
        else:
            self.holdings[symbol] = Holding(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price,
                sector=sector,
            )

        self.cash -= (quantity * price + commission)

        trade = Trade(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            commission=commission,
        )
        self.trades.append(trade)
        self.last_updated = datetime.now()

        return trade

    def reduce_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
    ) -> Optional[Trade]:
        """Reduce or close a position"""
        if symbol not in self.holdings:
            return None

        holding = self.holdings[symbol]
        if quantity > holding.quantity:
            quantity = holding.quantity

        commission = price * quantity * 0.001

        # Calculate realized P&L
        realized_pnl = (price - holding.avg_cost) * quantity

        holding.quantity -= quantity
        if holding.quantity <= 0:
            del self.holdings[symbol]

        self.cash += (quantity * price - commission)

        trade = Trade(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            commission=commission,
        )
        self.trades.append(trade)
        self.last_updated = datetime.now()

        return trade

    def update_prices(self, prices: Dict[str, float]):
        """Update all holdings with current prices"""
        total_value = self.get_total_value(prices)

        for symbol, holding in self.holdings.items():
            if symbol in prices:
                holding.update_price(prices[symbol], total_value)

        self.last_updated = datetime.now()

    def get_total_value(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Get total portfolio value"""
        prices = prices or {}
        invested = sum(
            holding.quantity * prices.get(symbol, holding.current_price)
            for symbol, holding in self.holdings.items()
        )
        return self.cash + invested

    def get_invested_value(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Get value of invested positions only"""
        prices = prices or {}
        return sum(
            holding.quantity * prices.get(symbol, holding.current_price)
            for symbol, holding in self.holdings.items()
        )

    def get_cost_basis(self) -> float:
        """Get total cost basis"""
        return sum(
            holding.quantity * holding.avg_cost
            for holding in self.holdings.values()
        )

    def get_summary(self, prices: Optional[Dict[str, float]] = None) -> PortfolioSummary:
        """Get portfolio summary"""
        prices = prices or {}
        self.update_prices(prices)

        total_value = self.get_total_value(prices)
        invested_value = self.get_invested_value(prices)
        total_cost = self.get_cost_basis()
        total_pnl = invested_value - total_cost

        # Sort by P&L for gainers/losers
        sorted_holdings = sorted(
            self.holdings.values(),
            key=lambda h: h.unrealized_pnl_pct,
            reverse=True,
        )

        top_gainers = [
            {"symbol": h.symbol, "pnl_pct": round(h.unrealized_pnl_pct, 2)}
            for h in sorted_holdings[:3]
            if h.unrealized_pnl_pct > 0
        ]

        top_losers = [
            {"symbol": h.symbol, "pnl_pct": round(h.unrealized_pnl_pct, 2)}
            for h in reversed(sorted_holdings[-3:])
            if h.unrealized_pnl_pct < 0
        ]

        # Sector allocation
        sector_allocation = {}
        for holding in self.holdings.values():
            sector = holding.sector or "Unknown"
            sector_allocation[sector] = (
                sector_allocation.get(sector, 0) + holding.weight
            )

        return PortfolioSummary(
            total_value=round(total_value, 2),
            cash=round(self.cash, 2),
            invested_value=round(invested_value, 2),
            total_cost=round(total_cost, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0,
            day_pnl=0,  # Would need previous day's value
            day_pnl_pct=0,
            num_positions=len(self.holdings),
            top_gainers=top_gainers,
            top_losers=top_losers,
            sector_allocation=sector_allocation,
        )

    def get_weights(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Get portfolio weights"""
        prices = prices or {}
        total = self.get_total_value(prices)
        if total == 0:
            return {}

        weights = {}
        for symbol, holding in self.holdings.items():
            price = prices.get(symbol, holding.current_price)
            weights[symbol] = (holding.quantity * price) / total

        weights["_cash"] = self.cash / total
        return weights

    def to_dict(self) -> Dict:
        """Serialize portfolio to dict"""
        return {
            "name": self.name,
            "cash": self.cash,
            "initial_cash": self.initial_cash,
            "holdings": {
                symbol: {
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "avg_cost": h.avg_cost,
                    "sector": h.sector,
                }
                for symbol, h in self.holdings.items()
            },
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Portfolio":
        """Deserialize portfolio from dict"""
        portfolio = cls(
            name=data.get("name", "Portfolio"),
            initial_cash=data.get("initial_cash", 100000),
        )
        portfolio.cash = data.get("cash", portfolio.initial_cash)

        for symbol, h_data in data.get("holdings", {}).items():
            portfolio.holdings[symbol] = Holding(
                symbol=h_data["symbol"],
                quantity=h_data["quantity"],
                avg_cost=h_data["avg_cost"],
                sector=h_data.get("sector", ""),
            )

        return portfolio


class PortfolioManager:
    """
    High-level portfolio management.

    Features:
    - Multiple portfolio support
    - Performance tracking
    - Rebalancing
    - Trade execution simulation
    """

    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.default_portfolio = "main"

    def create_portfolio(
        self,
        name: str,
        initial_cash: float = 100000.0,
    ) -> Portfolio:
        """Create a new portfolio"""
        portfolio = Portfolio(name=name, initial_cash=initial_cash)
        self.portfolios[name] = portfolio
        return portfolio

    def get_portfolio(self, name: Optional[str] = None) -> Optional[Portfolio]:
        """Get portfolio by name"""
        name = name or self.default_portfolio
        return self.portfolios.get(name)

    def get_or_create_portfolio(
        self,
        name: str,
        initial_cash: float = 100000.0,
    ) -> Portfolio:
        """Get existing portfolio or create new one"""
        if name not in self.portfolios:
            return self.create_portfolio(name, initial_cash)
        return self.portfolios[name]

    def calculate_returns(
        self,
        portfolio: Portfolio,
        price_history: Dict[str, pd.DataFrame],
        period: str = "1Y",
    ) -> pd.Series:
        """Calculate portfolio returns over time"""
        # Get date range
        periods = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "YTD": None}
        days = periods.get(period, 252)

        # Simulate portfolio value over time
        # This is simplified - real implementation would track actual trades
        if not portfolio.holdings:
            return pd.Series()

        # Find common date range
        min_len = min(
            len(df) for df in price_history.values()
            if df is not None and len(df) > 0
        )
        if days:
            min_len = min(min_len, days)

        dates = None
        for df in price_history.values():
            if df is not None and len(df) >= min_len:
                dates = df.index[-min_len:]
                break

        if dates is None:
            return pd.Series()

        # Calculate portfolio value for each date
        values = []
        for i in range(len(dates)):
            total = portfolio.cash
            for symbol, holding in portfolio.holdings.items():
                if symbol in price_history:
                    df = price_history[symbol]
                    if len(df) > i:
                        total += holding.quantity * df["Close"].iloc[-min_len + i]
            values.append(total)

        portfolio_values = pd.Series(values, index=dates)
        returns = portfolio_values.pct_change().dropna()

        return returns

    def get_performance_metrics(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, float]:
        """Calculate performance metrics from returns"""
        if len(returns) == 0:
            return {}

        trading_days = 252

        # Total return
        total_return = (1 + returns).prod() - 1

        # Annualized return
        n_days = len(returns)
        annualized_return = (1 + total_return) ** (trading_days / n_days) - 1

        # Volatility
        volatility = returns.std() * np.sqrt(trading_days)

        # Sharpe ratio
        excess_return = annualized_return - risk_free_rate
        sharpe = excess_return / volatility if volatility > 0 else 0

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        # Sortino ratio (downside deviation)
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() * np.sqrt(trading_days)
        sortino = excess_return / downside_std if downside_std > 0 else 0

        # Win rate
        win_rate = (returns > 0).sum() / len(returns)

        return {
            "total_return": round(total_return * 100, 2),
            "annualized_return": round(annualized_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "max_drawdown": round(max_drawdown * 100, 2),
            "win_rate": round(win_rate * 100, 2),
        }

    def suggest_rebalance(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, float],
        prices: Dict[str, float],
        threshold: float = 0.05,
    ) -> List[Dict]:
        """Suggest trades to rebalance portfolio"""
        current_weights = portfolio.get_weights(prices)
        total_value = portfolio.get_total_value(prices)

        suggestions = []

        for symbol, target in target_weights.items():
            current = current_weights.get(symbol, 0)
            diff = target - current

            if abs(diff) >= threshold:
                target_value = total_value * target
                current_value = total_value * current
                value_diff = target_value - current_value

                if symbol in prices:
                    shares = int(value_diff / prices[symbol])
                    if shares != 0:
                        suggestions.append({
                            "symbol": symbol,
                            "action": "buy" if shares > 0 else "sell",
                            "shares": abs(shares),
                            "current_weight": round(current * 100, 2),
                            "target_weight": round(target * 100, 2),
                            "value": round(abs(value_diff), 2),
                        })

        return suggestions
