"""
Stock Analysis Service

Main service that coordinates all stock analysis components:
- Data providers (YFinance, Alpha Vantage, Finnhub)
- Technical analysis
- Fundamental analysis
- Sentiment analysis
- Quantitative strategies
- Portfolio management
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import pandas as pd

from .providers.base import Quote, CompanyInfo, FinancialData, NewsItem, Interval
from .providers import (
    YFinanceProvider,
    AlphaVantageProvider,
    FinnhubProvider,
)
from .analysis import (
    TechnicalAnalyzer,
    FundamentalAnalyzer,
    SentimentAnalyzer,
)
from .strategies import (
    Strategy,
    StrategyResult,
    MomentumStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MultiFactorStrategy,
)
from .portfolio import (
    Portfolio,
    PortfolioManager,
    RiskManager,
    RiskMetrics,
    PositionSizer,
    PortfolioOptimizer,
    OptimizationMethod,
    OptimizationResult,
)


logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Combined analysis result for a stock"""
    symbol: str
    company_name: str = ""
    current_price: float = 0.0
    change_percent: float = 0.0

    # Analysis summaries
    technical_summary: Dict = field(default_factory=dict)
    fundamental_summary: Dict = field(default_factory=dict)
    sentiment_summary: Dict = field(default_factory=dict)

    # Signals
    technical_signal: str = "neutral"
    fundamental_rating: str = "hold"
    sentiment_level: str = "neutral"

    # Overall
    overall_score: float = 0.0
    overall_signal: str = "hold"
    key_insights: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)


class StockService:
    """
    Stock Analysis Service

    Provides a unified interface for all stock analysis:
    - Real-time quotes and market data
    - Technical analysis (indicators, signals)
    - Fundamental analysis (valuation, financials)
    - Sentiment analysis (news, social)
    - Quantitative strategies
    - Portfolio management and optimization

    Usage:
        service = StockService()
        await service.initialize()

        # Get quote
        quote = await service.get_quote("AAPL")

        # Full analysis
        analysis = await service.analyze_stock("AAPL")

        # Run strategy
        signals = await service.run_strategy("momentum", ["AAPL", "MSFT"])

        # Optimize portfolio
        result = await service.optimize_portfolio(["AAPL", "MSFT", "GOOG"])
    """

    def __init__(
        self,
        alphavantage_key: Optional[str] = None,
        finnhub_key: Optional[str] = None,
    ):
        # Initialize providers
        self.yfinance = YFinanceProvider()
        self.alphavantage = AlphaVantageProvider(api_key=alphavantage_key) if alphavantage_key else None
        self.finnhub = FinnhubProvider(api_key=finnhub_key) if finnhub_key else None

        # Primary provider (fallback order)
        self.primary_provider = self.yfinance

        # Initialize analyzers
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Initialize strategies
        self.strategies: Dict[str, Strategy] = {
            "momentum": MomentumStrategy(),
            "trend_following": TrendFollowingStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "multi_factor": MultiFactorStrategy(),
        }

        # Portfolio components
        self.portfolio_manager = PortfolioManager()
        self.risk_manager = RiskManager()
        self.position_sizer = PositionSizer()
        self.portfolio_optimizer = PortfolioOptimizer()

        # Data cache
        self._price_cache: Dict[str, pd.DataFrame] = {}
        self._quote_cache: Dict[str, tuple] = {}  # (Quote, timestamp)
        self._cache_ttl = 60  # seconds

        logger.info("StockService initialized")

    # ==================== Data Methods ====================

    async def get_quote(self, symbol: str, use_cache: bool = True) -> Quote:
        """Get current stock quote"""
        # Check cache
        if use_cache and symbol in self._quote_cache:
            quote, cached_at = self._quote_cache[symbol]
            if (datetime.now() - cached_at).seconds < self._cache_ttl:
                return quote

        # Try providers in order
        providers = [self.yfinance]
        if self.finnhub:
            providers.insert(0, self.finnhub)

        for provider in providers:
            try:
                quote = await provider.get_quote(symbol)
                self._quote_cache[symbol] = (quote, datetime.now())
                return quote
            except Exception as e:
                logger.debug(f"Provider {provider.name} failed for {symbol}: {e}")
                continue

        raise ValueError(f"Could not get quote for {symbol}")

    async def get_history(
        self,
        symbol: str,
        days: int = 365,
        interval: Interval = Interval.DAY_1,
    ) -> pd.DataFrame:
        """Get historical price data"""
        end = date.today()
        start = end - timedelta(days=days)

        # Try yfinance first (free, no limits)
        try:
            df = await self.yfinance.get_history(symbol, start, end, interval)
            if df is not None and len(df) > 0:
                self._price_cache[symbol] = df
                return df
        except Exception as e:
            logger.debug(f"YFinance history failed: {e}")

        # Try Alpha Vantage
        if self.alphavantage:
            try:
                df = await self.alphavantage.get_history(symbol, start, end, interval)
                if df is not None and len(df) > 0:
                    self._price_cache[symbol] = df
                    return df
            except Exception as e:
                logger.debug(f"Alpha Vantage history failed: {e}")

        # Try Finnhub
        if self.finnhub:
            try:
                df = await self.finnhub.get_history(symbol, start, end, interval)
                if df is not None and len(df) > 0:
                    self._price_cache[symbol] = df
                    return df
            except Exception as e:
                logger.debug(f"Finnhub history failed: {e}")

        return pd.DataFrame()

    async def get_company_info(self, symbol: str) -> CompanyInfo:
        """Get company information"""
        providers = [self.yfinance]
        if self.finnhub:
            providers.append(self.finnhub)

        for provider in providers:
            try:
                return await provider.get_company_info(symbol)
            except Exception:
                continue

        raise ValueError(f"Could not get company info for {symbol}")

    async def get_financials(self, symbol: str) -> List[FinancialData]:
        """Get financial data"""
        # Try Finnhub first (better metrics)
        if self.finnhub:
            try:
                financials = await self.finnhub.get_financials(symbol)
                if financials:
                    return financials
            except Exception:
                pass

        # Fallback to yfinance
        try:
            return await self.yfinance.get_financials(symbol)
        except Exception:
            return []

    async def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        """Get news for a stock"""
        news = []

        # Try Finnhub
        if self.finnhub:
            try:
                news = await self.finnhub.get_news(symbol, limit)
            except Exception:
                pass

        # Fallback to yfinance
        if not news:
            try:
                news = await self.yfinance.get_news(symbol, limit)
            except Exception:
                pass

        return news[:limit]

    async def search_stocks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for stocks"""
        if self.finnhub:
            try:
                return await self.finnhub.search(query, limit)
            except Exception:
                pass

        try:
            return await self.yfinance.search(query, limit)
        except Exception:
            return []

    # ==================== Analysis Methods ====================

    async def analyze_technical(
        self,
        symbol: str,
        days: int = 365,
    ) -> Dict:
        """Perform technical analysis"""
        df = await self.get_history(symbol, days)
        if df.empty:
            return {"error": "No data available"}

        # Calculate indicators
        indicators = self.technical_analyzer.calculate_all_indicators(df)

        # Generate signals
        signals = self.technical_analyzer.generate_signals(indicators)

        # Get current values
        current = {
            "price": float(df["Close"].iloc[-1]),
            "sma_20": float(indicators["sma_20"].iloc[-1]) if "sma_20" in indicators else None,
            "sma_50": float(indicators["sma_50"].iloc[-1]) if "sma_50" in indicators else None,
            "rsi": float(indicators["rsi"].iloc[-1]) if "rsi" in indicators else None,
            "macd": float(indicators["macd"].iloc[-1]) if "macd" in indicators else None,
        }

        return {
            "symbol": symbol,
            "current": current,
            "signals": signals,
            "trend": "bullish" if signals.get("trend_score", 0) > 0.5 else "bearish" if signals.get("trend_score", 0) < -0.5 else "neutral",
        }

    async def analyze_fundamental(
        self,
        symbol: str,
    ) -> Dict:
        """Perform fundamental analysis"""
        try:
            company = await self.get_company_info(symbol)
            financials = await self.get_financials(symbol)
            quote = await self.get_quote(symbol)

            if not financials:
                return {"error": "No financial data available"}

            # Build metrics dict from latest financials
            metrics = {}
            latest = financials[0]
            for field_name in [
                "pe_ratio", "pb_ratio", "ps_ratio", "peg_ratio",
                "roe", "roa", "profit_margin", "operating_margin",
                "current_ratio", "quick_ratio", "debt_to_equity",
                "eps", "revenue", "book_value_per_share",
            ]:
                value = getattr(latest, field_name, None)
                if value is not None:
                    metrics[field_name] = value

            # Run analysis
            summary = self.fundamental_analyzer.analyze(
                symbol=symbol,
                company_name=company.name,
                current_price=quote.price,
                metrics=metrics,
                sector=company.sector,
            )

            return {
                "symbol": symbol,
                "company": company.name,
                "rating": summary.investment_rating,
                "score": summary.overall_score,
                "valuation": {
                    "rating": summary.valuation.rating.value,
                    "pe_ratio": summary.valuation.pe_ratio,
                    "graham_number": summary.valuation.graham_number,
                },
                "health": {
                    "rating": summary.financial_health.rating.value,
                    "score": summary.financial_health.score,
                    "strengths": summary.financial_health.strengths,
                    "concerns": summary.financial_health.concerns,
                },
                "growth": {
                    "rating": summary.growth.rating.value,
                },
                "highlights": summary.key_highlights,
                "risks": summary.risk_factors,
            }

        except Exception as e:
            logger.error(f"Fundamental analysis error: {e}")
            return {"error": str(e)}

    async def analyze_sentiment(
        self,
        symbol: str,
        llm_service: Optional[Any] = None,
    ) -> Dict:
        """Perform sentiment analysis"""
        news = await self.get_news(symbol, 20)

        if not news:
            return {"error": "No news available"}

        # Convert to dicts
        news_items = [
            {
                "title": n.title,
                "summary": n.summary,
                "source": n.source,
                "published": n.published.isoformat() if n.published else None,
                "url": n.url,
            }
            for n in news
        ]

        # Run analysis
        if llm_service:
            summary = await self.sentiment_analyzer.analyze_with_llm(
                news_items, llm_service, symbol
            )
        else:
            summary = self.sentiment_analyzer.analyze_news(news_items, symbol)

        return {
            "symbol": symbol,
            "overall_sentiment": summary.overall_sentiment.value,
            "sentiment_score": summary.sentiment_score,
            "news_count": summary.news_count,
            "bullish_count": summary.bullish_count,
            "bearish_count": summary.bearish_count,
            "keywords": summary.keywords,
            "top_bullish": [
                {"title": n.title, "score": n.sentiment_score}
                for n in summary.top_bullish_news
            ],
            "top_bearish": [
                {"title": n.title, "score": n.sentiment_score}
                for n in summary.top_bearish_news
            ],
        }

    async def analyze_stock(
        self,
        symbol: str,
        include_sentiment: bool = True,
        llm_service: Optional[Any] = None,
    ) -> AnalysisResult:
        """
        Perform comprehensive stock analysis.

        Combines technical, fundamental, and sentiment analysis.
        """
        result = AnalysisResult(symbol=symbol)

        # Get basic info
        try:
            quote = await self.get_quote(symbol)
            result.current_price = quote.price
            result.change_percent = quote.change_percent

            company = await self.get_company_info(symbol)
            result.company_name = company.name
        except Exception as e:
            logger.error(f"Basic info error: {e}")

        # Technical analysis
        try:
            tech = await self.analyze_technical(symbol)
            result.technical_summary = tech
            result.technical_signal = tech.get("trend", "neutral")
        except Exception as e:
            logger.error(f"Technical analysis error: {e}")

        # Fundamental analysis
        try:
            fund = await self.analyze_fundamental(symbol)
            result.fundamental_summary = fund
            result.fundamental_rating = fund.get("rating", "hold")
        except Exception as e:
            logger.error(f"Fundamental analysis error: {e}")

        # Sentiment analysis
        if include_sentiment:
            try:
                sent = await self.analyze_sentiment(symbol, llm_service)
                result.sentiment_summary = sent
                result.sentiment_level = sent.get("overall_sentiment", "neutral")
            except Exception as e:
                logger.error(f"Sentiment analysis error: {e}")

        # Calculate overall score
        scores = []
        insights = []

        # Technical score
        tech_signals = result.technical_summary.get("signals", {})
        tech_score = tech_signals.get("trend_score", 0)
        scores.append(tech_score * 100)

        if result.technical_signal == "bullish":
            insights.append("Technical indicators are bullish")
        elif result.technical_signal == "bearish":
            insights.append("Technical indicators are bearish")

        # Fundamental score
        fund_score = result.fundamental_summary.get("score", 50)
        scores.append(fund_score)

        if "highlights" in result.fundamental_summary:
            insights.extend(result.fundamental_summary["highlights"][:2])

        # Sentiment score
        sent_score = result.sentiment_summary.get("sentiment_score", 0)
        scores.append((sent_score + 1) * 50)  # -1 to 1 -> 0 to 100

        if result.sentiment_level in ["very_bullish", "bullish"]:
            insights.append(f"Market sentiment is {result.sentiment_level}")
        elif result.sentiment_level in ["very_bearish", "bearish"]:
            insights.append(f"Market sentiment is {result.sentiment_level}")

        # Overall
        result.overall_score = sum(scores) / len(scores) if scores else 50
        result.key_insights = insights[:5]

        # Overall signal
        if result.overall_score >= 70:
            result.overall_signal = "strong_buy"
        elif result.overall_score >= 60:
            result.overall_signal = "buy"
        elif result.overall_score <= 30:
            result.overall_signal = "strong_sell"
        elif result.overall_score <= 40:
            result.overall_signal = "sell"
        else:
            result.overall_signal = "hold"

        return result

    # ==================== Strategy Methods ====================

    async def run_strategy(
        self,
        strategy_name: str,
        symbols: List[str],
        params: Optional[Dict] = None,
    ) -> StrategyResult:
        """Run a quantitative strategy"""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy = self.strategies[strategy_name]
        if params:
            strategy.params.update(params)

        # Get data for all symbols
        data = {}
        for symbol in symbols:
            df = await self.get_history(symbol, days=365)
            if not df.empty:
                data[symbol] = df

        return strategy.analyze(data, symbols)

    async def screen_stocks(
        self,
        symbols: List[str],
        strategy: str = "multi_factor",
        top_n: int = 10,
    ) -> List[Dict]:
        """Screen stocks using a strategy"""
        result = await self.run_strategy(strategy, symbols)

        # Sort by signal strength
        buy_signals = [
            s for s in result.signals
            if s.signal_type.value in ["strong_buy", "buy"]
        ]
        buy_signals.sort(key=lambda x: x.strength, reverse=True)

        return [
            {
                "symbol": s.symbol,
                "signal": s.signal_type.value,
                "strength": round(s.strength, 3),
                "price": s.price,
                "reason": s.reason,
            }
            for s in buy_signals[:top_n]
        ]

    # ==================== Portfolio Methods ====================

    def get_portfolio(self, name: str = "main") -> Portfolio:
        """Get or create a portfolio"""
        return self.portfolio_manager.get_or_create_portfolio(name)

    async def optimize_portfolio(
        self,
        symbols: List[str],
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        constraints: Optional[Dict] = None,
    ) -> OptimizationResult:
        """Optimize portfolio allocation"""
        # Get price data
        price_data = {}
        for symbol in symbols:
            df = await self.get_history(symbol, days=365)
            if not df.empty:
                price_data[symbol] = df

        return self.portfolio_optimizer.optimize(price_data, method, constraints)

    async def calculate_portfolio_risk(
        self,
        portfolio: Portfolio,
        benchmark_symbol: str = "SPY",
    ) -> RiskMetrics:
        """Calculate portfolio risk metrics"""
        # Get price data for holdings
        price_data = {}
        prices = {}

        for symbol in portfolio.holdings:
            df = await self.get_history(symbol, days=365)
            if not df.empty:
                price_data[symbol] = df
                prices[symbol] = df["Close"].iloc[-1]

        # Get benchmark data
        benchmark_data = await self.get_history(benchmark_symbol, days=365)

        # Update portfolio with current prices
        portfolio.update_prices(prices)
        weights = portfolio.get_weights(prices)

        return self.risk_manager.calculate_risk_metrics(
            price_data, weights, benchmark_data
        )

    def calculate_position_size(
        self,
        portfolio: Portfolio,
        symbol: str,
        price: float,
        method: str = "fixed",
        **kwargs,
    ) -> int:
        """Calculate position size for a trade"""
        total_value = portfolio.get_total_value()

        return self.position_sizer.calculate_position_size(
            method=method,
            portfolio_value=total_value,
            price=price,
            **kwargs,
        )

    # ==================== Cleanup ====================

    async def close(self):
        """Close all provider connections"""
        if self.finnhub:
            await self.finnhub.close()
        logger.info("StockService closed")
