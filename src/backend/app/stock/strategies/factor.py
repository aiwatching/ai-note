"""
Factor-Based Trading Strategies

Strategies based on quantitative factors (Value, Quality, Momentum, etc.)
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from .base import Strategy, StrategySignal, StrategyResult, SignalType


class FactorStrategy(Strategy):
    """
    Single Factor Strategy

    Ranks stocks by a single factor and generates signals
    for top/bottom ranked stocks.

    Available Factors:
    - value: Low P/E, P/B, P/S ratios
    - momentum: Recent price performance
    - quality: High ROE, profit margins
    - volatility: Low volatility stocks
    - size: Market capitalization

    Parameters:
        factor: Factor to use (default: "value")
        top_pct: Top percentile to buy (default: 0.2)
        bottom_pct: Bottom percentile to sell (default: 0.2)
    """

    name = "single_factor"
    description = "Ranks stocks by a single factor"

    DEFAULT_PARAMS = {
        "factor": "value",
        "top_pct": 0.2,
        "bottom_pct": 0.2,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    def _calculate_value_score(
        self,
        metrics: Dict[str, Any],
    ) -> Optional[float]:
        """Calculate value factor score (lower P/E, P/B = higher score)"""
        scores = []

        pe = metrics.get("pe_ratio")
        if pe and pe > 0 and pe < 100:
            # Invert: lower P/E = higher score
            scores.append(max(0, 1 - pe / 50))

        pb = metrics.get("pb_ratio")
        if pb and pb > 0 and pb < 20:
            scores.append(max(0, 1 - pb / 10))

        ps = metrics.get("ps_ratio")
        if ps and ps > 0 and ps < 20:
            scores.append(max(0, 1 - ps / 10))

        return sum(scores) / len(scores) if scores else None

    def _calculate_momentum_score(
        self,
        df: pd.DataFrame,
        periods: List[int] = [21, 63, 252],
    ) -> Optional[float]:
        """Calculate momentum factor score"""
        if len(df) < max(periods):
            return None

        close = df["Close"]
        current = close.iloc[-1]

        scores = []
        for period in periods:
            if len(df) >= period:
                past = close.iloc[-period]
                returns = (current - past) / past
                # Normalize to 0-1 range
                scores.append(max(0, min(1, (returns + 0.5) / 1.0)))

        return sum(scores) / len(scores) if scores else None

    def _calculate_quality_score(
        self,
        metrics: Dict[str, Any],
    ) -> Optional[float]:
        """Calculate quality factor score"""
        scores = []

        roe = metrics.get("roe")
        if roe is not None:
            scores.append(max(0, min(1, roe / 0.3)))

        roa = metrics.get("roa")
        if roa is not None:
            scores.append(max(0, min(1, roa / 0.15)))

        margin = metrics.get("profit_margin")
        if margin is not None:
            scores.append(max(0, min(1, margin / 0.25)))

        # Debt consideration (lower is better)
        debt_equity = metrics.get("debt_to_equity")
        if debt_equity is not None and debt_equity >= 0:
            scores.append(max(0, 1 - debt_equity / 3))

        return sum(scores) / len(scores) if scores else None

    def _calculate_volatility_score(
        self,
        df: pd.DataFrame,
        period: int = 60,
    ) -> Optional[float]:
        """Calculate volatility factor score (lower vol = higher score)"""
        if len(df) < period:
            return None

        returns = df["Close"].pct_change().dropna()
        if len(returns) < period:
            return None

        vol = returns.iloc[-period:].std() * np.sqrt(252)

        # Lower volatility = higher score
        return max(0, 1 - vol / 0.6)

    def calculate_factor_score(
        self,
        symbol: str,
        df: Optional[pd.DataFrame],
        metrics: Optional[Dict[str, Any]],
    ) -> Optional[float]:
        """Calculate factor score based on strategy parameter"""
        factor = self.params["factor"]

        if factor == "value":
            return self._calculate_value_score(metrics or {})
        elif factor == "momentum":
            if df is not None and len(df) > 0:
                return self._calculate_momentum_score(df)
        elif factor == "quality":
            return self._calculate_quality_score(metrics or {})
        elif factor == "volatility":
            if df is not None and len(df) > 0:
                return self._calculate_volatility_score(df)

        return None

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
        fundamentals: Optional[Dict[str, Dict]] = None,
    ) -> StrategyResult:
        """Rank stocks by factor and generate signals"""
        fundamentals = fundamentals or {}
        scores = []
        summary = {"analyzed": 0, "scored": 0}

        for symbol in symbols:
            df = data.get(symbol)
            metrics = fundamentals.get(symbol, {})

            summary["analyzed"] += 1

            score = self.calculate_factor_score(symbol, df, metrics)
            if score is not None:
                summary["scored"] += 1
                scores.append((symbol, score, df["Close"].iloc[-1] if df is not None else 0))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        signals = []
        n_stocks = len(scores)
        top_n = int(n_stocks * self.params["top_pct"])
        bottom_n = int(n_stocks * self.params["bottom_pct"])

        # Top ranked = buy signals
        for symbol, score, price in scores[:top_n]:
            signals.append(StrategySignal(
                symbol=symbol,
                signal_type=SignalType.BUY if score > 0.6 else SignalType.HOLD,
                strength=score,
                price=price,
                timestamp=datetime.now(),
                reason=f"Top {self.params['factor']} factor rank ({score:.2f})",
                metadata={
                    "factor": self.params["factor"],
                    "score": round(score, 3),
                    "rank": scores.index((symbol, score, price)) + 1,
                    "total_stocks": n_stocks,
                },
            ))

        # Bottom ranked = sell signals
        for symbol, score, price in scores[-bottom_n:]:
            signals.append(StrategySignal(
                symbol=symbol,
                signal_type=SignalType.SELL if score < 0.4 else SignalType.HOLD,
                strength=1 - score,
                price=price,
                timestamp=datetime.now(),
                reason=f"Bottom {self.params['factor']} factor rank ({score:.2f})",
                metadata={
                    "factor": self.params["factor"],
                    "score": round(score, 3),
                    "rank": scores.index((symbol, score, price)) + 1,
                    "total_stocks": n_stocks,
                },
            ))

        summary["top_picks"] = [s[0] for s in scores[:top_n]]
        summary["bottom_picks"] = [s[0] for s in scores[-bottom_n:]]

        return StrategyResult(
            strategy_name=f"{self.name}_{self.params['factor']}",
            symbols=symbols,
            signals=signals,
            summary=summary,
        )


class MultiFactorStrategy(Strategy):
    """
    Multi-Factor Strategy

    Combines multiple factors with configurable weights:
    - Value (P/E, P/B)
    - Momentum (price performance)
    - Quality (ROE, margins)
    - Volatility (risk)

    Parameters:
        weights: Dict of factor -> weight (default: equal weight)
        top_pct: Top percentile to buy (default: 0.2)
        bottom_pct: Bottom percentile to sell (default: 0.2)
    """

    name = "multi_factor"
    description = "Combines multiple factors for stock selection"

    DEFAULT_PARAMS = {
        "weights": {
            "value": 0.25,
            "momentum": 0.25,
            "quality": 0.25,
            "volatility": 0.25,
        },
        "top_pct": 0.2,
        "bottom_pct": 0.2,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self._factor_strategy = FactorStrategy()

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
        fundamentals: Optional[Dict[str, Dict]] = None,
    ) -> StrategyResult:
        """Calculate multi-factor scores and generate signals"""
        fundamentals = fundamentals or {}
        weights = self.params["weights"]
        total_weight = sum(weights.values())

        composite_scores = []
        factor_details = {}
        summary = {"analyzed": 0, "scored": 0}

        for symbol in symbols:
            df = data.get(symbol)
            metrics = fundamentals.get(symbol, {})

            summary["analyzed"] += 1

            factor_scores = {}
            weighted_score = 0.0
            weight_sum = 0.0

            for factor, weight in weights.items():
                self._factor_strategy.params["factor"] = factor
                score = self._factor_strategy.calculate_factor_score(symbol, df, metrics)

                if score is not None:
                    factor_scores[factor] = score
                    weighted_score += score * weight
                    weight_sum += weight

            if weight_sum > 0:
                summary["scored"] += 1
                final_score = weighted_score / weight_sum
                composite_scores.append((symbol, final_score, factor_scores))
                factor_details[symbol] = factor_scores

        # Sort by composite score
        composite_scores.sort(key=lambda x: x[1], reverse=True)

        signals = []
        n_stocks = len(composite_scores)
        top_n = max(1, int(n_stocks * self.params["top_pct"]))
        bottom_n = max(1, int(n_stocks * self.params["bottom_pct"]))

        # Top ranked = buy signals
        for i, (symbol, score, factor_scores) in enumerate(composite_scores[:top_n]):
            df = data.get(symbol)
            price = df["Close"].iloc[-1] if df is not None and len(df) > 0 else 0

            # Determine signal strength based on score
            if score >= 0.7:
                signal_type = SignalType.STRONG_BUY
            elif score >= 0.5:
                signal_type = SignalType.BUY
            else:
                signal_type = SignalType.HOLD

            signals.append(StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=score,
                price=price,
                timestamp=datetime.now(),
                reason=f"Top multi-factor rank #{i+1} (score: {score:.2f})",
                metadata={
                    "composite_score": round(score, 3),
                    "factor_scores": {k: round(v, 3) for k, v in factor_scores.items()},
                    "rank": i + 1,
                    "total_stocks": n_stocks,
                },
            ))

        # Bottom ranked = sell signals
        for i, (symbol, score, factor_scores) in enumerate(composite_scores[-bottom_n:]):
            df = data.get(symbol)
            price = df["Close"].iloc[-1] if df is not None and len(df) > 0 else 0

            # Determine signal strength
            if score <= 0.3:
                signal_type = SignalType.STRONG_SELL
            elif score <= 0.5:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            signals.append(StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=1 - score,
                price=price,
                timestamp=datetime.now(),
                reason=f"Bottom multi-factor rank (score: {score:.2f})",
                metadata={
                    "composite_score": round(score, 3),
                    "factor_scores": {k: round(v, 3) for k, v in factor_scores.items()},
                    "rank": n_stocks - bottom_n + i + 1,
                    "total_stocks": n_stocks,
                },
            ))

        summary["top_picks"] = [s[0] for s in composite_scores[:top_n]]
        summary["bottom_picks"] = [s[0] for s in composite_scores[-bottom_n:]]
        summary["weights"] = weights

        return StrategyResult(
            strategy_name=self.name,
            symbols=symbols,
            signals=signals,
            summary=summary,
        )
