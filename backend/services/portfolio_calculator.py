from __future__ import annotations

from collections import defaultdict
from typing import Any

try:
    from ..schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from ..symbols import detect_market
except ImportError:
    from schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from symbols import detect_market


TECH_KEYWORDS = {
    "technology",
    "semiconductor",
    "electronics",
    "software",
    "cloud",
    "ai",
    "chip",
    "foundry",
    "server",
    "allianz taiwan technology fund",
    "00881",
    "00922",
}
DEFENSIVE_KEYWORDS = {
    "defensive",
    "bond",
    "cash",
    "treasury",
    "income",
    "high dividend",
    "utility",
    "consumer staples",
}
LONG_DURATION_KEYWORDS = {
    "20 year",
    "20-year",
    "long duration",
    "long treasury",
    "美債",
    "bond",
    "00687b",
}


def round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def classify_theme(
    holding: HoldingInput,
    sector: str | None = None,
    category: str | None = None,
) -> str:
    text = " ".join(
        filter(
            None,
            [
                holding.ticker,
                holding.name or "",
                holding.asset_type or "",
                category or holding.category or "",
                sector or "",
                holding.notes or "",
            ],
        )
    ).lower()
    if any(keyword in text for keyword in TECH_KEYWORDS):
        return "Technology / AI"
    if any(keyword in text for keyword in LONG_DURATION_KEYWORDS):
        return "Bond / Rate-sensitive"
    if any(keyword in text for keyword in DEFENSIVE_KEYWORDS):
        return "Defensive / Income"
    if "financial" in text or "bank" in text:
        return "Financials"
    if "health" in text or "medical" in text or "biotech" in text:
        return "Healthcare"
    if "industrial" in text or "auto" in text or "manufacturing" in text:
        return "Industrials / Auto"
    return "General Equity"


def estimate_dividend(
    current_value: float | None,
    shares: float | None,
    annual_dividend_per_share: float | None = None,
    dividend_yield: float | None = None,
) -> tuple[float | None, float | None]:
    annual: float | None = None
    if shares is not None and annual_dividend_per_share is not None:
        annual = shares * annual_dividend_per_share
    elif current_value is not None and dividend_yield is not None:
        annual = current_value * dividend_yield

    if annual is None:
        return None, None
    return round2(annual), round2(annual / 12)


def calculate_holding_metrics(
    holding: HoldingInput,
    total_value: float,
    *,
    sector: str | None = None,
    theme: str | None = None,
    dividend_yield: float | None = None,
    annual_dividend_per_share: float | None = None,
) -> HoldingMetrics:
    current_price = holding.current_price
    shares = holding.shares
    current_value = holding.current_value
    missing_data: list[str] = []

    if current_value is None and current_price is not None and shares is not None:
        current_value = current_price * shares
    elif shares is None and current_value is not None and current_price not in {None, 0}:
        shares = current_value / current_price

    cost_basis: float | None = None
    if holding.avg_cost is not None and shares is not None:
        cost_basis = holding.avg_cost * shares
    else:
        missing_data.append("Missing average cost or shares for cost basis.")

    if current_value is None:
        missing_data.append("Missing current value and price/shares.")

    unrealized_gain_loss = (
        None if cost_basis is None or current_value is None else current_value - cost_basis
    )
    return_pct = (
        None
        if unrealized_gain_loss is None or not cost_basis
        else (unrealized_gain_loss / cost_basis) * 100
    )
    weight_pct = (current_value / total_value * 100) if total_value and current_value else None
    annual_dividend, monthly_dividend = estimate_dividend(
        current_value,
        shares,
        annual_dividend_per_share=annual_dividend_per_share,
        dividend_yield=dividend_yield,
    )
    market = detect_market(holding.ticker) if holding.ticker else None

    return HoldingMetrics(
        ticker=holding.ticker,
        name=holding.name,
        cost_basis=round2(cost_basis),
        current_value=round2(current_value),
        unrealized_gain_loss=round2(unrealized_gain_loss),
        return_pct=round2(return_pct),
        portfolio_weight_pct=round2(weight_pct),
        estimated_annual_dividend=annual_dividend,
        estimated_monthly_dividend=monthly_dividend,
        current_price=round2(current_price),
        shares=round2(shares),
        category=holding.category,
        asset_type=holding.asset_type,
        sector=sector,
        theme=theme,
        market=market,
        notes=holding.notes,
        missing_data=missing_data,
    )


def compute_exposure(holdings: list[HoldingMetrics], field: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    total_value = sum(metric.current_value or 0 for metric in holdings)
    if total_value <= 0:
        return {}

    for metric in holdings:
        current_value = metric.current_value or 0
        if current_value <= 0:
            continue
        key = getattr(metric, field, None) or "Unclassified"
        totals[str(key)] += current_value

    return {
        key: round(value / total_value * 100, 2)
        for key, value in sorted(totals.items())
    }


def detect_risk_flags(holdings: list[HoldingMetrics]) -> list[str]:
    flags: list[str] = []
    if not holdings:
        return flags

    highest_weight = max((metric.portfolio_weight_pct or 0) for metric in holdings)
    if highest_weight > 25:
        flags.append(
            "Single-position concentration is high. "
            "At least one holding exceeds 25% of the portfolio."
        )

    tech_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme == "Technology / AI"
    )
    if tech_weight > 60:
        flags.append(
            "Technology / AI exposure exceeds 60% and may increase cyclical volatility."
        )

    defensive_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme in {"Defensive / Income", "Bond / Rate-sensitive"}
    )
    if defensive_weight < 10:
        flags.append(
            "Defensive allocation is below 10%, so the portfolio may have limited ballast."
        )

    large_losers = [
        metric.ticker
        for metric in holdings
        if (metric.return_pct or 0) <= -30
    ]
    if large_losers:
        flags.append(
            "One or more holdings have unrealized losses worse than -30%: "
            + ", ".join(sorted(large_losers))
        )

    duration_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme == "Bond / Rate-sensitive"
    )
    if duration_weight > 20:
        flags.append(
            "Long-duration bond exposure is meaningful and remains sensitive to rate moves."
        )

    total_dividends = sum(metric.estimated_annual_dividend or 0 for metric in holdings)
    if total_dividends > 0:
        leading_income = max(
            (
                (metric.estimated_annual_dividend or 0, metric.ticker)
                for metric in holdings
            ),
            default=(0.0, ""),
        )
        if leading_income[0] / total_dividends > 0.5:
            flags.append(
                f"Dividend income depends heavily on {leading_income[1]}."
            )

    return flags


def compute_risk_attribution(holdings: list[HoldingMetrics]) -> dict[str, float]:
    if not holdings:
        return {}

    top_weight = max((metric.portfolio_weight_pct or 0) for metric in holdings)
    tech_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme == "Technology / AI"
    )
    defensive_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme in {"Defensive / Income", "Bond / Rate-sensitive"}
    )
    duration_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme == "Bond / Rate-sensitive"
    )
    loss_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if (metric.return_pct or 0) <= -30
    )
    total_dividends = sum(metric.estimated_annual_dividend or 0 for metric in holdings)
    leading_dividend = max(
        (metric.estimated_annual_dividend or 0 for metric in holdings),
        default=0.0,
    )
    dividend_concentration = (
        leading_dividend / total_dividends * 100 if total_dividends else 0.0
    )

    raw = {
        "single_position_concentration": max(top_weight - 20, 0),
        "technology_theme_exposure": max(tech_weight - 40, 0),
        "defensive_allocation_gap": max(10 - defensive_weight, 0) * 2,
        "large_unrealized_loss_exposure": loss_weight,
        "duration_rate_sensitivity": max(duration_weight - 10, 0),
        "dividend_source_concentration": max(dividend_concentration - 40, 0),
    }
    total = sum(raw.values())
    if total <= 0:
        return {key: 0.0 for key in raw}
    return {key: round(value / total * 100, 2) for key, value in raw.items()}


def compute_health_scores(holdings: list[HoldingMetrics]) -> dict[str, int]:
    if not holdings:
        return {
            "overall_score": 0,
            "diversification_score": 0,
            "concentration_score": 0,
            "income_score": 0,
            "defensive_score": 0,
            "growth_score": 0,
        }

    count = len([metric for metric in holdings if (metric.current_value or 0) > 0])
    top_weight = max((metric.portfolio_weight_pct or 0) for metric in holdings)
    tech_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme == "Technology / AI"
    )
    defensive_weight = sum(
        metric.portfolio_weight_pct or 0
        for metric in holdings
        if metric.theme in {"Defensive / Income", "Bond / Rate-sensitive"}
    )
    annual_dividend = sum(metric.estimated_annual_dividend or 0 for metric in holdings)
    current_value = sum(metric.current_value or 0 for metric in holdings)

    diversification_score = max(
        0,
        min(100, int(35 + min(count, 8) * 6 - max(top_weight - 20, 0) * 1.2)),
    )
    concentration_score = max(
        0,
        min(100, int(100 - max(top_weight - 10, 0) * 2.2)),
    )
    income_yield = (annual_dividend / current_value * 100) if current_value else 0.0
    income_score = max(0, min(100, int(25 + income_yield * 10)))
    defensive_score = max(0, min(100, int(min(defensive_weight, 25) * 4)))
    growth_score = max(0, min(100, int(60 - abs(tech_weight - 35) * 1.1)))
    overall_score = int(
        round(
            diversification_score * 0.2
            + concentration_score * 0.25
            + income_score * 0.15
            + defensive_score * 0.2
            + growth_score * 0.2
        )
    )

    return {
        "overall_score": overall_score,
        "diversification_score": diversification_score,
        "concentration_score": concentration_score,
        "income_score": income_score,
        "defensive_score": defensive_score,
        "growth_score": growth_score,
    }


def _build_summary(
    request: PortfolioRequest,
    holdings: list[HoldingMetrics],
    risk_flags: list[str],
) -> tuple[str, list[str]]:
    total_value = round2(sum(metric.current_value or 0 for metric in holdings)) or 0.0
    total_return = round2(sum(metric.unrealized_gain_loss or 0 for metric in holdings)) or 0.0
    winners = [metric for metric in holdings if (metric.unrealized_gain_loss or 0) > 0]
    losers = [metric for metric in holdings if (metric.unrealized_gain_loss or 0) < 0]
    top_position = max(
        holdings,
        key=lambda metric: metric.portfolio_weight_pct or 0,
        default=None,
    )

    summary = (
        f"Portfolio current value is {request.base_currency} {total_value:,.2f} "
        f"with unrealized P/L of {request.base_currency} {total_return:,.2f}. "
        f"There are {len(winners)} winner(s) and {len(losers)} loser(s)."
    )
    if top_position and top_position.portfolio_weight_pct is not None:
        summary += (
            f" The largest position is {top_position.ticker} at "
            f"{top_position.portfolio_weight_pct:.2f}%."
        )

    suggestions: list[str] = []
    if top_position and (top_position.portfolio_weight_pct or 0) > 25:
        suggestions.append(
            f"Review whether {top_position.ticker} should remain above 25% of the portfolio."
        )
    if losers:
        worst = min(losers, key=lambda metric: metric.return_pct or 0)
        suggestions.append(
            f"Reassess the weakest holding first: {worst.ticker} "
            f"is at {worst.return_pct or 0:.2f}%."
        )
    if not any(
        metric.theme in {"Defensive / Income", "Bond / Rate-sensitive"}
        for metric in holdings
    ):
        suggestions.append(
            "Consider whether a defensive income or bond allocation is needed for drawdown control."
        )
    if request.goal:
        suggestions.append(
            f"Keep future reallocations aligned with the stated goal: {request.goal}."
        )
    suggestions.extend(risk_flags[:2])
    return summary, suggestions[:6]


def calculate_portfolio_metrics(
    request: PortfolioRequest,
    *,
    enrichment: dict[str, dict[str, Any]] | None = None,
) -> PortfolioAnalysisResponse:
    enrichment = enrichment or {}
    normalized_holdings: list[HoldingInput] = []
    total_value = 0.0

    for holding in request.holdings:
        data = enrichment.get(holding.ticker, {})
        price = (
            holding.current_price
            if holding.current_price is not None
            else data.get("current_price")
        )
        current_value = holding.current_value
        shares = holding.shares
        if current_value is None and price is not None and shares is not None:
            current_value = price * shares
        elif current_value is not None and shares is None and price not in {None, 0}:
            shares = current_value / price

        normalized = holding.model_copy(
            update={
                "current_price": price,
                "current_value": current_value,
                "shares": shares,
                "name": holding.name or data.get("name"),
                "category": holding.category or data.get("category"),
                "asset_type": holding.asset_type or data.get("asset_type"),
            }
        )
        normalized_holdings.append(normalized)
        total_value += current_value or 0.0

    holdings = [
        calculate_holding_metrics(
            holding,
            total_value,
            sector=enrichment.get(holding.ticker, {}).get("sector"),
            theme=enrichment.get(holding.ticker, {}).get("theme"),
            dividend_yield=enrichment.get(holding.ticker, {}).get("dividend_yield"),
            annual_dividend_per_share=enrichment.get(holding.ticker, {}).get(
                "annual_dividend_per_share"
            ),
        )
        for holding in normalized_holdings
    ]

    total_cost_basis = sum(metric.cost_basis or 0 for metric in holdings)
    total_current_value = sum(metric.current_value or 0 for metric in holdings)
    total_unrealized = sum(metric.unrealized_gain_loss or 0 for metric in holdings)
    total_return_pct = (total_unrealized / total_cost_basis) * 100 if total_cost_basis else None
    annual_dividend = sum(metric.estimated_annual_dividend or 0 for metric in holdings)
    monthly_dividend = sum(metric.estimated_monthly_dividend or 0 for metric in holdings)
    risk_flags = detect_risk_flags(holdings)
    scores = compute_health_scores(holdings)
    summary, suggestions = _build_summary(request, holdings, risk_flags)
    missing_data = sorted({issue for metric in holdings for issue in metric.missing_data})

    return PortfolioAnalysisResponse(
        total_cost_basis=round2(total_cost_basis),
        total_current_value=round2(total_current_value),
        total_unrealized_gain_loss=round2(total_unrealized),
        total_return_pct=round2(total_return_pct),
        estimated_annual_dividend=round2(annual_dividend),
        estimated_monthly_dividend=round2(monthly_dividend),
        holdings=holdings,
        asset_type_exposure=compute_exposure(holdings, "asset_type"),
        category_exposure=compute_exposure(holdings, "category"),
        sector_exposure=compute_exposure(holdings, "sector"),
        theme_exposure=compute_exposure(holdings, "theme"),
        market_exposure=compute_exposure(holdings, "market"),
        risk_attribution=compute_risk_attribution(holdings),
        risk_flags=risk_flags,
        summary=summary,
        suggestions=suggestions,
        missing_data=missing_data,
        **scores,
    )
