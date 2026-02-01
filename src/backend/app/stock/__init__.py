"""
Stock Analysis & Quantitative Trading Module

A comprehensive investment analysis system with:
- Multiple data providers (yfinance, Alpha Vantage, Finnhub)
- Technical analysis (indicators, patterns)
- Fundamental analysis (financials, ratios, valuations)
- Sentiment analysis (news, keywords)
- Quantitative strategies (momentum, mean reversion, factor models)
- Portfolio management & optimization
- Risk analysis & management
"""

from .providers import (
    StockDataProvider,
    Quote,
    OHLCV,
    CompanyInfo,
    FinancialData,
    NewsItem,
    Interval,
    YFinanceProvider,
    AlphaVantageProvider,
    FinnhubProvider,
    get_data_provider,
)
from .analysis import (
    TechnicalAnalyzer,
    FundamentalAnalyzer,
    SentimentAnalyzer,
)
from .strategies import (
    Strategy,
    StrategySignal,
    SignalType,
    StrategyResult,
    MomentumStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    PairsTradingStrategy,
    FactorStrategy,
    MultiFactorStrategy,
)
from .portfolio import (
    Portfolio,
    PortfolioManager,
    PortfolioSummary,
    Holding,
    RiskManager,
    RiskMetrics,
    PositionSizer,
    PortfolioOptimizer,
    OptimizationResult,
    OptimizationMethod,
)
from .service import StockService, AnalysisResult

__all__ = [
    # Providers
    "StockDataProvider",
    "Quote",
    "OHLCV",
    "CompanyInfo",
    "FinancialData",
    "NewsItem",
    "Interval",
    "YFinanceProvider",
    "AlphaVantageProvider",
    "FinnhubProvider",
    "get_data_provider",
    # Analysis
    "TechnicalAnalyzer",
    "FundamentalAnalyzer",
    "SentimentAnalyzer",
    # Strategies
    "Strategy",
    "StrategySignal",
    "SignalType",
    "StrategyResult",
    "MomentumStrategy",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "PairsTradingStrategy",
    "FactorStrategy",
    "MultiFactorStrategy",
    # Portfolio
    "Portfolio",
    "PortfolioManager",
    "PortfolioSummary",
    "Holding",
    "RiskManager",
    "RiskMetrics",
    "PositionSizer",
    "PortfolioOptimizer",
    "OptimizationResult",
    "OptimizationMethod",
    # Service
    "StockService",
    "AnalysisResult",
]
