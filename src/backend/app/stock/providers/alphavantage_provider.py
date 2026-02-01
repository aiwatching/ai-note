"""
Alpha Vantage Data Provider

Provides:
- Real-time and historical stock data
- Technical indicators
- Fundamental data
- Forex and crypto

Requires API key (free tier: 25 requests/day)
Get your key at: https://www.alphavantage.co/support/#api-key
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import httpx
import pandas as pd

from .base import (
    StockDataProvider,
    Quote,
    CompanyInfo,
    FinancialData,
    Interval,
)


class AlphaVantageProvider(StockDataProvider):
    """
    Alpha Vantage data provider.

    Features:
    - Real-time quotes
    - Intraday and daily historical data
    - Technical indicators (SMA, EMA, RSI, MACD, etc.)
    - Fundamental data
    - Sector performance

    Rate limits:
    - Free: 25 requests/day
    - Premium: Higher limits

    Usage:
        provider = AlphaVantageProvider(api_key="your_key")
        quote = await provider.get_quote("AAPL")
    """

    name = "alphavantage"
    requires_api_key = True
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _request(self, **params) -> Dict:
        """Make API request"""
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")

        params["apikey"] = self.api_key
        response = await self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # Check for error messages
        if "Error Message" in data:
            raise ValueError(data["Error Message"])
        if "Note" in data:
            raise ValueError(f"Rate limit: {data['Note']}")

        return data

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_quote(self, symbol: str) -> Quote:
        """Get current stock quote"""
        data = await self._request(
            function="GLOBAL_QUOTE",
            symbol=symbol.upper()
        )

        q = data.get("Global Quote", {})
        if not q:
            raise ValueError(f"No data found for {symbol}")

        price = float(q.get("05. price", 0))
        prev_close = float(q.get("08. previous close", 0))
        change = float(q.get("09. change", 0))
        change_pct = float(q.get("10. change percent", "0%").replace("%", ""))

        return Quote(
            symbol=symbol.upper(),
            price=price,
            change=change,
            change_percent=change_pct,
            volume=int(q.get("06. volume", 0)),
            high=float(q.get("03. high", 0)),
            low=float(q.get("04. low", 0)),
            open=float(q.get("02. open", 0)),
            previous_close=prev_close,
            timestamp=datetime.now(),
        )

    async def get_history(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        interval: Interval = Interval.DAY_1,
    ) -> pd.DataFrame:
        """Get historical OHLCV data"""
        # Determine function based on interval
        if interval in [Interval.MINUTE_1, Interval.MINUTE_5, Interval.MINUTE_15, Interval.MINUTE_30, Interval.HOUR_1]:
            function = "TIME_SERIES_INTRADAY"
            av_interval = {
                Interval.MINUTE_1: "1min",
                Interval.MINUTE_5: "5min",
                Interval.MINUTE_15: "15min",
                Interval.MINUTE_30: "30min",
                Interval.HOUR_1: "60min",
            }.get(interval, "5min")

            data = await self._request(
                function=function,
                symbol=symbol.upper(),
                interval=av_interval,
                outputsize="full"
            )
            time_series_key = f"Time Series ({av_interval})"
        else:
            function = "TIME_SERIES_DAILY_ADJUSTED"
            data = await self._request(
                function=function,
                symbol=symbol.upper(),
                outputsize="full"
            )
            time_series_key = "Time Series (Daily)"

        series = data.get(time_series_key, {})
        if not series:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(series, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Rename columns
        df.columns = [c.split(". ")[1] if ". " in c else c for c in df.columns]
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "adjusted close": "Adj_Close",
            "volume": "Volume",
        })

        # Convert to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Filter by date range
        if start:
            df = df[df.index.date >= start]
        if end:
            df = df[df.index.date <= end]

        return df

    async def get_company_info(self, symbol: str) -> CompanyInfo:
        """Get company information"""
        data = await self._request(
            function="OVERVIEW",
            symbol=symbol.upper()
        )

        if not data or "Symbol" not in data:
            raise ValueError(f"No company info found for {symbol}")

        return CompanyInfo(
            symbol=data.get("Symbol", symbol),
            name=data.get("Name", ""),
            description=data.get("Description", ""),
            sector=data.get("Sector", ""),
            industry=data.get("Industry", ""),
            country=data.get("Country", ""),
            exchange=data.get("Exchange", ""),
            currency=data.get("Currency", "USD"),
            employees=int(data["FullTimeEmployees"]) if data.get("FullTimeEmployees") else None,
        )

    async def get_financials(
        self,
        symbol: str,
        period: str = "annual",
    ) -> List[FinancialData]:
        """Get company financial statements"""
        # Fetch all financial data
        income = await self._request(function="INCOME_STATEMENT", symbol=symbol.upper())
        balance = await self._request(function="BALANCE_SHEET", symbol=symbol.upper())
        cash_flow = await self._request(function="CASH_FLOW", symbol=symbol.upper())
        overview = await self._request(function="OVERVIEW", symbol=symbol.upper())

        # Select annual or quarterly
        reports_key = "annualReports" if period == "annual" else "quarterlyReports"

        income_reports = income.get(reports_key, [])
        balance_reports = balance.get(reports_key, [])
        cash_reports = cash_flow.get(reports_key, [])

        financials = []

        for i, inc_report in enumerate(income_reports[:4]):
            try:
                bal_report = balance_reports[i] if i < len(balance_reports) else {}
                cf_report = cash_reports[i] if i < len(cash_reports) else {}

                def get_float(d, key):
                    val = d.get(key)
                    if val and val != "None":
                        return float(val)
                    return None

                fiscal_date = datetime.strptime(inc_report.get("fiscalDateEnding", "2024-01-01"), "%Y-%m-%d").date()

                financial = FinancialData(
                    symbol=symbol.upper(),
                    period=period,
                    fiscal_date=fiscal_date,
                    # Income Statement
                    revenue=get_float(inc_report, "totalRevenue"),
                    gross_profit=get_float(inc_report, "grossProfit"),
                    operating_income=get_float(inc_report, "operatingIncome"),
                    net_income=get_float(inc_report, "netIncome"),
                    eps=get_float(overview, "EPS"),
                    # Balance Sheet
                    total_assets=get_float(bal_report, "totalAssets"),
                    total_liabilities=get_float(bal_report, "totalLiabilities"),
                    total_equity=get_float(bal_report, "totalShareholderEquity"),
                    cash=get_float(bal_report, "cashAndCashEquivalentsAtCarryingValue"),
                    total_debt=get_float(bal_report, "longTermDebt"),
                    # Cash Flow
                    operating_cash_flow=get_float(cf_report, "operatingCashflow"),
                    free_cash_flow=get_float(cf_report, "freeCashFlow") if cf_report.get("freeCashFlow") else None,
                    # Ratios
                    pe_ratio=get_float(overview, "PERatio"),
                    pb_ratio=get_float(overview, "PriceToBookRatio"),
                    peg_ratio=get_float(overview, "PEGRatio"),
                    roe=get_float(overview, "ReturnOnEquityTTM"),
                    roa=get_float(overview, "ReturnOnAssetsTTM"),
                    profit_margin=get_float(overview, "ProfitMargin"),
                    operating_margin=get_float(overview, "OperatingMarginTTM"),
                )
                financials.append(financial)
            except Exception:
                continue

        return financials

    # ==================== Technical Indicators ====================

    async def get_sma(self, symbol: str, period: int = 20, interval: str = "daily") -> pd.Series:
        """Get Simple Moving Average"""
        data = await self._request(
            function="SMA",
            symbol=symbol.upper(),
            interval=interval,
            time_period=period,
            series_type="close"
        )

        sma_data = data.get("Technical Analysis: SMA", {})
        series = pd.Series({k: float(v["SMA"]) for k, v in sma_data.items()})
        series.index = pd.to_datetime(series.index)
        return series.sort_index()

    async def get_ema(self, symbol: str, period: int = 20, interval: str = "daily") -> pd.Series:
        """Get Exponential Moving Average"""
        data = await self._request(
            function="EMA",
            symbol=symbol.upper(),
            interval=interval,
            time_period=period,
            series_type="close"
        )

        ema_data = data.get("Technical Analysis: EMA", {})
        series = pd.Series({k: float(v["EMA"]) for k, v in ema_data.items()})
        series.index = pd.to_datetime(series.index)
        return series.sort_index()

    async def get_rsi(self, symbol: str, period: int = 14, interval: str = "daily") -> pd.Series:
        """Get Relative Strength Index"""
        data = await self._request(
            function="RSI",
            symbol=symbol.upper(),
            interval=interval,
            time_period=period,
            series_type="close"
        )

        rsi_data = data.get("Technical Analysis: RSI", {})
        series = pd.Series({k: float(v["RSI"]) for k, v in rsi_data.items()})
        series.index = pd.to_datetime(series.index)
        return series.sort_index()

    async def get_macd(self, symbol: str, interval: str = "daily") -> pd.DataFrame:
        """Get MACD (Moving Average Convergence Divergence)"""
        data = await self._request(
            function="MACD",
            symbol=symbol.upper(),
            interval=interval,
            series_type="close"
        )

        macd_data = data.get("Technical Analysis: MACD", {})
        df = pd.DataFrame.from_dict(macd_data, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        return df.sort_index()

    async def get_bbands(self, symbol: str, period: int = 20, interval: str = "daily") -> pd.DataFrame:
        """Get Bollinger Bands"""
        data = await self._request(
            function="BBANDS",
            symbol=symbol.upper(),
            interval=interval,
            time_period=period,
            series_type="close"
        )

        bb_data = data.get("Technical Analysis: BBANDS", {})
        df = pd.DataFrame.from_dict(bb_data, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.astype(float)
        return df.sort_index()

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()
