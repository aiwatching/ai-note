"""
Mean Reversion Trading Strategies

Strategies that bet on prices returning to their mean.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from .base import Strategy, StrategySignal, StrategyResult, SignalType


class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy

    Identifies overbought/oversold conditions expecting
    price to revert to its mean.

    Key Indicators:
    - Bollinger Bands (price deviation from mean)
    - Z-Score (statistical deviation)
    - RSI for confirmation

    Parameters:
        bb_period: Bollinger Bands period (default: 20)
        bb_std: Bollinger Bands std dev (default: 2)
        zscore_period: Z-score calculation period (default: 20)
        zscore_threshold: Z-score threshold for signals (default: 2)
        rsi_period: RSI period (default: 14)
    """

    name = "mean_reversion"
    description = "Trades price reversion to mean using Bollinger Bands and Z-Score"

    DEFAULT_PARAMS = {
        "bb_period": 20,
        "bb_std": 2.0,
        "zscore_period": 20,
        "zscore_threshold": 2.0,
        "rsi_period": 14,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    def _calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        num_std: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        return upper, middle, lower

    def _calculate_zscore(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Z-Score"""
        mean = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        zscore = (prices - mean) / std
        return zscore

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_percent_b(
        self,
        price: float,
        upper: float,
        lower: float,
    ) -> float:
        """Calculate %B (position within Bollinger Bands)"""
        if upper == lower:
            return 0.5
        return (price - lower) / (upper - lower)

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> StrategyResult:
        """Analyze mean reversion opportunities"""
        signals = []
        summary = {
            "analyzed": 0,
            "oversold": 0,
            "overbought": 0,
            "buy_signals": 0,
            "sell_signals": 0,
        }

        for symbol in symbols:
            df = data.get(symbol)
            if df is None or len(df) < self.params["bb_period"] + 5:
                continue

            summary["analyzed"] += 1
            close = df["Close"]
            current_price = close.iloc[-1]

            # Calculate indicators
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
                close,
                self.params["bb_period"],
                self.params["bb_std"],
            )
            zscore = self._calculate_zscore(close, self.params["zscore_period"])
            rsi = self._calculate_rsi(close, self.params["rsi_period"])

            # Get latest values
            current_zscore = zscore.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_upper = bb_upper.iloc[-1]
            current_lower = bb_lower.iloc[-1]
            current_middle = bb_middle.iloc[-1]
            percent_b = self._calculate_percent_b(
                current_price, current_upper, current_lower
            )

            # Scoring
            score = 0.0
            reasons = []

            # Z-Score signals (inverted for mean reversion)
            threshold = self.params["zscore_threshold"]
            if current_zscore <= -threshold:
                score += 0.4
                reasons.append(f"Z-Score oversold ({current_zscore:.2f})")
                summary["oversold"] += 1
            elif current_zscore >= threshold:
                score -= 0.4
                reasons.append(f"Z-Score overbought ({current_zscore:.2f})")
                summary["overbought"] += 1
            elif abs(current_zscore) > threshold * 0.75:
                if current_zscore < 0:
                    score += 0.2
                else:
                    score -= 0.2

            # Bollinger Band position
            if percent_b < 0:
                score += 0.3
                reasons.append(f"Below lower BB")
            elif percent_b > 1:
                score -= 0.3
                reasons.append(f"Above upper BB")
            elif percent_b < 0.2:
                score += 0.15
            elif percent_b > 0.8:
                score -= 0.15

            # RSI confirmation
            if current_rsi < 30:
                score += 0.2
                reasons.append(f"RSI oversold ({current_rsi:.1f})")
            elif current_rsi > 70:
                score -= 0.2
                reasons.append(f"RSI overbought ({current_rsi:.1f})")

            # Check for reversal signs (price moving back toward mean)
            prev_zscore = zscore.iloc[-2]
            if current_zscore < prev_zscore and prev_zscore < -threshold:
                score += 0.1  # Oversold and starting to recover
            elif current_zscore > prev_zscore and prev_zscore > threshold:
                score -= 0.1  # Overbought and starting to decline

            # Clamp score
            score = max(-1, min(1, score))

            # Generate signal
            signal_type = self.get_signal_type(score)

            if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                summary["buy_signals"] += 1
            elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                summary["sell_signals"] += 1

            signals.append(StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=abs(score),
                price=current_price,
                timestamp=datetime.now(),
                reason="; ".join(reasons) if reasons else "Near mean value",
                metadata={
                    "zscore": round(current_zscore, 3),
                    "rsi": round(current_rsi, 2),
                    "percent_b": round(percent_b, 3),
                    "bb_upper": round(current_upper, 2),
                    "bb_middle": round(current_middle, 2),
                    "bb_lower": round(current_lower, 2),
                },
            ))

        return StrategyResult(
            strategy_name=self.name,
            symbols=symbols,
            signals=signals,
            summary=summary,
        )


class PairsTradingStrategy(Strategy):
    """
    Pairs Trading Strategy

    Trades pairs of correlated stocks:
    - Go long the underperformer
    - Go short the outperformer
    - Profit when spread reverts to mean

    Parameters:
        lookback_period: Period for calculating spread (default: 60)
        zscore_entry: Z-score threshold to enter trade (default: 2)
        zscore_exit: Z-score threshold to exit trade (default: 0.5)
        min_correlation: Minimum correlation for valid pair (default: 0.7)
    """

    name = "pairs_trading"
    description = "Trades mean reversion of spread between correlated pairs"

    DEFAULT_PARAMS = {
        "lookback_period": 60,
        "zscore_entry": 2.0,
        "zscore_exit": 0.5,
        "min_correlation": 0.7,
    }

    def __init__(
        self,
        pairs: Optional[List[Tuple[str, str]]] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.pairs = pairs or []

    def _calculate_spread_zscore(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        period: int,
    ) -> Tuple[pd.Series, pd.Series, float]:
        """Calculate spread and its z-score between two assets"""
        # Calculate hedge ratio using rolling regression
        ratio = prices_a / prices_b
        spread = prices_a - ratio.mean() * prices_b

        # Z-score of spread
        mean = spread.rolling(period).mean()
        std = spread.rolling(period).std()
        zscore = (spread - mean) / std

        # Correlation
        correlation = prices_a.rolling(period).corr(prices_b).iloc[-1]

        return spread, zscore, correlation

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> StrategyResult:
        """Analyze pairs for trading opportunities"""
        signals = []
        summary = {
            "pairs_analyzed": 0,
            "valid_pairs": 0,
            "long_short_signals": 0,
        }

        # If no pairs specified, generate from symbols
        if not self.pairs and len(symbols) >= 2:
            from itertools import combinations
            self.pairs = list(combinations(symbols[:10], 2))  # Limit combinations

        for symbol_a, symbol_b in self.pairs:
            df_a = data.get(symbol_a)
            df_b = data.get(symbol_b)

            if df_a is None or df_b is None:
                continue
            if len(df_a) < self.params["lookback_period"]:
                continue
            if len(df_b) < self.params["lookback_period"]:
                continue

            summary["pairs_analyzed"] += 1

            # Align data
            prices_a = df_a["Close"]
            prices_b = df_b["Close"]

            # Calculate spread z-score
            spread, zscore, correlation = self._calculate_spread_zscore(
                prices_a, prices_b, self.params["lookback_period"]
            )

            # Check correlation
            if abs(correlation) < self.params["min_correlation"]:
                continue

            summary["valid_pairs"] += 1

            current_zscore = zscore.iloc[-1]
            entry_threshold = self.params["zscore_entry"]

            # Generate signals
            if current_zscore >= entry_threshold:
                # Spread too wide: short A, long B
                summary["long_short_signals"] += 1

                signals.append(StrategySignal(
                    symbol=symbol_a,
                    signal_type=SignalType.SELL,
                    strength=min(abs(current_zscore) / 3, 1.0),
                    price=prices_a.iloc[-1],
                    timestamp=datetime.now(),
                    reason=f"Pairs trade: spread z-score {current_zscore:.2f}, short {symbol_a}",
                    metadata={
                        "pair": symbol_b,
                        "spread_zscore": round(current_zscore, 3),
                        "correlation": round(correlation, 3),
                        "position": "short",
                    },
                ))

                signals.append(StrategySignal(
                    symbol=symbol_b,
                    signal_type=SignalType.BUY,
                    strength=min(abs(current_zscore) / 3, 1.0),
                    price=prices_b.iloc[-1],
                    timestamp=datetime.now(),
                    reason=f"Pairs trade: spread z-score {current_zscore:.2f}, long {symbol_b}",
                    metadata={
                        "pair": symbol_a,
                        "spread_zscore": round(current_zscore, 3),
                        "correlation": round(correlation, 3),
                        "position": "long",
                    },
                ))

            elif current_zscore <= -entry_threshold:
                # Spread too narrow: long A, short B
                summary["long_short_signals"] += 1

                signals.append(StrategySignal(
                    symbol=symbol_a,
                    signal_type=SignalType.BUY,
                    strength=min(abs(current_zscore) / 3, 1.0),
                    price=prices_a.iloc[-1],
                    timestamp=datetime.now(),
                    reason=f"Pairs trade: spread z-score {current_zscore:.2f}, long {symbol_a}",
                    metadata={
                        "pair": symbol_b,
                        "spread_zscore": round(current_zscore, 3),
                        "correlation": round(correlation, 3),
                        "position": "long",
                    },
                ))

                signals.append(StrategySignal(
                    symbol=symbol_b,
                    signal_type=SignalType.SELL,
                    strength=min(abs(current_zscore) / 3, 1.0),
                    price=prices_b.iloc[-1],
                    timestamp=datetime.now(),
                    reason=f"Pairs trade: spread z-score {current_zscore:.2f}, short {symbol_b}",
                    metadata={
                        "pair": symbol_a,
                        "spread_zscore": round(current_zscore, 3),
                        "correlation": round(correlation, 3),
                        "position": "short",
                    },
                ))

        return StrategyResult(
            strategy_name=self.name,
            symbols=symbols,
            signals=signals,
            summary=summary,
        )
