"""
Finnhub Data Provider

Provides:
- Real-time quotes
- Company news and sentiment
- Earnings calendar
- Insider transactions
- SEC filings

Requires API key (free tier: 60 calls/minute)
Get your key at: https://finnhub.io/
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import httpx
import pandas as pd

from .base import (
    StockDataProvider,
    Quote,
    CompanyInfo,
    FinancialData,
    NewsItem,
    Interval,
)


class FinnhubProvider(StockDataProvider):
    """
    Finnhub data provider.

    Features:
    - Real-time US stock quotes
    - Company news with sentiment
    - Earnings calendar
    - Insider transactions
    - Analyst recommendations
    - SEC filings

    Rate limits:
    - Free: 60 calls/minute
    - Premium: Higher limits

    Usage:
        provider = FinnhubProvider(api_key="your_key")
        quote = await provider.get_quote("AAPL")
        news = await provider.get_news("AAPL")
    """

    name = "finnhub"
    requires_api_key = True
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _request(self, endpoint: str, **params) -> Dict:
        """Make API request"""
        if not self.api_key:
            raise ValueError("Finnhub API key not configured")

        params["token"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> Quote:
        """Get current stock quote"""
        data = await self._request("quote", symbol=symbol.upper())

        if not data or data.get("c") == 0:
            raise ValueError(f"No data found for {symbol}")

        price = data.get("c", 0)  # Current price
        prev_close = data.get("pc", 0)  # Previous close
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        return Quote(
            symbol=symbol.upper(),
            price=round(price, 2),
            change=round(change, 2),
            change_percent=round(change_pct, 2),
            volume=0,  # Not provided in basic quote
            high=round(data.get("h", 0), 2),
            low=round(data.get("l", 0), 2),
            open=round(data.get("o", 0), 2),
            previous_close=round(prev_close, 2),
            timestamp=datetime.fromtimestamp(data.get("t", 0)) if data.get("t") else datetime.now(),
        )

    async def get_history(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        interval: Interval = Interval.DAY_1,
    ) -> pd.DataFrame:
        """Get historical OHLCV data (candles)"""
        # Convert dates to timestamps
        if not end:
            end = date.today()
        if not start:
            start = end - timedelta(days=365)

        start_ts = int(datetime.combine(start, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end, datetime.max.time()).timestamp())

        # Convert interval
        resolution = {
            Interval.MINUTE_1: "1",
            Interval.MINUTE_5: "5",
            Interval.MINUTE_15: "15",
            Interval.MINUTE_30: "30",
            Interval.HOUR_1: "60",
            Interval.DAY_1: "D",
            Interval.WEEK_1: "W",
            Interval.MONTH_1: "M",
        }.get(interval, "D")

        data = await self._request(
            "stock/candle",
            symbol=symbol.upper(),
            resolution=resolution,
            **{"from": start_ts, "to": end_ts}
        )

        if data.get("s") != "ok":
            return pd.DataFrame()

        df = pd.DataFrame({
            "Open": data.get("o", []),
            "High": data.get("h", []),
            "Low": data.get("l", []),
            "Close": data.get("c", []),
            "Volume": data.get("v", []),
        })

        df.index = pd.to_datetime(data.get("t", []), unit="s")
        return df.sort_index()

    async def get_company_info(self, symbol: str) -> CompanyInfo:
        """Get company profile"""
        data = await self._request("stock/profile2", symbol=symbol.upper())

        if not data:
            raise ValueError(f"No company info found for {symbol}")

        return CompanyInfo(
            symbol=data.get("ticker", symbol),
            name=data.get("name", ""),
            description="",  # Not provided
            sector=data.get("finnhubIndustry", ""),
            industry=data.get("finnhubIndustry", ""),
            country=data.get("country", ""),
            exchange=data.get("exchange", ""),
            currency=data.get("currency", "USD"),
            website=data.get("weburl"),
            employees=data.get("employeeTotal"),
        )

    async def get_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> List[FinancialData]:
        """Get basic financials (metrics)"""
        data = await self._request("stock/metric", symbol=symbol.upper(), metric="all")

        if not data or "metric" not in data:
            return []

        metrics = data.get("metric", {})

        # Create a single financial record with current metrics
        financial = FinancialData(
            symbol=symbol.upper(),
            period="current",
            fiscal_date=date.today(),
            pe_ratio=metrics.get("peBasicExclExtraTTM"),
            pb_ratio=metrics.get("pbQuarterly"),
            ps_ratio=metrics.get("psTTM"),
            peg_ratio=metrics.get("pegRatioTTM"),
            roe=metrics.get("roeTTM"),
            roa=metrics.get("roaTTM"),
            current_ratio=metrics.get("currentRatioQuarterly"),
            quick_ratio=metrics.get("quickRatioQuarterly"),
            debt_to_equity=metrics.get("totalDebt/totalEquityQuarterly"),
            eps=metrics.get("epsBasicExclExtraItemsTTM"),
            revenue=metrics.get("revenuePerShareTTM"),
            profit_margin=metrics.get("netProfitMarginTTM"),
        )

        return [financial]

    async def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        """Get company news"""
        # Get news from last 7 days
        end = date.today()
        start = end - timedelta(days=7)

        data = await self._request(
            "company-news",
            symbol=symbol.upper(),
            **{"from": start.isoformat(), "to": end.isoformat()}
        )

        if not data:
            return []

        items = []
        for article in data[:limit]:
            try:
                items.append(NewsItem(
                    title=article.get("headline", ""),
                    summary=article.get("summary", "")[:500],
                    url=article.get("url", ""),
                    source=article.get("source", ""),
                    published=datetime.fromtimestamp(article.get("datetime", 0)),
                    symbols=[symbol.upper()],
                    sentiment=None,  # Sentiment available in premium
                ))
            except Exception:
                continue

        return items

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for stocks"""
        data = await self._request("search", q=query)

        if not data or "result" not in data:
            return []

        results = []
        for item in data["result"][:limit]:
            results.append({
                "symbol": item.get("symbol", ""),
                "name": item.get("description", ""),
                "type": item.get("type", ""),
            })

        return results

    # ==================== Finnhub-specific features ====================

    async def get_earnings_calendar(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict]:
        """Get earnings calendar"""
        if not start:
            start = date.today()
        if not end:
            end = start + timedelta(days=30)

        params = {"from": start.isoformat(), "to": end.isoformat()}
        if symbol:
            params["symbol"] = symbol.upper()

        data = await self._request("calendar/earnings", **params)
        return data.get("earningsCalendar", [])

    async def get_insider_transactions(self, symbol: str) -> List[Dict]:
        """Get insider transactions"""
        data = await self._request("stock/insider-transactions", symbol=symbol.upper())
        return data.get("data", [])

    async def get_recommendations(self, symbol: str) -> List[Dict]:
        """Get analyst recommendations"""
        data = await self._request("stock/recommendation", symbol=symbol.upper())
        return data if isinstance(data, list) else []

    async def get_price_target(self, symbol: str) -> Dict:
        """Get analyst price targets"""
        return await self._request("stock/price-target", symbol=symbol.upper())

    async def get_peers(self, symbol: str) -> List[str]:
        """Get company peers"""
        data = await self._request("stock/peers", symbol=symbol.upper())
        return data if isinstance(data, list) else []

    async def get_sentiment(self, symbol: str) -> Dict:
        """Get social sentiment (requires premium)"""
        try:
            return await self._request("stock/social-sentiment", symbol=symbol.upper())
        except Exception:
            return {}

    async def get_sec_filings(self, symbol: str) -> List[Dict]:
        """Get SEC filings"""
        data = await self._request("stock/filings", symbol=symbol.upper())
        return data if isinstance(data, list) else []

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()
