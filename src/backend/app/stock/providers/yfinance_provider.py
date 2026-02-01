"""
Yahoo Finance Data Provider

Free, no API key required.
Provides real-time quotes, historical data, financials, and company info.
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import pandas as pd

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from .base import (
    StockDataProvider,
    Quote,
    OHLCV,
    CompanyInfo,
    FinancialData,
    NewsItem,
    Interval,
)


class YFinanceProvider(StockDataProvider):
    """
    Yahoo Finance data provider.

    Features:
    - Real-time quotes (15-20 min delayed for free)
    - Historical OHLCV data
    - Company info & financials
    - No API key required
    - Rate limits are generous

    Usage:
        provider = YFinanceProvider()
        quote = await provider.get_quote("AAPL")
        history = await provider.get_history("AAPL", period="1mo")
    """

    name = "yfinance"
    requires_api_key = False

    def __init__(self):
        if not HAS_YFINANCE:
            raise ImportError("yfinance not installed. Run: pip install yfinance")
        self._cache: Dict[str, yf.Ticker] = {}

    def _get_ticker(self, symbol: str) -> "yf.Ticker":
        """Get or create ticker object with caching"""
        symbol = symbol.upper()
        if symbol not in self._cache:
            self._cache[symbol] = yf.Ticker(symbol)
        return self._cache[symbol]

    async def get_quote(self, symbol: str) -> Quote:
        """Get current stock quote"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="2d")

            if hist.empty:
                raise ValueError(f"No data found for {symbol}")

            current = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else current["Open"]
            price = current["Close"]
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return Quote(
                symbol=symbol.upper(),
                price=round(price, 2),
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=int(current["Volume"]),
                high=round(current["High"], 2),
                low=round(current["Low"], 2),
                open=round(current["Open"], 2),
                previous_close=round(prev_close, 2),
                timestamp=datetime.now(),
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
                avg_volume=info.get("averageVolume"),
                bid=info.get("bid"),
                ask=info.get("ask"),
            )

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_history(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        interval: Interval = Interval.DAY_1,
    ) -> pd.DataFrame:
        """Get historical OHLCV data"""
        def _fetch():
            ticker = self._get_ticker(symbol)

            # Convert interval
            yf_interval = {
                Interval.MINUTE_1: "1m",
                Interval.MINUTE_5: "5m",
                Interval.MINUTE_15: "15m",
                Interval.MINUTE_30: "30m",
                Interval.HOUR_1: "1h",
                Interval.DAY_1: "1d",
                Interval.WEEK_1: "1wk",
                Interval.MONTH_1: "1mo",
            }.get(interval, "1d")

            # Default date range
            if not end:
                end = date.today()
            if not start:
                start = end - timedelta(days=365)

            hist = ticker.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval=yf_interval,
            )

            # Rename columns to standard format
            hist.columns = [c.replace(" ", "_") for c in hist.columns]

            return hist

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_company_info(self, symbol: str) -> CompanyInfo:
        """Get company information"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            info = ticker.info

            return CompanyInfo(
                symbol=symbol.upper(),
                name=info.get("longName", info.get("shortName", symbol)),
                description=info.get("longBusinessSummary", ""),
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                country=info.get("country", ""),
                exchange=info.get("exchange", ""),
                currency=info.get("currency", "USD"),
                website=info.get("website"),
                employees=info.get("fullTimeEmployees"),
            )

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> List[FinancialData]:
        """Get company financial statements"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            info = ticker.info

            # Get financial statements
            if period == "quarterly":
                income = ticker.quarterly_income_stmt
                balance = ticker.quarterly_balance_sheet
                cash_flow = ticker.quarterly_cashflow
            else:
                income = ticker.income_stmt
                balance = ticker.balance_sheet
                cash_flow = ticker.cashflow

            financials = []

            # Process each period
            for col in income.columns[:4]:  # Last 4 periods
                try:
                    fiscal_date = col.date() if hasattr(col, 'date') else date.today()

                    # Helper to safely get values
                    def get_val(df, keys):
                        for key in keys:
                            if key in df.index:
                                val = df.loc[key, col]
                                if pd.notna(val):
                                    return float(val)
                        return None

                    financial = FinancialData(
                        symbol=symbol.upper(),
                        period=period,
                        fiscal_date=fiscal_date,
                        # Income Statement
                        revenue=get_val(income, ["Total Revenue", "Revenue"]),
                        gross_profit=get_val(income, ["Gross Profit"]),
                        operating_income=get_val(income, ["Operating Income", "EBIT"]),
                        net_income=get_val(income, ["Net Income", "Net Income Common Stockholders"]),
                        eps=info.get("trailingEps"),
                        # Balance Sheet
                        total_assets=get_val(balance, ["Total Assets"]),
                        total_liabilities=get_val(balance, ["Total Liabilities Net Minority Interest", "Total Liab"]),
                        total_equity=get_val(balance, ["Total Equity Gross Minority Interest", "Total Stockholder Equity"]),
                        cash=get_val(balance, ["Cash And Cash Equivalents", "Cash"]),
                        total_debt=get_val(balance, ["Total Debt"]),
                        # Cash Flow
                        operating_cash_flow=get_val(cash_flow, ["Operating Cash Flow", "Total Cash From Operating Activities"]),
                        free_cash_flow=get_val(cash_flow, ["Free Cash Flow"]),
                        # Ratios from info
                        pe_ratio=info.get("trailingPE"),
                        pb_ratio=info.get("priceToBook"),
                        ps_ratio=info.get("priceToSalesTrailing12Months"),
                        peg_ratio=info.get("pegRatio"),
                        debt_to_equity=info.get("debtToEquity"),
                        current_ratio=info.get("currentRatio"),
                        roe=info.get("returnOnEquity"),
                        roa=info.get("returnOnAssets"),
                        profit_margin=info.get("profitMargins"),
                        operating_margin=info.get("operatingMargins"),
                    )
                    financials.append(financial)
                except Exception:
                    continue

            return financials

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        """Get news related to a stock"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            news = ticker.news[:limit] if hasattr(ticker, 'news') else []

            items = []
            for article in news:
                try:
                    items.append(NewsItem(
                        title=article.get("title", ""),
                        summary=article.get("summary", "")[:500] if article.get("summary") else "",
                        url=article.get("link", ""),
                        source=article.get("publisher", ""),
                        published=datetime.fromtimestamp(article.get("providerPublishTime", 0)),
                        symbols=[symbol.upper()],
                    ))
                except Exception:
                    continue
            return items

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for stocks"""
        def _fetch():
            # yfinance doesn't have a built-in search
            # We can try to look up the symbol directly
            try:
                ticker = yf.Ticker(query)
                info = ticker.info
                if info.get("symbol"):
                    return [{
                        "symbol": info.get("symbol"),
                        "name": info.get("longName", info.get("shortName", "")),
                        "exchange": info.get("exchange", ""),
                        "type": info.get("quoteType", ""),
                    }]
            except Exception:
                pass
            return []

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_options_chain(self, symbol: str) -> Dict:
        """Get options chain data"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            dates = ticker.options

            if not dates:
                return {"expirations": [], "calls": [], "puts": []}

            # Get first expiration
            opt = ticker.option_chain(dates[0])

            return {
                "expirations": list(dates),
                "calls": opt.calls.to_dict("records") if not opt.calls.empty else [],
                "puts": opt.puts.to_dict("records") if not opt.puts.empty else [],
            }

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_recommendations(self, symbol: str) -> List[Dict]:
        """Get analyst recommendations"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            recs = ticker.recommendations

            if recs is None or recs.empty:
                return []

            return recs.tail(10).to_dict("records")

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)

    async def get_institutional_holders(self, symbol: str) -> List[Dict]:
        """Get institutional holders"""
        def _fetch():
            ticker = self._get_ticker(symbol)
            holders = ticker.institutional_holders

            if holders is None or holders.empty:
                return []

            return holders.to_dict("records")

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)
