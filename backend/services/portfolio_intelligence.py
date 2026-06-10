from __future__ import annotations

try:
    from ..schemas.portfolio import HoldingMetrics
    from ..schemas.portfolio_intelligence import (
        ConcentrationSnapshot,
        HoldingContribution,
        IncomeQualitySnapshot,
        PortfolioIntelligenceSnapshot,
        ReviewItem,
        RiskAttributionSnapshot,
    )
except ImportError:
    from schemas.portfolio import HoldingMetrics
    from schemas.portfolio_intelligence import (
        ConcentrationSnapshot,
        HoldingContribution,
        IncomeQualitySnapshot,
        PortfolioIntelligenceSnapshot,
        ReviewItem,
        RiskAttributionSnapshot,
    )


def round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _sort_by_numeric(
    holdings: list[HoldingMetrics],
    value_getter,
    *,
    reverse: bool = True,
) -> list[HoldingMetrics]:
    return sorted(
        holdings,
        key=lambda metric: value_getter(metric) or 0.0,
        reverse=reverse,
    )


def _build_contribution(
    metric: HoldingMetrics,
    *,
    contribution_value: float | None = None,
    contribution_pct: float | None = None,
    explanation: str | None = None,
) -> HoldingContribution:
    return HoldingContribution(
        ticker=metric.ticker,
        name=metric.name,
        weight_pct=round2(metric.portfolio_weight_pct),
        current_value=round2(metric.current_value),
        unrealized_gain_loss=round2(metric.unrealized_gain_loss),
        return_pct=round2(metric.return_pct),
        contribution_value=round2(contribution_value),
        contribution_pct=round2(contribution_pct),
        explanation=explanation,
    )


def _build_ranked_contributions(
    holdings: list[HoldingMetrics],
    contribution_lookup: dict[str, float],
    *,
    limit: int = 5,
    explanation: str | None = None,
) -> list[HoldingContribution]:
    total = sum(max(value, 0.0) for value in contribution_lookup.values())
    ranked: list[HoldingContribution] = []
    for metric in sorted(
        holdings,
        key=lambda item: contribution_lookup.get(item.ticker, 0.0),
        reverse=True,
    ):
        contribution_value = contribution_lookup.get(metric.ticker, 0.0)
        if contribution_value <= 0:
            continue
        contribution_pct = (
            contribution_value / total * 100 if total > 0 else 0.0
        )
        ranked.append(
            _build_contribution(
                metric,
                contribution_value=contribution_value,
                contribution_pct=contribution_pct,
                explanation=explanation,
            )
        )
        if len(ranked) >= limit:
            break
    return ranked


def calculate_concentration_snapshot(
    holdings: list[HoldingMetrics],
    *,
    theme_exposure: dict[str, float] | None = None,
    sector_exposure: dict[str, float] | None = None,
    market_exposure: dict[str, float] | None = None,
) -> ConcentrationSnapshot:
    ranked = _sort_by_numeric(
        [metric for metric in holdings if (metric.current_value or 0) > 0],
        lambda metric: metric.portfolio_weight_pct,
    )

    top_weights = [metric.portfolio_weight_pct or 0.0 for metric in ranked]
    top_holding = top_weights[0] if top_weights else None
    top_3 = sum(top_weights[:3]) if top_weights else None
    top_5 = sum(top_weights[:5]) if top_weights else None

    top_tickers = [
        _build_contribution(
            metric,
            contribution_value=metric.current_value,
            contribution_pct=metric.portfolio_weight_pct,
            explanation="Portfolio weight contribution.",
        )
        for metric in ranked[:5]
    ]

    flags: list[str] = []
    if (top_holding or 0) > 35:
        flags.append("Very high single-position concentration: one holding exceeds 35%.")
    elif (top_holding or 0) > 25:
        flags.append("High single-position concentration: one holding exceeds 25%.")

    if (top_3 or 0) > 60:
        flags.append("Top 3 holdings exceed 60% of portfolio value.")
    if (top_5 or 0) > 80:
        flags.append("Top 5 holdings exceed 80% of portfolio value.")

    for label, exposure in sorted(
        (theme_exposure or {}).items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        if exposure > 65:
            flags.append(f"Very high theme concentration in {label} ({exposure:.2f}%).")
        elif exposure > 50:
            flags.append(f"High theme concentration in {label} ({exposure:.2f}%).")

    for label, exposure in sorted(
        (market_exposure or {}).items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        if exposure > 70:
            flags.append(f"Market concentration is high in {label} ({exposure:.2f}%).")

    return ConcentrationSnapshot(
        top_holding_weight_pct=round2(top_holding),
        top_3_weight_pct=round2(top_3),
        top_5_weight_pct=round2(top_5),
        top_tickers=top_tickers,
        theme_exposure_pct=theme_exposure or {},
        sector_exposure_pct=sector_exposure or {},
        market_exposure_pct=market_exposure or {},
        flags=flags,
    )


def calculate_risk_attribution_snapshot(
    holdings: list[HoldingMetrics],
    *,
    stress_test_impacts: dict[str, float] | None = None,
) -> RiskAttributionSnapshot:
    downside_lookup = {
        metric.ticker: (metric.current_value or 0.0) * max(0.0, -(metric.return_pct or 0.0))
        for metric in holdings
    }
    negative_gl_lookup = {
        metric.ticker: abs(metric.unrealized_gain_loss or 0.0)
        for metric in holdings
        if (metric.unrealized_gain_loss or 0.0) < 0
    }
    positive_gl_lookup = {
        metric.ticker: metric.unrealized_gain_loss or 0.0
        for metric in holdings
        if (metric.unrealized_gain_loss or 0.0) > 0
    }
    stress_lookup = {
        ticker: max(impact or 0.0, 0.0)
        for ticker, impact in (stress_test_impacts or {}).items()
    }

    downside_ranked = _build_ranked_contributions(
        holdings,
        downside_lookup,
        explanation="Downside-weighted exposure estimate.",
    )
    loser_ranked = _build_ranked_contributions(
        holdings,
        negative_gl_lookup,
        explanation="Share of total unrealized losses.",
    )
    winner_ranked = _build_ranked_contributions(
        holdings,
        positive_gl_lookup,
        explanation="Share of total unrealized gains.",
    )
    stress_ranked = _build_ranked_contributions(
        holdings,
        stress_lookup,
        explanation="Share of stress-test impact.",
    )

    flags: list[str] = []
    if downside_ranked and (downside_ranked[0].contribution_pct or 0.0) > 40:
        flags.append(
            f"{downside_ranked[0].ticker} dominates downside-weighted risk attribution."
        )
    if loser_ranked and (loser_ranked[0].contribution_pct or 0.0) > 35:
        flags.append(
            f"{loser_ranked[0].ticker} dominates unrealized loss concentration."
        )
    if stress_ranked and (stress_ranked[0].contribution_pct or 0.0) > 50:
        flags.append(
            f"{stress_ranked[0].ticker} dominates the current stress-test impact."
        )

    return RiskAttributionSnapshot(
        top_downside_weighted_holdings=downside_ranked,
        top_unrealized_losers=loser_ranked,
        top_unrealized_winners=winner_ranked,
        top_stress_test_contributors=stress_ranked,
        flags=flags,
    )


def calculate_income_quality_snapshot(
    holdings: list[HoldingMetrics],
) -> IncomeQualitySnapshot:
    annual_dividend = sum(metric.estimated_annual_dividend or 0.0 for metric in holdings)
    monthly_dividend = annual_dividend / 12 if annual_dividend else 0.0

    dividend_lookup = {
        metric.ticker: metric.estimated_annual_dividend or 0.0
        for metric in holdings
    }
    top_dividend_contributors = _build_ranked_contributions(
        holdings,
        dividend_lookup,
        explanation="Share of estimated annual dividend.",
    )

    top_dividend_pct = (
        top_dividend_contributors[0].contribution_pct
        if top_dividend_contributors
        else None
    )

    missing_dividend_data = sorted(
        metric.ticker
        for metric in holdings
        if (metric.current_value or 0.0) > 0 and metric.estimated_annual_dividend is None
    )

    caveats: list[str] = []
    if missing_dividend_data:
        caveats.append(
            "Dividend estimates are incomplete because some holdings are missing dividend data."
        )
    if annual_dividend > 0:
        caveats.append(
            "Estimated dividend income is heuristic and should not be treated as guaranteed income."
        )
    else:
        caveats.append(
            "No estimated dividend income is available from the current holding data."
        )

    if (top_dividend_pct or 0.0) > 40:
        caveats.append(
            "Estimated income appears concentrated in one holding and may be less diversified."
        )

    return IncomeQualitySnapshot(
        estimated_annual_dividend=round2(annual_dividend),
        estimated_monthly_dividend=round2(monthly_dividend),
        top_dividend_contributors=top_dividend_contributors,
        dividend_concentration_pct=round2(top_dividend_pct),
        holdings_missing_dividend_data=missing_dividend_data,
        caveats=caveats,
    )


def build_suggested_review_items(
    holdings: list[HoldingMetrics],
    concentration: ConcentrationSnapshot,
    income_quality: IncomeQualitySnapshot,
    risk_attribution: RiskAttributionSnapshot,
) -> list[ReviewItem]:
    items: list[ReviewItem] = []

    if (concentration.top_tickers and (concentration.top_holding_weight_pct or 0.0) > 35):
        top = concentration.top_tickers[0]
        items.append(
            ReviewItem(
                title=f"Review very high concentration in {top.ticker}",
                reason=(
                    f"{top.ticker} is {top.weight_pct or 0:.2f}% of portfolio value, "
                    "which is above the 35% concentration threshold."
                ),
                evidence_keys=[
                    "holdings",
                    "concentration.top_holding_weight_pct",
                    "concentration.top_tickers",
                ],
                severity="high",
            )
        )
    elif concentration.top_tickers and (concentration.top_holding_weight_pct or 0.0) > 25:
        top = concentration.top_tickers[0]
        items.append(
            ReviewItem(
                title=f"Review concentration in {top.ticker}",
                reason=(
                    f"{top.ticker} is {top.weight_pct or 0:.2f}% of portfolio value, "
                    "which is above the 25% concentration threshold."
                ),
                evidence_keys=[
                    "holdings",
                    "concentration.top_holding_weight_pct",
                    "concentration.top_tickers",
                ],
                severity="medium",
            )
        )

    if (concentration.top_3_weight_pct or 0.0) > 60:
        items.append(
            ReviewItem(
                title="Review top 3 holding concentration",
                reason=(
                    f"The top 3 holdings represent {concentration.top_3_weight_pct or 0:.2f}% "
                    "of portfolio value."
                ),
                evidence_keys=["holdings", "concentration.top_3_weight_pct"],
                severity="medium",
            )
        )

    for label, exposure in sorted(
        concentration.theme_exposure_pct.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        if exposure > 65:
            items.append(
                ReviewItem(
                    title=f"Review very high {label} theme concentration",
                    reason=f"{label} represents {exposure:.2f}% of the portfolio.",
                    evidence_keys=["theme_exposure", "concentration.theme_exposure_pct"],
                    severity="high",
                )
            )
            break
        if exposure > 50:
            items.append(
                ReviewItem(
                    title=f"Review {label} theme concentration",
                    reason=f"{label} represents {exposure:.2f}% of the portfolio.",
                    evidence_keys=["theme_exposure", "concentration.theme_exposure_pct"],
                    severity="medium",
                )
            )
            break

    for label, exposure in sorted(
        concentration.market_exposure_pct.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        if exposure > 70:
            items.append(
                ReviewItem(
                    title=f"Review market concentration in {label}",
                    reason=f"{label} represents {exposure:.2f}% of the portfolio.",
                    evidence_keys=["market_exposure", "concentration.market_exposure_pct"],
                    severity="medium",
                )
            )
            break

    if (
        (income_quality.dividend_concentration_pct or 0.0) > 40
        and income_quality.top_dividend_contributors
    ):
        leader = income_quality.top_dividend_contributors[0]
        items.append(
            ReviewItem(
                title=f"Review income concentration in {leader.ticker}",
                reason=(
                    f"{leader.ticker} contributes {leader.contribution_pct or 0:.2f}% "
                    "of estimated annual dividend income."
                ),
                evidence_keys=[
                    "holdings",
                    "income_quality.top_dividend_contributors",
                    "income_quality.dividend_concentration_pct",
                ],
                severity="medium",
            )
        )

    if income_quality.holdings_missing_dividend_data:
        items.append(
            ReviewItem(
                title="Review missing dividend data coverage",
                reason=(
                    "Some holdings are missing dividend inputs, so income "
                    "estimates may be incomplete."
                ),
                evidence_keys=[
                    "holdings",
                    "income_quality.holdings_missing_dividend_data",
                    "income_quality.caveats",
                ],
                severity="low",
            )
        )

    if risk_attribution.top_unrealized_losers and (
        risk_attribution.top_unrealized_losers[0].contribution_pct or 0.0
    ) > 35:
        leader = risk_attribution.top_unrealized_losers[0]
        items.append(
            ReviewItem(
                title=f"Review unrealized loss concentration in {leader.ticker}",
                reason=(
                    f"{leader.ticker} accounts for {leader.contribution_pct or 0:.2f}% "
                    "of current unrealized losses."
                ),
                evidence_keys=[
                    "holdings",
                    "risk_attribution.top_unrealized_losers",
                ],
                severity="medium",
            )
        )

    if risk_attribution.top_stress_test_contributors and (
        risk_attribution.top_stress_test_contributors[0].contribution_pct or 0.0
    ) > 50:
        leader = risk_attribution.top_stress_test_contributors[0]
        items.append(
            ReviewItem(
                title=f"Monitor stress sensitivity in {leader.ticker}",
                reason=(
                    f"{leader.ticker} contributes {leader.contribution_pct or 0:.2f}% "
                    "of the latest stress-test impact."
                ),
                evidence_keys=[
                    "risk_attribution.top_stress_test_contributors",
                ],
                severity="medium",
            )
        )

    return items[:8]


def build_portfolio_intelligence_snapshot(
    holdings: list[HoldingMetrics],
    *,
    theme_exposure: dict[str, float] | None = None,
    sector_exposure: dict[str, float] | None = None,
    market_exposure: dict[str, float] | None = None,
    stress_test_impacts: dict[str, float] | None = None,
) -> PortfolioIntelligenceSnapshot:
    concentration = calculate_concentration_snapshot(
        holdings,
        theme_exposure=theme_exposure,
        sector_exposure=sector_exposure,
        market_exposure=market_exposure,
    )
    income_quality = calculate_income_quality_snapshot(holdings)
    risk_attribution = calculate_risk_attribution_snapshot(
        holdings,
        stress_test_impacts=stress_test_impacts,
    )
    suggested_review_items = build_suggested_review_items(
        holdings,
        concentration,
        income_quality,
        risk_attribution,
    )

    return PortfolioIntelligenceSnapshot(
        risk_attribution=risk_attribution,
        concentration=concentration,
        income_quality=income_quality,
        suggested_review_items=suggested_review_items,
    )
