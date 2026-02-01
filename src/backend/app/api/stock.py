"""
Stock Analysis API Endpoints

REST API for stock analysis, strategies, and portfolio management.
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..stock import (
    StockService,
    OptimizationMethod,
)
from ..config import get_settings


router = APIRouter(prefix="/stock", tags=["stock"])


# ==================== Request/Response Models ====================

class QuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    high: float
    low: float
    open: float
    previous_close: float
    volume: int = 0


class CompanyInfoResponse(BaseModel):
    symbol: str
    name: str
    sector: str = ""
    industry: str = ""
    country: str = ""
    website: Optional[str] = None
    description: str = ""


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    current: dict
    signals: dict
    trend: str


class FundamentalAnalysisResponse(BaseModel):
    symbol: str
    company: str = ""
    rating: str
    score: float
    valuation: dict
    health: dict
    growth: dict
    highlights: List[str] = []
    risks: List[str] = []


class SentimentAnalysisResponse(BaseModel):
    symbol: str
    overall_sentiment: str
    sentiment_score: float
    news_count: int
    bullish_count: int
    bearish_count: int
    keywords: dict = {}


class FullAnalysisResponse(BaseModel):
    symbol: str
    company_name: str = ""
    current_price: float
    change_percent: float
    technical_signal: str
    fundamental_rating: str
    sentiment_level: str
    overall_score: float
    overall_signal: str
    key_insights: List[str] = []


class StrategySignalResponse(BaseModel):
    symbol: str
    signal: str
    strength: float
    price: float
    reason: str
    metadata: dict = {}


class StrategyResultResponse(BaseModel):
    strategy_name: str
    symbols: List[str]
    signals: List[StrategySignalResponse]
    summary: dict


class OptimizationRequest(BaseModel):
    symbols: List[str]
    method: str = "max_sharpe"
    min_weight: float = 0.0
    max_weight: float = 1.0


class OptimizationResponse(BaseModel):
    method: str
    weights: dict
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float


class PortfolioHoldingResponse(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float


class PortfolioSummaryResponse(BaseModel):
    total_value: float
    cash: float
    invested_value: float
    total_pnl: float
    total_pnl_pct: float
    num_positions: int
    holdings: List[PortfolioHoldingResponse] = []


class TradeRequest(BaseModel):
    symbol: str
    quantity: float
    price: Optional[float] = None  # Use current price if not specified
    side: str = "buy"


# ==================== Service Dependency ====================

_stock_service: Optional[StockService] = None


async def get_stock_service() -> StockService:
    """Get or create stock service instance"""
    global _stock_service
    if _stock_service is None:
        settings = get_settings()
        _stock_service = StockService(
            alphavantage_key=getattr(settings, "alpha_vantage_key", None),
            finnhub_key=getattr(settings, "finnhub_key", None),
        )
    return _stock_service


# ==================== Quote & Data Endpoints ====================

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    service: StockService = Depends(get_stock_service),
):
    """Get current stock quote"""
    try:
        quote = await service.get_quote(symbol.upper())
        return QuoteResponse(
            symbol=quote.symbol,
            price=quote.price,
            change=quote.change,
            change_percent=quote.change_percent,
            high=quote.high,
            low=quote.low,
            open=quote.open,
            previous_close=quote.previous_close,
            volume=quote.volume,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/company/{symbol}", response_model=CompanyInfoResponse)
async def get_company_info(
    symbol: str,
    service: StockService = Depends(get_stock_service),
):
    """Get company information"""
    try:
        info = await service.get_company_info(symbol.upper())
        return CompanyInfoResponse(
            symbol=info.symbol,
            name=info.name,
            sector=info.sector,
            industry=info.industry,
            country=info.country,
            website=info.website,
            description=info.description,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    days: int = Query(default=365, ge=1, le=3650),
    service: StockService = Depends(get_stock_service),
):
    """Get historical price data"""
    try:
        df = await service.get_history(symbol.upper(), days=days)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data available")

        # Convert to list of dicts
        df_reset = df.reset_index()
        df_reset.columns = ["date" if c == df.index.name else c for c in df_reset.columns]

        return {
            "symbol": symbol.upper(),
            "count": len(df),
            "data": df_reset.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    service: StockService = Depends(get_stock_service),
):
    """Search for stocks by name or symbol"""
    results = await service.search_stocks(q, limit)
    return {"query": q, "results": results}


@router.get("/news/{symbol}")
async def get_news(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
    service: StockService = Depends(get_stock_service),
):
    """Get news for a stock"""
    news = await service.get_news(symbol.upper(), limit)
    return {
        "symbol": symbol.upper(),
        "count": len(news),
        "news": [
            {
                "title": n.title,
                "summary": n.summary,
                "source": n.source,
                "published": n.published.isoformat() if n.published else None,
                "url": n.url,
            }
            for n in news
        ],
    }


# ==================== Analysis Endpoints ====================

@router.get("/analysis/technical/{symbol}", response_model=TechnicalAnalysisResponse)
async def analyze_technical(
    symbol: str,
    days: int = Query(default=365, ge=30, le=3650),
    service: StockService = Depends(get_stock_service),
):
    """Perform technical analysis"""
    result = await service.analyze_technical(symbol.upper(), days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TechnicalAnalysisResponse(**result)


@router.get("/analysis/fundamental/{symbol}", response_model=FundamentalAnalysisResponse)
async def analyze_fundamental(
    symbol: str,
    service: StockService = Depends(get_stock_service),
):
    """Perform fundamental analysis"""
    result = await service.analyze_fundamental(symbol.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return FundamentalAnalysisResponse(**result)


@router.get("/analysis/sentiment/{symbol}", response_model=SentimentAnalysisResponse)
async def analyze_sentiment(
    symbol: str,
    service: StockService = Depends(get_stock_service),
):
    """Perform sentiment analysis"""
    result = await service.analyze_sentiment(symbol.upper())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SentimentAnalysisResponse(**result)


@router.get("/analysis/full/{symbol}", response_model=FullAnalysisResponse)
async def analyze_full(
    symbol: str,
    service: StockService = Depends(get_stock_service),
):
    """Perform comprehensive analysis (technical + fundamental + sentiment)"""
    result = await service.analyze_stock(symbol.upper())
    return FullAnalysisResponse(
        symbol=result.symbol,
        company_name=result.company_name,
        current_price=result.current_price,
        change_percent=result.change_percent,
        technical_signal=result.technical_signal,
        fundamental_rating=result.fundamental_rating,
        sentiment_level=result.sentiment_level,
        overall_score=result.overall_score,
        overall_signal=result.overall_signal,
        key_insights=result.key_insights,
    )


# ==================== Strategy Endpoints ====================

@router.get("/strategy/list")
async def list_strategies(
    service: StockService = Depends(get_stock_service),
):
    """List available strategies"""
    return {
        "strategies": [
            {
                "name": name,
                "description": strategy.description,
            }
            for name, strategy in service.strategies.items()
        ]
    }


@router.post("/strategy/run/{strategy_name}", response_model=StrategyResultResponse)
async def run_strategy(
    strategy_name: str,
    symbols: List[str],
    service: StockService = Depends(get_stock_service),
):
    """Run a quantitative strategy on given symbols"""
    if strategy_name not in service.strategies:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_name}")

    symbols = [s.upper() for s in symbols]
    result = await service.run_strategy(strategy_name, symbols)

    return StrategyResultResponse(
        strategy_name=result.strategy_name,
        symbols=result.symbols,
        signals=[
            StrategySignalResponse(
                symbol=s.symbol,
                signal=s.signal_type.value,
                strength=s.strength,
                price=s.price,
                reason=s.reason,
                metadata=s.metadata,
            )
            for s in result.signals
        ],
        summary=result.summary,
    )


@router.post("/strategy/screen", response_model=List[dict])
async def screen_stocks(
    symbols: List[str],
    strategy: str = Query(default="multi_factor"),
    top_n: int = Query(default=10, ge=1, le=100),
    service: StockService = Depends(get_stock_service),
):
    """Screen stocks using a strategy and return top picks"""
    symbols = [s.upper() for s in symbols]
    return await service.screen_stocks(symbols, strategy, top_n)


# ==================== Portfolio Endpoints ====================

@router.post("/portfolio/optimize", response_model=OptimizationResponse)
async def optimize_portfolio(
    request: OptimizationRequest,
    service: StockService = Depends(get_stock_service),
):
    """Optimize portfolio allocation"""
    method_map = {
        "max_sharpe": OptimizationMethod.MAX_SHARPE,
        "min_variance": OptimizationMethod.MIN_VARIANCE,
        "risk_parity": OptimizationMethod.RISK_PARITY,
        "equal_weight": OptimizationMethod.EQUAL_WEIGHT,
    }

    method = method_map.get(request.method.lower(), OptimizationMethod.MAX_SHARPE)
    symbols = [s.upper() for s in request.symbols]

    result = await service.optimize_portfolio(
        symbols,
        method=method,
        constraints={"min_weight": request.min_weight, "max_weight": request.max_weight},
    )

    return OptimizationResponse(
        method=result.method,
        weights=result.weights,
        expected_return=result.expected_return,
        expected_volatility=result.expected_volatility,
        sharpe_ratio=result.sharpe_ratio,
    )


@router.get("/portfolio/{name}", response_model=PortfolioSummaryResponse)
async def get_portfolio(
    name: str = "main",
    service: StockService = Depends(get_stock_service),
):
    """Get portfolio summary"""
    portfolio = service.get_portfolio(name)

    # Get current prices
    prices = {}
    for symbol in portfolio.holdings:
        try:
            quote = await service.get_quote(symbol)
            prices[symbol] = quote.price
        except Exception:
            pass

    summary = portfolio.get_summary(prices)

    return PortfolioSummaryResponse(
        total_value=summary.total_value,
        cash=summary.cash,
        invested_value=summary.invested_value,
        total_pnl=summary.total_pnl,
        total_pnl_pct=summary.total_pnl_pct,
        num_positions=summary.num_positions,
        holdings=[
            PortfolioHoldingResponse(
                symbol=h.symbol,
                quantity=h.quantity,
                avg_cost=h.avg_cost,
                current_price=h.current_price,
                market_value=h.market_value,
                unrealized_pnl=h.unrealized_pnl,
                unrealized_pnl_pct=h.unrealized_pnl_pct,
                weight=h.weight,
            )
            for h in portfolio.holdings.values()
        ],
    )


@router.post("/portfolio/{name}/trade")
async def execute_trade(
    name: str,
    trade: TradeRequest,
    service: StockService = Depends(get_stock_service),
):
    """Execute a trade (paper trading)"""
    portfolio = service.get_portfolio(name)
    symbol = trade.symbol.upper()

    # Get current price if not specified
    price = trade.price
    if price is None:
        quote = await service.get_quote(symbol)
        price = quote.price

    if trade.side.lower() == "buy":
        result = portfolio.add_position(symbol, trade.quantity, price)
    else:
        result = portfolio.reduce_position(symbol, trade.quantity, price)
        if result is None:
            raise HTTPException(status_code=400, detail="Position not found")

    return {
        "success": True,
        "trade": {
            "symbol": result.symbol,
            "side": result.side,
            "quantity": result.quantity,
            "price": result.price,
            "commission": result.commission,
        },
        "portfolio_cash": portfolio.cash,
    }


@router.get("/portfolio/{name}/risk")
async def get_portfolio_risk(
    name: str = "main",
    benchmark: str = Query(default="SPY"),
    service: StockService = Depends(get_stock_service),
):
    """Get portfolio risk metrics"""
    portfolio = service.get_portfolio(name)

    if not portfolio.holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings")

    metrics = await service.calculate_portfolio_risk(portfolio, benchmark)

    return {
        "volatility": {
            "daily": round(metrics.daily_volatility * 100, 2),
            "annualized": round(metrics.annualized_volatility * 100, 2),
        },
        "var": {
            "var_95": round(metrics.var_95 * 100, 2),
            "var_99": round(metrics.var_99 * 100, 2),
            "cvar_95": round(metrics.cvar_95 * 100, 2),
        },
        "drawdown": {
            "max": round(metrics.max_drawdown * 100, 2),
            "current": round(metrics.current_drawdown * 100, 2),
        },
        "beta": metrics.beta,
        "correlation": metrics.correlation,
        "concentration": {
            "herfindahl": round(metrics.herfindahl_index, 4),
            "top_3": round(metrics.top_3_concentration * 100, 2),
        },
        "risk_score": metrics.overall_risk_score,
        "risk_level": metrics.risk_level,
    }
