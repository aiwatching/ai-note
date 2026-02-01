"""
Risk Management Module

Provides risk analysis, position sizing, and risk metrics.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    # Volatility
    daily_volatility: float = 0.0
    annualized_volatility: float = 0.0

    # Value at Risk
    var_95: float = 0.0  # 95% VaR
    var_99: float = 0.0  # 99% VaR
    cvar_95: float = 0.0  # Conditional VaR (Expected Shortfall)

    # Drawdown
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0

    # Beta and correlation
    beta: Optional[float] = None  # vs benchmark
    correlation: Optional[float] = None

    # Concentration
    herfindahl_index: float = 0.0  # Position concentration
    top_3_concentration: float = 0.0

    # Risk ratings
    overall_risk_score: float = 0.0  # 0-100
    risk_level: str = "medium"  # low, medium, high, very_high


class RiskManager:
    """
    Portfolio Risk Manager

    Calculates various risk metrics:
    - Value at Risk (VaR)
    - Volatility
    - Maximum Drawdown
    - Beta and correlation
    - Concentration risk

    Usage:
        rm = RiskManager()
        metrics = rm.calculate_risk_metrics(returns, weights)
    """

    def calculate_portfolio_returns(
        self,
        price_data: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
    ) -> pd.Series:
        """Calculate portfolio returns from asset prices"""
        returns_list = []
        weight_list = []

        for symbol, weight in weights.items():
            if symbol.startswith("_"):  # Skip cash
                continue
            if symbol in price_data and price_data[symbol] is not None:
                df = price_data[symbol]
                if "Close" in df.columns:
                    asset_returns = df["Close"].pct_change().dropna()
                    returns_list.append(asset_returns)
                    weight_list.append(weight)

        if not returns_list:
            return pd.Series()

        # Align all returns to common dates
        combined = pd.concat(returns_list, axis=1)
        combined.columns = range(len(returns_list))
        combined = combined.dropna()

        # Calculate weighted portfolio returns
        weights_arr = np.array(weight_list)
        weights_arr = weights_arr / weights_arr.sum()  # Normalize

        portfolio_returns = combined.dot(weights_arr)
        return portfolio_returns

    def calculate_var(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        method: str = "historical",
    ) -> float:
        """
        Calculate Value at Risk.

        Methods:
        - historical: Based on historical returns distribution
        - parametric: Assumes normal distribution
        """
        if len(returns) == 0:
            return 0.0

        if method == "historical":
            var = returns.quantile(1 - confidence)
        else:  # parametric
            z_score = {0.95: 1.645, 0.99: 2.326}.get(confidence, 1.645)
            var = returns.mean() - z_score * returns.std()

        return abs(var)

    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).

        CVaR is the expected loss given that loss exceeds VaR.
        """
        if len(returns) == 0:
            return 0.0

        var = self.calculate_var(returns, confidence)
        # Get returns worse than VaR
        tail_returns = returns[returns <= -var]

        if len(tail_returns) == 0:
            return var

        return abs(tail_returns.mean())

    def calculate_max_drawdown(self, returns: pd.Series) -> tuple:
        """Calculate maximum drawdown and current drawdown"""
        if len(returns) == 0:
            return 0.0, 0.0

        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max

        max_dd = abs(drawdowns.min())
        current_dd = abs(drawdowns.iloc[-1])

        return max_dd, current_dd

    def calculate_beta(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> tuple:
        """Calculate beta and correlation vs benchmark"""
        if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
            return None, None

        # Align data
        combined = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(combined) < 20:
            return None, None

        port_ret = combined.iloc[:, 0]
        bench_ret = combined.iloc[:, 1]

        # Beta = Cov(Rp, Rb) / Var(Rb)
        covariance = port_ret.cov(bench_ret)
        benchmark_variance = bench_ret.var()

        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        correlation = port_ret.corr(bench_ret)

        return beta, correlation

    def calculate_concentration(self, weights: Dict[str, float]) -> tuple:
        """Calculate position concentration metrics"""
        # Filter out cash
        position_weights = [w for k, w in weights.items() if not k.startswith("_")]

        if not position_weights:
            return 0.0, 0.0

        # Herfindahl-Hirschman Index
        hhi = sum(w ** 2 for w in position_weights)

        # Top 3 concentration
        sorted_weights = sorted(position_weights, reverse=True)
        top_3 = sum(sorted_weights[:3])

        return hhi, top_3

    def calculate_risk_metrics(
        self,
        price_data: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
        benchmark_data: Optional[pd.DataFrame] = None,
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics.

        Args:
            price_data: Dict of symbol -> OHLCV DataFrame
            weights: Portfolio weights
            benchmark_data: Optional benchmark OHLCV data (e.g., SPY)

        Returns:
            RiskMetrics with all calculations
        """
        metrics = RiskMetrics()

        # Calculate portfolio returns
        returns = self.calculate_portfolio_returns(price_data, weights)

        if len(returns) < 20:
            return metrics

        # Volatility
        metrics.daily_volatility = returns.std()
        metrics.annualized_volatility = metrics.daily_volatility * np.sqrt(252)

        # VaR
        metrics.var_95 = self.calculate_var(returns, 0.95)
        metrics.var_99 = self.calculate_var(returns, 0.99)
        metrics.cvar_95 = self.calculate_cvar(returns, 0.95)

        # Drawdown
        metrics.max_drawdown, metrics.current_drawdown = self.calculate_max_drawdown(returns)

        # Beta and correlation (if benchmark provided)
        if benchmark_data is not None and "Close" in benchmark_data.columns:
            bench_returns = benchmark_data["Close"].pct_change().dropna()
            metrics.beta, metrics.correlation = self.calculate_beta(returns, bench_returns)

        # Concentration
        metrics.herfindahl_index, metrics.top_3_concentration = self.calculate_concentration(weights)

        # Calculate overall risk score (0-100, higher = riskier)
        risk_score = 0

        # Volatility component (0-30)
        vol_pct = metrics.annualized_volatility * 100
        if vol_pct > 40:
            risk_score += 30
        elif vol_pct > 25:
            risk_score += 20
        elif vol_pct > 15:
            risk_score += 10

        # VaR component (0-25)
        var_pct = metrics.var_95 * 100
        if var_pct > 5:
            risk_score += 25
        elif var_pct > 3:
            risk_score += 15
        elif var_pct > 2:
            risk_score += 8

        # Drawdown component (0-25)
        dd_pct = metrics.max_drawdown * 100
        if dd_pct > 30:
            risk_score += 25
        elif dd_pct > 20:
            risk_score += 15
        elif dd_pct > 10:
            risk_score += 8

        # Concentration component (0-20)
        if metrics.top_3_concentration > 0.7:
            risk_score += 20
        elif metrics.top_3_concentration > 0.5:
            risk_score += 12
        elif metrics.top_3_concentration > 0.3:
            risk_score += 5

        metrics.overall_risk_score = min(100, risk_score)

        # Risk level
        if metrics.overall_risk_score >= 70:
            metrics.risk_level = "very_high"
        elif metrics.overall_risk_score >= 50:
            metrics.risk_level = "high"
        elif metrics.overall_risk_score >= 30:
            metrics.risk_level = "medium"
        else:
            metrics.risk_level = "low"

        return metrics


class PositionSizer:
    """
    Position Sizing Calculator

    Methods:
    - Fixed fractional (% of portfolio)
    - Kelly Criterion
    - Volatility-based
    - Risk parity
    """

    def fixed_fractional(
        self,
        portfolio_value: float,
        fraction: float = 0.05,
        price: float = 1.0,
    ) -> int:
        """
        Fixed fractional position sizing.

        Allocates a fixed percentage of portfolio to each position.
        """
        position_value = portfolio_value * fraction
        shares = int(position_value / price)
        return max(0, shares)

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25,  # Use fraction of Kelly for safety
    ) -> float:
        """
        Kelly Criterion for optimal position sizing.

        Args:
            win_rate: Probability of winning trade
            avg_win: Average profit on winning trades
            avg_loss: Average loss on losing trades (positive number)
            fraction: Fraction of full Kelly to use (0.25 = quarter Kelly)

        Returns:
            Fraction of portfolio to allocate
        """
        if avg_loss == 0 or avg_win == 0:
            return 0.0

        # Kelly formula: f* = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate

        kelly = (b * p - q) / b

        # Apply fraction and bound
        position_size = max(0, min(1, kelly * fraction))
        return position_size

    def volatility_based(
        self,
        portfolio_value: float,
        price: float,
        volatility: float,  # Daily volatility
        target_risk: float = 0.02,  # 2% portfolio risk
    ) -> int:
        """
        Volatility-based position sizing.

        Sizes position to target a specific portfolio risk contribution.

        Args:
            portfolio_value: Total portfolio value
            price: Current asset price
            volatility: Asset's daily volatility (decimal)
            target_risk: Target risk as fraction of portfolio

        Returns:
            Number of shares
        """
        if volatility == 0 or price == 0:
            return 0

        # Position value = (Portfolio Value × Target Risk) / Volatility
        position_value = (portfolio_value * target_risk) / volatility
        shares = int(position_value / price)
        return max(0, shares)

    def risk_parity_weights(
        self,
        volatilities: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calculate risk parity weights.

        Each position contributes equally to portfolio risk.

        Args:
            volatilities: Dict of symbol -> annualized volatility

        Returns:
            Dict of symbol -> weight
        """
        if not volatilities:
            return {}

        # Inverse volatility weighting
        inv_vols = {s: 1/v for s, v in volatilities.items() if v > 0}

        if not inv_vols:
            return {}

        total_inv_vol = sum(inv_vols.values())
        weights = {s: iv / total_inv_vol for s, iv in inv_vols.items()}

        return weights

    def calculate_position_size(
        self,
        method: str,
        portfolio_value: float,
        price: float,
        **kwargs,
    ) -> int:
        """
        Calculate position size using specified method.

        Args:
            method: 'fixed', 'kelly', 'volatility'
            portfolio_value: Total portfolio value
            price: Asset price
            **kwargs: Method-specific parameters

        Returns:
            Number of shares to buy
        """
        if method == "fixed":
            fraction = kwargs.get("fraction", 0.05)
            return self.fixed_fractional(portfolio_value, fraction, price)

        elif method == "kelly":
            win_rate = kwargs.get("win_rate", 0.5)
            avg_win = kwargs.get("avg_win", 1)
            avg_loss = kwargs.get("avg_loss", 1)
            kelly_fraction = kwargs.get("kelly_fraction", 0.25)

            position_fraction = self.kelly_criterion(
                win_rate, avg_win, avg_loss, kelly_fraction
            )
            return int((portfolio_value * position_fraction) / price)

        elif method == "volatility":
            volatility = kwargs.get("volatility", 0.02)
            target_risk = kwargs.get("target_risk", 0.02)
            return self.volatility_based(
                portfolio_value, price, volatility, target_risk
            )

        else:
            # Default to 5% fixed
            return self.fixed_fractional(portfolio_value, 0.05, price)
