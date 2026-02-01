"""
Momentum Trading Strategies

Strategies that follow price trends and momentum.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from .base import Strategy, StrategySignal, StrategyResult, SignalType


class MomentumStrategy(Strategy):
    """
    Classic Momentum Strategy

    Buys stocks with positive price momentum (recent outperformance)
    and sells stocks with negative momentum.

    Key Indicators:
    - Rate of Change (ROC)
    - Relative Strength Index (RSI)
    - Moving Average crossovers

    Parameters:
        lookback_period: Days to measure momentum (default: 20)
        rsi_period: RSI calculation period (default: 14)
        rsi_overbought: RSI overbought threshold (default: 70)
        rsi_oversold: RSI oversold threshold (default: 30)
    """

    name = "momentum"
    description = "Follows price momentum using ROC and RSI"

    DEFAULT_PARAMS = {
        "lookback_period": 20,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "ma_short": 10,
        "ma_long": 50,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_roc(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Rate of Change"""
        return ((prices - prices.shift(period)) / prices.shift(period)) * 100

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> StrategyResult:
        """Analyze momentum for given symbols"""
        signals = []
        summary = {"analyzed": 0, "buy_signals": 0, "sell_signals": 0}

        for symbol in symbols:
            df = data.get(symbol)
            if df is None or len(df) < self.params["ma_long"]:
                continue

            summary["analyzed"] += 1
            close = df["Close"]

            # Calculate indicators
            rsi = self._calculate_rsi(close, self.params["rsi_period"])
            roc = self._calculate_roc(close, self.params["lookback_period"])
            ma_short = close.rolling(self.params["ma_short"]).mean()
            ma_long = close.rolling(self.params["ma_long"]).mean()

            # Get latest values
            current_rsi = rsi.iloc[-1]
            current_roc = roc.iloc[-1]
            current_price = close.iloc[-1]
            ma_short_current = ma_short.iloc[-1]
            ma_long_current = ma_long.iloc[-1]

            # Calculate score
            score = 0.0
            reasons = []

            # RSI signals
            if current_rsi < self.params["rsi_oversold"]:
                score += 0.3
                reasons.append(f"RSI oversold ({current_rsi:.1f})")
            elif current_rsi > self.params["rsi_overbought"]:
                score -= 0.3
                reasons.append(f"RSI overbought ({current_rsi:.1f})")

            # ROC signals
            if current_roc > 5:
                score += 0.3
                reasons.append(f"Strong momentum ({current_roc:.1f}%)")
            elif current_roc > 0:
                score += 0.1
            elif current_roc < -5:
                score -= 0.3
                reasons.append(f"Weak momentum ({current_roc:.1f}%)")
            elif current_roc < 0:
                score -= 0.1

            # Moving average crossover
            if ma_short_current > ma_long_current:
                score += 0.2
                if ma_short.iloc[-2] <= ma_long.iloc[-2]:
                    score += 0.2  # Fresh crossover
                    reasons.append("Bullish MA crossover")
            else:
                score -= 0.2
                if ma_short.iloc[-2] >= ma_long.iloc[-2]:
                    score -= 0.2
                    reasons.append("Bearish MA crossover")

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
                reason="; ".join(reasons) if reasons else "Neutral momentum",
                metadata={
                    "rsi": round(current_rsi, 2),
                    "roc": round(current_roc, 2),
                    "ma_short": round(ma_short_current, 2),
                    "ma_long": round(ma_long_current, 2),
                },
            ))

        return StrategyResult(
            strategy_name=self.name,
            symbols=symbols,
            signals=signals,
            summary=summary,
        )


class TrendFollowingStrategy(Strategy):
    """
    Trend Following Strategy

    Identifies and follows established trends using:
    - ADX (Average Directional Index) for trend strength
    - MACD for trend direction
    - Donchian Channels for breakouts

    Parameters:
        adx_period: ADX calculation period (default: 14)
        adx_threshold: Min ADX for strong trend (default: 25)
        macd_fast: MACD fast period (default: 12)
        macd_slow: MACD slow period (default: 26)
        macd_signal: MACD signal period (default: 9)
        donchian_period: Donchian channel period (default: 20)
    """

    name = "trend_following"
    description = "Follows established trends using ADX and MACD"

    DEFAULT_PARAMS = {
        "adx_period": 14,
        "adx_threshold": 25,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "donchian_period": 20,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX (Average Directional Index)"""
        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # Smooth the values
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()

        return adx, plus_di, minus_di

    def _calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_donchian(self, df: pd.DataFrame, period: int = 20) -> tuple:
        """Calculate Donchian Channels"""
        upper = df["High"].rolling(period).max()
        lower = df["Low"].rolling(period).min()
        middle = (upper + lower) / 2
        return upper, lower, middle

    def analyze(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> StrategyResult:
        """Analyze trends for given symbols"""
        signals = []
        summary = {"analyzed": 0, "trending": 0, "buy_signals": 0, "sell_signals": 0}

        for symbol in symbols:
            df = data.get(symbol)
            if df is None or len(df) < self.params["macd_slow"] + 10:
                continue

            summary["analyzed"] += 1
            close = df["Close"]
            current_price = close.iloc[-1]

            # Calculate indicators
            adx, plus_di, minus_di = self._calculate_adx(df, self.params["adx_period"])
            macd_line, signal_line, histogram = self._calculate_macd(
                close,
                self.params["macd_fast"],
                self.params["macd_slow"],
                self.params["macd_signal"],
            )
            dc_upper, dc_lower, dc_middle = self._calculate_donchian(
                df, self.params["donchian_period"]
            )

            # Get latest values
            current_adx = adx.iloc[-1]
            current_plus_di = plus_di.iloc[-1]
            current_minus_di = minus_di.iloc[-1]
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1]

            # Scoring
            score = 0.0
            reasons = []

            # Check trend strength
            is_trending = current_adx >= self.params["adx_threshold"]
            if is_trending:
                summary["trending"] += 1

                # Trend direction from DI
                if current_plus_di > current_minus_di:
                    score += 0.3
                    reasons.append(f"Uptrend (ADX: {current_adx:.1f})")
                else:
                    score -= 0.3
                    reasons.append(f"Downtrend (ADX: {current_adx:.1f})")

            # MACD signals
            if current_macd > current_signal:
                score += 0.2
                if histogram.iloc[-2] < 0 and current_histogram > 0:
                    score += 0.2
                    reasons.append("MACD bullish crossover")
            else:
                score -= 0.2
                if histogram.iloc[-2] > 0 and current_histogram < 0:
                    score -= 0.2
                    reasons.append("MACD bearish crossover")

            # Donchian breakout
            prev_close = close.iloc[-2]
            if current_price >= dc_upper.iloc[-2]:
                score += 0.3
                reasons.append("Donchian upper breakout")
            elif current_price <= dc_lower.iloc[-2]:
                score -= 0.3
                reasons.append("Donchian lower breakout")

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
                reason="; ".join(reasons) if reasons else "No clear trend",
                metadata={
                    "adx": round(current_adx, 2) if not np.isnan(current_adx) else None,
                    "plus_di": round(current_plus_di, 2) if not np.isnan(current_plus_di) else None,
                    "minus_di": round(current_minus_di, 2) if not np.isnan(current_minus_di) else None,
                    "macd": round(current_macd, 4),
                    "macd_signal": round(current_signal, 4),
                    "is_trending": is_trending,
                },
            ))

        return StrategyResult(
            strategy_name=self.name,
            symbols=symbols,
            signals=signals,
            summary=summary,
        )
