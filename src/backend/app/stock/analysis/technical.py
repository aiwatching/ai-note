"""
Technical Analysis Module

Provides technical indicators and pattern recognition for stock analysis.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Signal(str, Enum):
    """Trading signal"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class Trend(str, Enum):
    """Market trend"""
    STRONG_UPTREND = "strong_uptrend"
    UPTREND = "uptrend"
    SIDEWAYS = "sideways"
    DOWNTREND = "downtrend"
    STRONG_DOWNTREND = "strong_downtrend"


@dataclass
class TechnicalSignal:
    """Technical analysis signal"""
    indicator: str
    value: float
    signal: Signal
    description: str


@dataclass
class TechnicalSummary:
    """Summary of technical analysis"""
    symbol: str
    trend: Trend
    signals: List[TechnicalSignal]
    support_levels: List[float]
    resistance_levels: List[float]
    overall_signal: Signal
    score: float  # -100 to 100


class TechnicalAnalyzer:
    """
    Technical Analysis Engine

    Calculates technical indicators and generates trading signals.

    Indicators included:
    - Moving Averages (SMA, EMA, WMA)
    - Momentum (RSI, Stochastic, Williams %R)
    - Trend (MACD, ADX, Parabolic SAR)
    - Volatility (Bollinger Bands, ATR)
    - Volume (OBV, Volume SMA)
    - Support/Resistance levels

    Usage:
        analyzer = TechnicalAnalyzer()
        df = analyzer.add_all_indicators(price_df)
        summary = analyzer.analyze(price_df, symbol="AAPL")
    """

    # ==================== Moving Averages ====================

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def wma(series: pd.Series, period: int) -> pd.Series:
        """Weighted Moving Average"""
        weights = np.arange(1, period + 1)
        return series.rolling(period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    # ==================== Momentum Indicators ====================

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator (%K and %D)"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return k, d

    @staticmethod
    def williams_r(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        wr = -100 * (highest_high - close) / (highest_high - lowest_low)
        return wr

    @staticmethod
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20,
    ) -> pd.Series:
        """Commodity Channel Index"""
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        cci = (typical_price - sma) / (0.015 * mad)
        return cci

    # ==================== Trend Indicators ====================

    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Average Directional Index"""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()

        return adx

    # ==================== Volatility Indicators ====================

    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return upper, middle, lower

    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Average True Range"""
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        return tr.ewm(alpha=1/period, min_periods=period).mean()

    # ==================== Volume Indicators ====================

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        direction = np.sign(close.diff())
        return (direction * volume).cumsum()

    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> pd.Series:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()

    # ==================== Support/Resistance ====================

    @staticmethod
    def find_support_resistance(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        window: int = 20,
        num_levels: int = 3,
    ) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels using pivot points"""
        current_price = close.iloc[-1]

        # Find local minima and maxima
        lows = low.rolling(window=window, center=True).min()
        highs = high.rolling(window=window, center=True).max()

        # Get unique levels
        support_candidates = lows[lows == low].dropna().unique()
        resistance_candidates = highs[highs == high].dropna().unique()

        # Filter to levels near current price
        price_range = current_price * 0.2  # 20% range

        supports = sorted([
            float(s) for s in support_candidates
            if s < current_price and s > current_price - price_range
        ], reverse=True)[:num_levels]

        resistances = sorted([
            float(r) for r in resistance_candidates
            if r > current_price and r < current_price + price_range
        ])[:num_levels]

        return supports, resistances

    # ==================== Add All Indicators ====================

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators and return DataFrame with indicators"""
        return self.add_all_indicators(df)

    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to a DataFrame"""
        df = df.copy()

        # Ensure column names are correct
        close = df["Close"] if "Close" in df.columns else df["close"]
        high = df["High"] if "High" in df.columns else df["high"]
        low = df["Low"] if "Low" in df.columns else df["low"]
        volume = df["Volume"] if "Volume" in df.columns else df.get("volume", pd.Series(0, index=df.index))

        # Moving Averages
        df["SMA_20"] = self.sma(close, 20)
        df["SMA_50"] = self.sma(close, 50)
        df["SMA_200"] = self.sma(close, 200)
        df["EMA_12"] = self.ema(close, 12)
        df["EMA_26"] = self.ema(close, 26)

        # Momentum
        df["RSI_14"] = self.rsi(close, 14)
        df["Stoch_K"], df["Stoch_D"] = self.stochastic(high, low, close)
        df["Williams_R"] = self.williams_r(high, low, close)
        df["CCI"] = self.cci(high, low, close)

        # Trend
        df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = self.macd(close)
        df["ADX"] = self.adx(high, low, close)

        # Volatility
        df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = self.bollinger_bands(close)
        df["ATR"] = self.atr(high, low, close)

        # Volume
        if volume.sum() > 0:
            df["OBV"] = self.obv(close, volume)
            df["VWAP"] = self.vwap(high, low, close, volume)

        return df

    # ==================== Signal Generation ====================

    def _get_rsi_signal(self, rsi: float) -> TechnicalSignal:
        """Generate RSI signal"""
        if rsi >= 80:
            signal = Signal.STRONG_SELL
            desc = "Extremely overbought"
        elif rsi >= 70:
            signal = Signal.SELL
            desc = "Overbought"
        elif rsi <= 20:
            signal = Signal.STRONG_BUY
            desc = "Extremely oversold"
        elif rsi <= 30:
            signal = Signal.BUY
            desc = "Oversold"
        else:
            signal = Signal.NEUTRAL
            desc = "Neutral"

        return TechnicalSignal("RSI", rsi, signal, desc)

    def _get_macd_signal(self, macd: float, signal_line: float, hist: float) -> TechnicalSignal:
        """Generate MACD signal"""
        if macd > signal_line and hist > 0:
            if hist > abs(macd) * 0.1:
                signal = Signal.STRONG_BUY
                desc = "Strong bullish momentum"
            else:
                signal = Signal.BUY
                desc = "Bullish crossover"
        elif macd < signal_line and hist < 0:
            if abs(hist) > abs(macd) * 0.1:
                signal = Signal.STRONG_SELL
                desc = "Strong bearish momentum"
            else:
                signal = Signal.SELL
                desc = "Bearish crossover"
        else:
            signal = Signal.NEUTRAL
            desc = "No clear trend"

        return TechnicalSignal("MACD", macd, signal, desc)

    def _get_ma_signal(self, price: float, sma_20: float, sma_50: float, sma_200: float) -> TechnicalSignal:
        """Generate Moving Average signal"""
        above_20 = price > sma_20
        above_50 = price > sma_50
        above_200 = price > sma_200

        count = sum([above_20, above_50, above_200])

        if count == 3 and sma_20 > sma_50 > sma_200:
            signal = Signal.STRONG_BUY
            desc = "Price above all MAs, golden cross pattern"
        elif count >= 2:
            signal = Signal.BUY
            desc = "Price above major MAs"
        elif count == 0 and sma_20 < sma_50 < sma_200:
            signal = Signal.STRONG_SELL
            desc = "Price below all MAs, death cross pattern"
        elif count <= 1:
            signal = Signal.SELL
            desc = "Price below major MAs"
        else:
            signal = Signal.NEUTRAL
            desc = "Mixed MA signals"

        return TechnicalSignal("Moving Averages", price, signal, desc)

    def _get_bb_signal(self, price: float, upper: float, middle: float, lower: float) -> TechnicalSignal:
        """Generate Bollinger Bands signal"""
        bb_position = (price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        if bb_position >= 0.95:
            signal = Signal.SELL
            desc = "Price at upper band (overbought)"
        elif bb_position >= 0.8:
            signal = Signal.NEUTRAL
            desc = "Price near upper band"
        elif bb_position <= 0.05:
            signal = Signal.BUY
            desc = "Price at lower band (oversold)"
        elif bb_position <= 0.2:
            signal = Signal.NEUTRAL
            desc = "Price near lower band"
        else:
            signal = Signal.NEUTRAL
            desc = "Price within bands"

        return TechnicalSignal("Bollinger Bands", bb_position * 100, signal, desc)

    def _get_trend(self, adx: float, price: float, sma_20: float, sma_50: float) -> Trend:
        """Determine market trend"""
        trending = adx > 25
        strong_trend = adx > 40

        if price > sma_20 > sma_50:
            if strong_trend:
                return Trend.STRONG_UPTREND
            elif trending:
                return Trend.UPTREND
        elif price < sma_20 < sma_50:
            if strong_trend:
                return Trend.STRONG_DOWNTREND
            elif trending:
                return Trend.DOWNTREND

        return Trend.SIDEWAYS

    def generate_signals(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading signals from indicator DataFrame.

        Args:
            df: DataFrame with indicators (from calculate_all_indicators)

        Returns:
            Dict with signal information
        """
        latest = df.iloc[-1]
        signals = {}

        # RSI signal
        if "RSI_14" in df.columns and pd.notna(latest["RSI_14"]):
            rsi = latest["RSI_14"]
            signals["rsi"] = {
                "value": round(rsi, 2),
                "signal": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",
            }

        # MACD signal
        if all(k in df.columns for k in ["MACD", "MACD_Signal"]):
            macd = latest["MACD"]
            macd_signal = latest["MACD_Signal"]
            signals["macd"] = {
                "macd": round(macd, 4),
                "signal_line": round(macd_signal, 4),
                "signal": "bullish" if macd > macd_signal else "bearish",
            }

        # Moving average signals
        close = latest.get("Close", latest.get("close"))
        ma_signals = []

        if "SMA_20" in df.columns and pd.notna(latest["SMA_20"]):
            ma_signals.append(("sma_20", close > latest["SMA_20"]))
        if "SMA_50" in df.columns and pd.notna(latest["SMA_50"]):
            ma_signals.append(("sma_50", close > latest["SMA_50"]))
        if "SMA_200" in df.columns and pd.notna(latest["SMA_200"]):
            ma_signals.append(("sma_200", close > latest["SMA_200"]))

        if ma_signals:
            above_count = sum(1 for _, above in ma_signals if above)
            signals["moving_averages"] = {
                "above_count": above_count,
                "total": len(ma_signals),
                "signal": "bullish" if above_count >= 2 else "bearish" if above_count == 0 else "neutral",
            }

        # Bollinger Bands
        if all(k in df.columns for k in ["BB_Upper", "BB_Lower"]):
            bb_upper = latest["BB_Upper"]
            bb_lower = latest["BB_Lower"]
            if bb_upper != bb_lower:
                bb_position = (close - bb_lower) / (bb_upper - bb_lower)
                signals["bollinger"] = {
                    "position": round(bb_position, 3),
                    "signal": "overbought" if bb_position > 0.95 else "oversold" if bb_position < 0.05 else "neutral",
                }

        # ADX trend strength
        if "ADX" in df.columns and pd.notna(latest["ADX"]):
            adx = latest["ADX"]
            signals["adx"] = {
                "value": round(adx, 2),
                "trend_strength": "strong" if adx > 40 else "moderate" if adx > 25 else "weak",
            }

        # Calculate overall trend score (-1 to 1)
        score = 0.0
        weight_sum = 0.0

        # RSI contribution
        if "rsi" in signals:
            rsi = signals["rsi"]["value"]
            if rsi < 30:
                score += 0.3
            elif rsi > 70:
                score -= 0.3
            weight_sum += 1

        # MACD contribution
        if "macd" in signals:
            if signals["macd"]["signal"] == "bullish":
                score += 0.3
            else:
                score -= 0.3
            weight_sum += 1

        # MA contribution
        if "moving_averages" in signals:
            ma_ratio = signals["moving_averages"]["above_count"] / signals["moving_averages"]["total"]
            score += (ma_ratio - 0.5) * 0.6
            weight_sum += 1

        signals["trend_score"] = round(score / weight_sum, 3) if weight_sum > 0 else 0

        return signals

    # ==================== Full Analysis ====================

    def analyze(self, df: pd.DataFrame, symbol: str = "") -> TechnicalSummary:
        """
        Perform full technical analysis on price data.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            TechnicalSummary with signals and levels
        """
        # Add indicators
        df = self.add_all_indicators(df)

        # Get latest values
        latest = df.iloc[-1]
        close = latest.get("Close", latest.get("close"))
        high = df["High"] if "High" in df.columns else df["high"]
        low = df["Low"] if "Low" in df.columns else df["low"]
        close_series = df["Close"] if "Close" in df.columns else df["close"]

        signals = []

        # RSI Signal
        if "RSI_14" in latest and pd.notna(latest["RSI_14"]):
            signals.append(self._get_rsi_signal(latest["RSI_14"]))

        # MACD Signal
        if all(k in latest for k in ["MACD", "MACD_Signal", "MACD_Hist"]):
            signals.append(self._get_macd_signal(
                latest["MACD"], latest["MACD_Signal"], latest["MACD_Hist"]
            ))

        # MA Signal
        if all(k in latest for k in ["SMA_20", "SMA_50", "SMA_200"]):
            signals.append(self._get_ma_signal(
                close, latest["SMA_20"], latest["SMA_50"], latest["SMA_200"]
            ))

        # Bollinger Bands Signal
        if all(k in latest for k in ["BB_Upper", "BB_Middle", "BB_Lower"]):
            signals.append(self._get_bb_signal(
                close, latest["BB_Upper"], latest["BB_Middle"], latest["BB_Lower"]
            ))

        # Find support/resistance
        supports, resistances = self.find_support_resistance(high, low, close_series)

        # Determine trend
        trend = Trend.SIDEWAYS
        if "ADX" in latest and "SMA_20" in latest and "SMA_50" in latest:
            trend = self._get_trend(
                latest["ADX"], close, latest["SMA_20"], latest["SMA_50"]
            )

        # Calculate overall score (-100 to 100)
        signal_scores = {
            Signal.STRONG_BUY: 100,
            Signal.BUY: 50,
            Signal.NEUTRAL: 0,
            Signal.SELL: -50,
            Signal.STRONG_SELL: -100,
        }

        if signals:
            score = sum(signal_scores[s.signal] for s in signals) / len(signals)
        else:
            score = 0

        # Determine overall signal
        if score >= 50:
            overall = Signal.STRONG_BUY
        elif score >= 20:
            overall = Signal.BUY
        elif score <= -50:
            overall = Signal.STRONG_SELL
        elif score <= -20:
            overall = Signal.SELL
        else:
            overall = Signal.NEUTRAL

        return TechnicalSummary(
            symbol=symbol,
            trend=trend,
            signals=signals,
            support_levels=supports,
            resistance_levels=resistances,
            overall_signal=overall,
            score=round(score, 2),
        )
