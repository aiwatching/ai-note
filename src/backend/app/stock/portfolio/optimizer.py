"""
Portfolio Optimization Module

Implements various portfolio optimization methods:
- Mean-Variance (Markowitz)
- Minimum Variance
- Maximum Sharpe Ratio
- Risk Parity
- Black-Litterman (simplified)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


class OptimizationMethod(str, Enum):
    """Available optimization methods"""
    MAX_SHARPE = "max_sharpe"
    MIN_VARIANCE = "min_variance"
    RISK_PARITY = "risk_parity"
    MAX_RETURN = "max_return"
    EQUAL_WEIGHT = "equal_weight"


@dataclass
class OptimizationResult:
    """Portfolio optimization result"""
    method: str
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    metrics: Dict[str, float] = field(default_factory=dict)


class PortfolioOptimizer:
    """
    Portfolio Optimizer

    Implements modern portfolio theory optimization methods.

    Usage:
        optimizer = PortfolioOptimizer()
        result = optimizer.optimize(
            returns_data,
            method=OptimizationMethod.MAX_SHARPE
        )
    """

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def calculate_returns_stats(
        self,
        price_data: Dict[str, pd.DataFrame],
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate expected returns and covariance matrix"""
        returns_dict = {}

        for symbol, df in price_data.items():
            if df is not None and "Close" in df.columns and len(df) > 20:
                returns_dict[symbol] = df["Close"].pct_change().dropna()

        if len(returns_dict) < 2:
            return pd.Series(), pd.DataFrame()

        # Align all returns
        returns_df = pd.DataFrame(returns_dict)
        returns_df = returns_df.dropna()

        if len(returns_df) < 20:
            return pd.Series(), pd.DataFrame()

        # Expected returns (annualized)
        expected_returns = returns_df.mean() * 252

        # Covariance matrix (annualized)
        cov_matrix = returns_df.cov() * 252

        return expected_returns, cov_matrix

    def portfolio_stats(
        self,
        weights: np.ndarray,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
    ) -> Tuple[float, float, float]:
        """Calculate portfolio statistics"""
        port_return = np.dot(weights, expected_returns)
        port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_volatility

        return port_return, port_volatility, sharpe

    def optimize_max_sharpe(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        constraints: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Find weights that maximize Sharpe ratio.

        Uses numerical optimization with scipy if available,
        otherwise uses a grid search approximation.
        """
        n_assets = len(expected_returns)
        constraints = constraints or {}

        min_weight = constraints.get("min_weight", 0.0)
        max_weight = constraints.get("max_weight", 1.0)

        try:
            from scipy.optimize import minimize

            def neg_sharpe(weights):
                ret, vol, sharpe = self.portfolio_stats(
                    weights, expected_returns, cov_matrix
                )
                return -sharpe

            # Constraints: weights sum to 1
            constraints_scipy = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1}
            ]

            # Bounds
            bounds = [(min_weight, max_weight) for _ in range(n_assets)]

            # Initial guess: equal weight
            init_weights = np.array([1/n_assets] * n_assets)

            result = minimize(
                neg_sharpe,
                init_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints_scipy,
            )

            if result.success:
                return result.x, -result.fun

        except ImportError:
            pass

        # Fallback: Monte Carlo simulation
        best_sharpe = -np.inf
        best_weights = np.array([1/n_assets] * n_assets)

        for _ in range(10000):
            weights = np.random.random(n_assets)
            weights = weights / weights.sum()

            # Apply constraints
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()

            ret, vol, sharpe = self.portfolio_stats(
                weights, expected_returns, cov_matrix
            )

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = weights

        return best_weights, best_sharpe

    def optimize_min_variance(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        constraints: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, float]:
        """Find minimum variance portfolio"""
        n_assets = len(expected_returns)
        constraints = constraints or {}

        min_weight = constraints.get("min_weight", 0.0)
        max_weight = constraints.get("max_weight", 1.0)

        try:
            from scipy.optimize import minimize

            def portfolio_variance(weights):
                return np.dot(weights.T, np.dot(cov_matrix, weights))

            constraints_scipy = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1}
            ]

            bounds = [(min_weight, max_weight) for _ in range(n_assets)]
            init_weights = np.array([1/n_assets] * n_assets)

            result = minimize(
                portfolio_variance,
                init_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints_scipy,
            )

            if result.success:
                variance = result.fun
                return result.x, np.sqrt(variance)

        except ImportError:
            pass

        # Fallback: inverse variance weighting
        variances = np.diag(cov_matrix)
        inv_var = 1 / variances
        weights = inv_var / inv_var.sum()

        weights = np.clip(weights, min_weight, max_weight)
        weights = weights / weights.sum()

        vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        return weights, vol

    def optimize_risk_parity(
        self,
        cov_matrix: pd.DataFrame,
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Risk parity optimization.

        Each asset contributes equally to portfolio risk.
        """
        n_assets = len(cov_matrix)

        try:
            from scipy.optimize import minimize

            def risk_parity_objective(weights):
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

                # Marginal risk contribution
                marginal_contrib = np.dot(cov_matrix, weights)
                risk_contrib = weights * marginal_contrib / port_vol

                # Target: equal risk contribution
                target_contrib = port_vol / n_assets
                return np.sum((risk_contrib - target_contrib) ** 2)

            constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
            bounds = [(0.01, 1.0) for _ in range(n_assets)]
            init_weights = np.array([1/n_assets] * n_assets)

            result = minimize(
                risk_parity_objective,
                init_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                weights = result.x
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

                # Calculate risk contributions
                marginal = np.dot(cov_matrix, weights)
                risk_contrib = weights * marginal / port_vol
                contrib_dict = {
                    cov_matrix.columns[i]: float(risk_contrib[i])
                    for i in range(n_assets)
                }

                return weights, contrib_dict

        except ImportError:
            pass

        # Fallback: inverse volatility
        vols = np.sqrt(np.diag(cov_matrix))
        weights = (1 / vols) / (1 / vols).sum()
        contrib_dict = {
            cov_matrix.columns[i]: float(weights[i])
            for i in range(n_assets)
        }

        return weights, contrib_dict

    def efficient_frontier(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        n_points: int = 50,
    ) -> List[Dict]:
        """Calculate points on the efficient frontier"""
        min_ret = expected_returns.min()
        max_ret = expected_returns.max()
        target_returns = np.linspace(min_ret, max_ret, n_points)

        frontier = []
        n_assets = len(expected_returns)

        try:
            from scipy.optimize import minimize

            for target in target_returns:
                def portfolio_variance(weights):
                    return np.dot(weights.T, np.dot(cov_matrix, weights))

                constraints = [
                    {"type": "eq", "fun": lambda w: np.sum(w) - 1},
                    {"type": "eq", "fun": lambda w: np.dot(w, expected_returns) - target},
                ]
                bounds = [(0, 1) for _ in range(n_assets)]
                init_weights = np.array([1/n_assets] * n_assets)

                result = minimize(
                    portfolio_variance,
                    init_weights,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                )

                if result.success:
                    vol = np.sqrt(result.fun)
                    sharpe = (target - self.risk_free_rate) / vol
                    frontier.append({
                        "return": round(target * 100, 2),
                        "volatility": round(vol * 100, 2),
                        "sharpe": round(sharpe, 3),
                    })

        except ImportError:
            # Simplified frontier using random portfolios
            for _ in range(n_points * 10):
                weights = np.random.random(n_assets)
                weights = weights / weights.sum()

                ret, vol, sharpe = self.portfolio_stats(
                    weights, expected_returns, cov_matrix
                )

                frontier.append({
                    "return": round(ret * 100, 2),
                    "volatility": round(vol * 100, 2),
                    "sharpe": round(sharpe, 3),
                })

            # Sort and deduplicate
            frontier = sorted(frontier, key=lambda x: x["volatility"])
            frontier = frontier[:n_points]

        return frontier

    def optimize(
        self,
        price_data: Dict[str, pd.DataFrame],
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        constraints: Optional[Dict] = None,
    ) -> OptimizationResult:
        """
        Optimize portfolio weights.

        Args:
            price_data: Dict of symbol -> OHLCV DataFrame
            method: Optimization method to use
            constraints: Optional constraints (min_weight, max_weight)

        Returns:
            OptimizationResult with optimal weights and metrics
        """
        expected_returns, cov_matrix = self.calculate_returns_stats(price_data)

        if len(expected_returns) < 2:
            symbols = list(price_data.keys())
            equal_weight = 1.0 / len(symbols) if symbols else 0
            return OptimizationResult(
                method=method.value,
                weights={s: equal_weight for s in symbols},
                expected_return=0,
                expected_volatility=0,
                sharpe_ratio=0,
            )

        symbols = list(expected_returns.index)
        n_assets = len(symbols)

        if method == OptimizationMethod.MAX_SHARPE:
            weights, sharpe = self.optimize_max_sharpe(
                expected_returns, cov_matrix, constraints
            )
            ret, vol, _ = self.portfolio_stats(weights, expected_returns, cov_matrix)

        elif method == OptimizationMethod.MIN_VARIANCE:
            weights, vol = self.optimize_min_variance(
                expected_returns, cov_matrix, constraints
            )
            ret, _, sharpe = self.portfolio_stats(weights, expected_returns, cov_matrix)

        elif method == OptimizationMethod.RISK_PARITY:
            weights, risk_contrib = self.optimize_risk_parity(cov_matrix)
            ret, vol, sharpe = self.portfolio_stats(weights, expected_returns, cov_matrix)

        elif method == OptimizationMethod.MAX_RETURN:
            # Simple: all weight in highest expected return asset
            max_idx = expected_returns.argmax()
            weights = np.zeros(n_assets)
            weights[max_idx] = 1.0
            ret, vol, sharpe = self.portfolio_stats(weights, expected_returns, cov_matrix)

        else:  # EQUAL_WEIGHT
            weights = np.array([1/n_assets] * n_assets)
            ret, vol, sharpe = self.portfolio_stats(weights, expected_returns, cov_matrix)

        # Convert to dict
        weights_dict = {symbols[i]: round(float(weights[i]), 4) for i in range(n_assets)}

        return OptimizationResult(
            method=method.value,
            weights=weights_dict,
            expected_return=round(float(ret) * 100, 2),
            expected_volatility=round(float(vol) * 100, 2),
            sharpe_ratio=round(float(sharpe), 3),
            metrics={
                "n_assets": n_assets,
                "risk_free_rate": self.risk_free_rate,
            },
        )
