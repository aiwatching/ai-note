"""
Fundamental Analysis Module

Provides company valuation, financial health, and growth analysis.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import math


class HealthRating(str, Enum):
    """Financial health rating"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class ValuationRating(str, Enum):
    """Valuation rating"""
    SEVERELY_UNDERVALUED = "severely_undervalued"
    UNDERVALUED = "undervalued"
    FAIR_VALUE = "fair_value"
    OVERVALUED = "overvalued"
    SEVERELY_OVERVALUED = "severely_overvalued"


class GrowthRating(str, Enum):
    """Growth rating"""
    HIGH_GROWTH = "high_growth"
    MODERATE_GROWTH = "moderate_growth"
    STABLE = "stable"
    DECLINING = "declining"
    CONTRACTING = "contracting"


@dataclass
class ValuationMetrics:
    """Valuation analysis results"""
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None

    # Fair value estimates
    dcf_value: Optional[float] = None
    graham_number: Optional[float] = None
    peter_lynch_value: Optional[float] = None

    # Comparisons
    sector_pe_avg: Optional[float] = None
    industry_pe_avg: Optional[float] = None

    rating: ValuationRating = ValuationRating.FAIR_VALUE
    score: float = 0.0  # -100 to 100


@dataclass
class FinancialHealth:
    """Financial health analysis"""
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    cash_ratio: Optional[float] = None

    # Profitability
    roe: Optional[float] = None
    roa: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None

    # Efficiency
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None

    rating: HealthRating = HealthRating.FAIR
    score: float = 0.0  # 0 to 100
    concerns: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class GrowthMetrics:
    """Growth analysis results"""
    revenue_growth_yoy: Optional[float] = None
    revenue_growth_3y: Optional[float] = None
    revenue_growth_5y: Optional[float] = None

    earnings_growth_yoy: Optional[float] = None
    earnings_growth_3y: Optional[float] = None
    earnings_growth_5y: Optional[float] = None

    eps_growth_yoy: Optional[float] = None
    dividend_growth_5y: Optional[float] = None

    rating: GrowthRating = GrowthRating.STABLE
    score: float = 0.0  # -100 to 100


@dataclass
class FundamentalSummary:
    """Complete fundamental analysis summary"""
    symbol: str
    company_name: str

    valuation: ValuationMetrics
    financial_health: FinancialHealth
    growth: GrowthMetrics

    # Overall
    overall_score: float  # 0 to 100
    investment_rating: str  # "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"
    key_highlights: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


class FundamentalAnalyzer:
    """
    Fundamental Analysis Engine

    Analyzes company financials to determine:
    - Valuation (P/E, P/B, DCF, etc.)
    - Financial health (liquidity, solvency, profitability)
    - Growth trajectory
    - Investment rating

    Usage:
        analyzer = FundamentalAnalyzer()
        summary = analyzer.analyze(financial_data, company_info)
    """

    # Industry average P/E ratios (simplified)
    SECTOR_PE_AVERAGES = {
        "Technology": 30,
        "Healthcare": 25,
        "Financial Services": 15,
        "Consumer Cyclical": 20,
        "Consumer Defensive": 22,
        "Industrials": 18,
        "Energy": 12,
        "Utilities": 18,
        "Real Estate": 35,
        "Basic Materials": 15,
        "Communication Services": 20,
    }

    # ==================== Valuation Analysis ====================

    def calculate_graham_number(
        self,
        eps: float,
        book_value_per_share: float,
    ) -> Optional[float]:
        """
        Calculate Graham Number (Benjamin Graham's fair value).
        Graham Number = sqrt(22.5 * EPS * Book Value)
        """
        if eps <= 0 or book_value_per_share <= 0:
            return None
        return math.sqrt(22.5 * eps * book_value_per_share)

    def calculate_peter_lynch_value(
        self,
        eps: float,
        growth_rate: float,
        dividend_yield: float = 0,
    ) -> Optional[float]:
        """
        Calculate Peter Lynch fair value.
        Fair P/E = Growth Rate + Dividend Yield
        """
        if eps <= 0 or growth_rate <= 0:
            return None
        fair_pe = growth_rate + dividend_yield
        return eps * fair_pe

    def calculate_dcf_value(
        self,
        free_cash_flow: float,
        growth_rate: float,
        discount_rate: float = 0.10,
        terminal_growth: float = 0.03,
        years: int = 10,
        shares_outstanding: float = 1,
    ) -> Optional[float]:
        """
        Simplified DCF (Discounted Cash Flow) valuation.
        """
        if free_cash_flow <= 0:
            return None

        # Project cash flows
        cash_flows = []
        fcf = free_cash_flow
        for year in range(1, years + 1):
            fcf *= (1 + growth_rate)
            discounted = fcf / ((1 + discount_rate) ** year)
            cash_flows.append(discounted)

        # Terminal value
        terminal_fcf = fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        discounted_terminal = terminal_value / ((1 + discount_rate) ** years)

        total_value = sum(cash_flows) + discounted_terminal
        return total_value / shares_outstanding if shares_outstanding > 0 else None

    def analyze_valuation(
        self,
        current_price: float,
        metrics: Dict[str, Any],
        sector: str = "",
    ) -> ValuationMetrics:
        """Analyze stock valuation"""
        valuation = ValuationMetrics(
            pe_ratio=metrics.get("pe_ratio"),
            pb_ratio=metrics.get("pb_ratio"),
            ps_ratio=metrics.get("ps_ratio"),
            peg_ratio=metrics.get("peg_ratio"),
        )

        # Get sector average P/E
        if sector in self.SECTOR_PE_AVERAGES:
            valuation.sector_pe_avg = self.SECTOR_PE_AVERAGES[sector]

        # Calculate Graham Number
        if metrics.get("eps") and metrics.get("book_value_per_share"):
            valuation.graham_number = self.calculate_graham_number(
                metrics["eps"], metrics["book_value_per_share"]
            )

        # Calculate score based on valuation metrics
        scores = []

        # P/E vs sector
        if valuation.pe_ratio and valuation.sector_pe_avg:
            pe_diff = (valuation.sector_pe_avg - valuation.pe_ratio) / valuation.sector_pe_avg * 50
            scores.append(max(-50, min(50, pe_diff)))

        # PEG ratio
        if valuation.peg_ratio:
            if valuation.peg_ratio < 1:
                scores.append(30)  # Undervalued
            elif valuation.peg_ratio < 1.5:
                scores.append(10)
            elif valuation.peg_ratio < 2:
                scores.append(-10)
            else:
                scores.append(-30)

        # Graham Number comparison
        if valuation.graham_number and current_price:
            graham_upside = (valuation.graham_number - current_price) / current_price * 50
            scores.append(max(-50, min(50, graham_upside)))

        valuation.score = sum(scores) / len(scores) if scores else 0

        # Determine rating
        if valuation.score >= 40:
            valuation.rating = ValuationRating.SEVERELY_UNDERVALUED
        elif valuation.score >= 20:
            valuation.rating = ValuationRating.UNDERVALUED
        elif valuation.score <= -40:
            valuation.rating = ValuationRating.SEVERELY_OVERVALUED
        elif valuation.score <= -20:
            valuation.rating = ValuationRating.OVERVALUED
        else:
            valuation.rating = ValuationRating.FAIR_VALUE

        return valuation

    # ==================== Financial Health ====================

    def analyze_financial_health(self, metrics: Dict[str, Any]) -> FinancialHealth:
        """Analyze financial health"""
        health = FinancialHealth(
            current_ratio=metrics.get("current_ratio"),
            quick_ratio=metrics.get("quick_ratio"),
            debt_to_equity=metrics.get("debt_to_equity"),
            roe=metrics.get("roe"),
            roa=metrics.get("roa"),
            profit_margin=metrics.get("profit_margin"),
            operating_margin=metrics.get("operating_margin"),
        )

        scores = []
        concerns = []
        strengths = []

        # Liquidity Analysis
        if health.current_ratio:
            if health.current_ratio >= 2:
                scores.append(20)
                strengths.append("Strong liquidity (current ratio > 2)")
            elif health.current_ratio >= 1.5:
                scores.append(15)
            elif health.current_ratio >= 1:
                scores.append(10)
            else:
                scores.append(-20)
                concerns.append("Low liquidity (current ratio < 1)")

        # Debt Analysis
        if health.debt_to_equity is not None:
            if health.debt_to_equity < 0.5:
                scores.append(20)
                strengths.append("Low debt levels")
            elif health.debt_to_equity < 1:
                scores.append(10)
            elif health.debt_to_equity < 2:
                scores.append(0)
            else:
                scores.append(-20)
                concerns.append("High debt levels (D/E > 2)")

        # Profitability
        if health.roe:
            if health.roe > 0.20:
                scores.append(20)
                strengths.append("Excellent ROE > 20%")
            elif health.roe > 0.15:
                scores.append(15)
            elif health.roe > 0.10:
                scores.append(10)
            elif health.roe > 0:
                scores.append(5)
            else:
                scores.append(-20)
                concerns.append("Negative ROE")

        if health.profit_margin:
            if health.profit_margin > 0.20:
                scores.append(15)
                strengths.append("High profit margins > 20%")
            elif health.profit_margin > 0.10:
                scores.append(10)
            elif health.profit_margin > 0:
                scores.append(5)
            else:
                scores.append(-15)
                concerns.append("Negative profit margin")

        health.score = sum(scores) / len(scores) * 2 if scores else 50  # Scale to 0-100
        health.score = max(0, min(100, health.score + 50))
        health.concerns = concerns
        health.strengths = strengths

        # Determine rating
        if health.score >= 80:
            health.rating = HealthRating.EXCELLENT
        elif health.score >= 65:
            health.rating = HealthRating.GOOD
        elif health.score >= 50:
            health.rating = HealthRating.FAIR
        elif health.score >= 35:
            health.rating = HealthRating.POOR
        else:
            health.rating = HealthRating.CRITICAL

        return health

    # ==================== Growth Analysis ====================

    def analyze_growth(self, metrics: Dict[str, Any]) -> GrowthMetrics:
        """Analyze growth metrics"""
        growth = GrowthMetrics(
            revenue_growth_yoy=metrics.get("revenue_growth_yoy"),
            earnings_growth_yoy=metrics.get("earnings_growth_yoy"),
            eps_growth_yoy=metrics.get("eps_growth_yoy"),
        )

        scores = []

        # Revenue growth
        if growth.revenue_growth_yoy is not None:
            rg = growth.revenue_growth_yoy * 100  # Convert to percentage
            if rg > 30:
                scores.append(50)
            elif rg > 15:
                scores.append(30)
            elif rg > 5:
                scores.append(10)
            elif rg > 0:
                scores.append(0)
            elif rg > -10:
                scores.append(-20)
            else:
                scores.append(-50)

        # Earnings growth
        if growth.earnings_growth_yoy is not None:
            eg = growth.earnings_growth_yoy * 100
            if eg > 30:
                scores.append(50)
            elif eg > 15:
                scores.append(30)
            elif eg > 5:
                scores.append(10)
            elif eg > 0:
                scores.append(0)
            else:
                scores.append(-30)

        growth.score = sum(scores) / len(scores) if scores else 0

        # Determine rating
        if growth.score >= 40:
            growth.rating = GrowthRating.HIGH_GROWTH
        elif growth.score >= 15:
            growth.rating = GrowthRating.MODERATE_GROWTH
        elif growth.score >= -10:
            growth.rating = GrowthRating.STABLE
        elif growth.score >= -30:
            growth.rating = GrowthRating.DECLINING
        else:
            growth.rating = GrowthRating.CONTRACTING

        return growth

    # ==================== Full Analysis ====================

    def analyze(
        self,
        symbol: str,
        company_name: str,
        current_price: float,
        metrics: Dict[str, Any],
        sector: str = "",
    ) -> FundamentalSummary:
        """
        Perform complete fundamental analysis.

        Args:
            symbol: Stock symbol
            company_name: Company name
            current_price: Current stock price
            metrics: Dictionary with financial metrics
            sector: Company sector

        Returns:
            FundamentalSummary with complete analysis
        """
        valuation = self.analyze_valuation(current_price, metrics, sector)
        health = self.analyze_financial_health(metrics)
        growth = self.analyze_growth(metrics)

        # Calculate overall score
        weights = {"valuation": 0.35, "health": 0.35, "growth": 0.30}

        # Normalize valuation score to 0-100
        val_score = (valuation.score + 50)  # -50 to 50 -> 0 to 100
        growth_score = (growth.score + 50)  # -50 to 50 -> 0 to 100

        overall_score = (
            val_score * weights["valuation"] +
            health.score * weights["health"] +
            growth_score * weights["growth"]
        )

        # Determine investment rating
        if overall_score >= 80:
            rating = "Strong Buy"
        elif overall_score >= 65:
            rating = "Buy"
        elif overall_score >= 45:
            rating = "Hold"
        elif overall_score >= 30:
            rating = "Sell"
        else:
            rating = "Strong Sell"

        # Generate highlights and risks
        highlights = health.strengths.copy()
        risks = health.concerns.copy()

        if valuation.rating in [ValuationRating.UNDERVALUED, ValuationRating.SEVERELY_UNDERVALUED]:
            highlights.append(f"Stock appears {valuation.rating.value}")
        elif valuation.rating in [ValuationRating.OVERVALUED, ValuationRating.SEVERELY_OVERVALUED]:
            risks.append(f"Stock appears {valuation.rating.value}")

        if growth.rating == GrowthRating.HIGH_GROWTH:
            highlights.append("Strong growth trajectory")
        elif growth.rating in [GrowthRating.DECLINING, GrowthRating.CONTRACTING]:
            risks.append(f"Company is {growth.rating.value}")

        return FundamentalSummary(
            symbol=symbol,
            company_name=company_name,
            valuation=valuation,
            financial_health=health,
            growth=growth,
            overall_score=round(overall_score, 1),
            investment_rating=rating,
            key_highlights=highlights,
            risk_factors=risks,
        )
