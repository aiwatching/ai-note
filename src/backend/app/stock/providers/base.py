"""
Stock Data Provider Base Class

Defines the interface for all stock data providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from enum import Enum
import pandas as pd


class Interval(str, Enum):
    """Data interval"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1wk"
    MONTH_1 = "1mo"


@dataclass
class Quote:
    """Real-time or delayed stock quote"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: datetime
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    avg_volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "previous_close": self.previous_close,
            "timestamp": self.timestamp.isoformat(),
            "market_cap": self.market_cap,
            "pe_ratio": self.pe_ratio,
            "week_52_high": self.week_52_high,
            "week_52_low": self.week_52_low,
        }


@dataclass
class OHLCV:
    """OHLCV (candlestick) data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "adjusted_close": self.adjusted_close,
        }


@dataclass
class CompanyInfo:
    """Company information"""
    symbol: str
    name: str
    description: str
    sector: str
    industry: str
    country: str
    exchange: str
    currency: str
    website: Optional[str] = None
    employees: Optional[int] = None
    ceo: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "description": self.description,
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "exchange": self.exchange,
            "currency": self.currency,
            "website": self.website,
            "employees": self.employees,
        }


@dataclass
class FinancialData:
    """Company financial data"""
    symbol: str
    period: str  # "annual" or "quarterly"
    fiscal_date: date

    # Income Statement
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None

    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash: Optional[float] = None
    total_debt: Optional[float] = None

    # Cash Flow
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    dividends_paid: Optional[float] = None

    # Ratios
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class NewsItem:
    """News article"""
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    symbols: List[str] = field(default_factory=list)
    sentiment: Optional[float] = None  # -1 to 1
    relevance: Optional[float] = None  # 0 to 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat(),
            "symbols": self.symbols,
            "sentiment": self.sentiment,
        }


class StockDataProvider(ABC):
    """
    Abstract base class for stock data providers.

    All providers must implement these methods to fetch stock data.
    """

    name: str = "base"
    requires_api_key: bool = False

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get current stock quote"""
        pass

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        interval: Interval = Interval.DAY_1,
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data.

        Returns DataFrame with columns: Open, High, Low, Close, Volume, Adj Close
        Index is DatetimeIndex.
        """
        pass

    @abstractmethod
    async def get_company_info(self, symbol: str) -> CompanyInfo:
        """Get company information"""
        pass

    @abstractmethod
    async def get_financials(
        self,
        symbol: str,
        period: str = "annual",  # "annual" or "quarterly"
    ) -> List[FinancialData]:
        """Get company financial statements"""
        pass

    async def get_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> List[NewsItem]:
        """Get news related to a stock (optional)"""
        return []

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for stocks by name or symbol (optional)"""
        return []

    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = await self.get_quote(symbol)
            except Exception:
                pass
        return quotes

    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        return True
