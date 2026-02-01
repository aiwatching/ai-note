"""
Stock Data Providers

Unified interface for fetching stock data from multiple sources.
"""

from .base import StockDataProvider, Quote, OHLCV, CompanyInfo, FinancialData, NewsItem, Interval
from .yfinance_provider import YFinanceProvider
from .alphavantage_provider import AlphaVantageProvider
from .finnhub_provider import FinnhubProvider

# Provider registry
_providers = {}


def register_provider(name: str, provider: StockDataProvider):
    """Register a data provider"""
    _providers[name] = provider


def get_data_provider(name: str = None) -> StockDataProvider:
    """
    Get a data provider by name.
    If no name specified, returns the first available provider.
    """
    if name and name in _providers:
        return _providers[name]

    # Return first available
    if _providers:
        return list(_providers.values())[0]

    # Default to yfinance (always available)
    return YFinanceProvider()


def list_providers() -> list:
    """List registered providers"""
    return list(_providers.keys())


__all__ = [
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
    "register_provider",
    "get_data_provider",
    "list_providers",
]
