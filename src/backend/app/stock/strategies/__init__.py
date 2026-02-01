"""
Quantitative Trading Strategies Module

Provides various algorithmic trading strategies.
"""

from .base import (
    Strategy,
    StrategySignal,
    SignalType,
    StrategyResult,
    Position,
    Trade,
)
from .momentum import MomentumStrategy, TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy, PairsTradingStrategy
from .factor import FactorStrategy, MultiFactorStrategy

__all__ = [
    # Base
    "Strategy",
    "StrategySignal",
    "SignalType",
    "StrategyResult",
    "Position",
    "Trade",
    # Momentum
    "MomentumStrategy",
    "TrendFollowingStrategy",
    # Mean Reversion
    "MeanReversionStrategy",
    "PairsTradingStrategy",
    # Factor
    "FactorStrategy",
    "MultiFactorStrategy",
]
