from __future__ import annotations

import logging
from copy import deepcopy

try:
    from ..schemas.portfolio import (
        HoldingInput,
        PortfolioAnalysisResponse,
        PortfolioRequest,
        ScenarioComparisonItem,
        ScenarioComparisonRequest,
        ScenarioComparisonResponse,
        ScenarioRequest,
        ScenarioResponse,
    )
    from ..services.portfolio_calculator import (
        calculate_portfolio_metrics,
        classify_theme,
        round2,
    )
    from ..symbols import normalize_symbol
    from ..tools.fundamentals_tool import FundamentalsRequest, fetch_fundamentals
    from ..tools.market_data_tool import MarketDataRequest, fetch_market_data
    from ..tools.news_tool import NewsRequest, fetch_news
except ImportError:
    from schemas.portfolio import (
        HoldingInput,
        PortfolioAnalysisResponse,
        PortfolioRequest,
        ScenarioComparisonItem,
        ScenarioComparisonRequest,
        ScenarioComparisonResponse,
        ScenarioRequest,
        ScenarioResponse,
    )
    from services.portfolio_calculator import (
        calculate_portfolio_metrics,
        classify_theme,
        round2,
    )
    from symbols import normalize_symbol
    from tools.fundamentals_tool import FundamentalsRequest, fetch_fundamentals
    from tools.market_data_tool import MarketDataRequest, fetch_market_data
    from tools.news_tool import NewsRequest, fetch_news

logger = logging.getLogger(__name__)


def _holding_name(holding: HoldingInput, fundamentals) -> str | None:
    if holding.name:
        return holding.name
    profile = getattr(fundamentals, "profile", None)
    return getattr(profile, "name", None)


def _holding_asset_type(holding: HoldingInput) -> str | None:
    if holding.asset_type:
        return holding.asset_type
    ticker = normalize_symbol(holding.ticker)
    if ticker.endswith(".TW") and ticker[:1] == "0":
        return "ETF"
    return "Stock"


def _enrich_holding(holding: HoldingInput) -> tuple[HoldingInput, dict]:
    canonical = normalize_symbol(holding.ticker)
    price_data = None
    fundamentals = None
    news = None

    try:
        price_data = fetch_market_data(
            MarketDataRequest(ticker=canonical, include_technicals=False)
        )
    except Exception:
        logger.exception("Failed to fetch market data for portfolio holding %s", canonical)

    try:
        fundamentals = fetch_fundamentals(
            FundamentalsRequest(
                ticker=canonical,
                include_estimates=False,
                include_segments=False,
            )
        )
    except Exception:
        logger.exception("Failed to fetch fundamentals for portfolio holding %s", canonical)

    try:
        news = fetch_news(NewsRequest(ticker=canonical, max_articles=3, lookback_days=7))
    except Exception:
        logger.exception("Failed to fetch news for portfolio holding %s", canonical)

    profile = getattr(fundamentals, "profile", None)
    holding_name = _holding_name(holding, fundamentals)
    sector = getattr(profile, "sector", None)
    category = holding.category or sector or "Unclassified"
    theme = classify_theme(holding, sector=sector, category=category)
    dividend_yield = getattr(profile, "dividend_yield", None)
    annual_dividend_per_share = getattr(profile, "annual_dividend_per_share", None)

    updated = holding.model_copy(
        update={
            "ticker": canonical,
            "name": holding_name,
            "current_price": (
                holding.current_price
                if holding.current_price is not None
                else getattr(price_data, "current_price", None)
            ),
            "asset_type": _holding_asset_type(holding),
            "category": category,
        }
    )

    enrichment = {
        "name": holding_name,
        "current_price": getattr(price_data, "current_price", None),
        "sector": sector,
        "theme": theme,
        "dividend_yield": dividend_yield,
        "annual_dividend_per_share": annual_dividend_per_share,
        "category": category,
        "asset_type": updated.asset_type,
        "news": [article.title for article in getattr(news, "articles", [])[:3]]
        if news
        else [],
        "market_data": (
            price_data.model_dump(mode="json")
            if price_data and hasattr(price_data, "model_dump")
            else None
        ),
        "fundamentals": (
            fundamentals.model_dump(mode="json")
            if fundamentals and hasattr(fundamentals, "model_dump")
            else None
        ),
        "news_articles": (
            [article.model_dump(mode="json") for article in getattr(news, "articles", [])]
            if news
            else []
        ),
    }
    return updated, enrichment


def _build_portfolio_enrichment(
    request: PortfolioRequest,
) -> tuple[PortfolioRequest, dict[str, dict]]:
    enriched_holdings: list[HoldingInput] = []
    enrichment: dict[str, dict] = {}
    for holding in request.holdings:
        enriched, extra = _enrich_holding(holding)
        enriched_holdings.append(enriched)
        enrichment[enriched.ticker] = extra
    return request.model_copy(update={"holdings": enriched_holdings}), enrichment


def _attach_news_to_monitor(
    response: PortfolioAnalysisResponse,
    enrichment: dict[str, dict],
) -> PortfolioAnalysisResponse:
    news_to_monitor = {
        ticker: payload.get("news", [])
        for ticker, payload in enrichment.items()
        if payload.get("news")
    }
    return response.model_copy(update={"news_to_monitor": news_to_monitor})


def analyze_portfolio_with_evidence(
    request: PortfolioRequest,
) -> tuple[PortfolioAnalysisResponse, dict[str, dict]]:
    enriched_request, enrichment = _build_portfolio_enrichment(request)
    response = calculate_portfolio_metrics(enriched_request, enrichment=enrichment)
    return _attach_news_to_monitor(response, enrichment), enrichment


def _analyze_portfolio_impl(request: PortfolioRequest) -> PortfolioAnalysisResponse:
    response, _ = analyze_portfolio_with_evidence(request)
    return response


def _resolve_action_quantity(holding: HoldingInput, action) -> tuple[float, list[str]]:
    caveats: list[str] = []
    shares = holding.shares or 0.0
    current_price = holding.current_price or 0.0

    if action.action == "hold_cash":
        return 0.0, caveats
    if action.shares is not None:
        return action.shares, caveats
    if action.percentage is not None:
        return shares * (action.percentage / 100), caveats
    if action.amount is not None and current_price > 0:
        return action.amount / current_price, caveats

    caveats.append(f"Could not resolve quantity for {action.action} {action.ticker}.")
    return 0.0, caveats


def _apply_scenario_actions(
    request: ScenarioRequest,
    enrichment: dict[str, dict],
) -> tuple[PortfolioRequest, list[str]]:
    updated_holdings = [deepcopy(holding.model_dump()) for holding in request.portfolio.holdings]
    by_ticker = {normalize_symbol(item["ticker"]): item for item in updated_holdings}
    caveats: list[str] = []
    proceeds = 0.0
    cash_buffer = 0.0

    for action in request.actions:
        ticker = normalize_symbol(action.ticker)
        if action.action == "hold_cash":
            if action.amount is not None:
                cash_buffer += action.amount
            continue

        if action.action == "sell":
            current = by_ticker.get(ticker)
            if not current:
                caveats.append(f"No existing holding matched sell action for {ticker}.")
                continue

            holding = HoldingInput(**current)
            quantity, issues = _resolve_action_quantity(holding, action)
            caveats.extend(issues)
            quantity = max(quantity, 0.0)

            if holding.shares is not None and quantity > holding.shares:
                caveats.append(
                    f"Sell quantity for {ticker} exceeded current shares and was capped."
                )
                quantity = holding.shares

            current_price = (
                holding.current_price
                or enrichment.get(ticker, {}).get("current_price")
                or 0.0
            )
            proceeds += quantity * current_price

            if holding.shares is not None:
                current["shares"] = max((holding.shares or 0.0) - quantity, 0.0)
            if current_price > 0 and current.get("current_value") is not None:
                current["current_value"] = max(
                    (holding.current_value or 0.0) - quantity * current_price,
                    0.0,
                )

        elif action.action == "buy":
            target = by_ticker.get(ticker)
            price = enrichment.get(ticker, {}).get("current_price")
            if price is None:
                fetched, extra = _enrich_holding(
                    HoldingInput(ticker=ticker, name=request.target_name)
                )
                enrichment[ticker] = extra
                price = fetched.current_price

            if price in {None, 0}:
                caveats.append(f"Missing price for buy action in {ticker}.")
                continue

            quantity = action.shares if action.shares is not None else None
            if quantity is None and action.amount is not None:
                quantity = action.amount / price
            elif quantity is None and action.percentage is not None:
                quantity = proceeds * (action.percentage / 100) / price if proceeds > 0 else 0.0

            if quantity is None:
                caveats.append(f"Could not resolve buy quantity for {ticker}.")
                continue

            cost = quantity * price
            if proceeds and cost > proceeds - cash_buffer + 1e-6:
                caveats.append(
                    f"Buy action for {ticker} uses more cash than the recorded sale proceeds."
                )

            if target:
                prior_shares = target.get("shares") or 0.0
                prior_value = target.get("current_value") or 0.0
                target["shares"] = prior_shares + quantity
                target["current_value"] = prior_value + cost
                target["current_price"] = price
                target["avg_cost"] = price
            else:
                by_ticker[ticker] = HoldingInput(
                    ticker=ticker,
                    name=request.target_name or enrichment.get(ticker, {}).get("name") or ticker,
                    avg_cost=price,
                    current_price=price,
                    current_value=cost,
                    shares=quantity,
                    asset_type=enrichment.get(ticker, {}).get("asset_type") or "Stock",
                    category=enrichment.get(ticker, {}).get("category"),
                ).model_dump()

    normalized = [HoldingInput(**holding) for holding in by_ticker.values()]
    filtered = [
        holding
        for holding in normalized
        if (holding.shares or 0) > 0 or (holding.current_value or 0) > 0
    ]
    return request.portfolio.model_copy(update={"holdings": filtered}), caveats


def _risk_change_summary(
    before: PortfolioAnalysisResponse,
    after: PortfolioAnalysisResponse,
) -> str:
    before_tech = before.theme_exposure.get("Technology / AI", 0.0)
    after_tech = after.theme_exposure.get("Technology / AI", 0.0)
    before_def = (
        before.theme_exposure.get("Defensive / Income", 0.0)
        + before.theme_exposure.get("Bond / Rate-sensitive", 0.0)
    )
    after_def = (
        after.theme_exposure.get("Defensive / Income", 0.0)
        + after.theme_exposure.get("Bond / Rate-sensitive", 0.0)
    )
    return (
        f"Technology / AI exposure changes from {before_tech:.2f}% to {after_tech:.2f}%, "
        f"while defensive allocation changes from {before_def:.2f}% to {after_def:.2f}%."
    )


def _scenario_recommendation(
    before: PortfolioAnalysisResponse,
    after: PortfolioAnalysisResponse,
    question: str | None,
) -> str:
    dividend_change = (
        (after.estimated_annual_dividend or 0)
        - (before.estimated_annual_dividend or 0)
    )
    lead = f"Question considered: {question.strip()} " if question else ""
    if dividend_change < 0:
        return (
            f"{lead}This reallocation is reasonable, but I would not move "
            "the full position at once. The portfolio gives up some income, "
            "so a gradual rebalance is easier to defend than an all-at-once shift."
        )
    if after.overall_score > before.overall_score:
        return (
            f"{lead}This scenario modestly improves the portfolio health score "
            "without obviously worsening concentration."
        )
    return (
        f"{lead}This scenario is analyzable, but the portfolio tradeoff is mixed "
        "and deserves a slower, staged approach."
    )


def _run_portfolio_scenario_impl(request: ScenarioRequest) -> ScenarioResponse:
    before, enrichment = analyze_portfolio_with_evidence(request.portfolio)
    return _run_portfolio_scenario_from_base(request, before, enrichment)


def _run_portfolio_scenario_from_base(
    request: ScenarioRequest,
    before: PortfolioAnalysisResponse,
    enrichment: dict[str, dict],
) -> ScenarioResponse:
    after_request, caveats = _apply_scenario_actions(
        request.model_copy(update={"portfolio": request.portfolio}),
        deepcopy(enrichment),
    )
    after, _ = analyze_portfolio_with_evidence(after_request)

    dividend_change = None
    if (
        before.estimated_annual_dividend is not None
        and after.estimated_annual_dividend is not None
    ):
        dividend_change = round2(
            after.estimated_annual_dividend - before.estimated_annual_dividend
        )

    return ScenarioResponse(
        before=before,
        after=after,
        dividend_change=dividend_change,
        risk_change_summary=_risk_change_summary(before, after),
        recommendation=_scenario_recommendation(before, after, request.user_question),
        caveats=caveats or before.missing_data or after.missing_data,
    )


def _compare_portfolio_scenarios_impl(
    request: ScenarioComparisonRequest,
) -> ScenarioComparisonResponse:
    current, base_enrichment = analyze_portfolio_with_evidence(request.portfolio)
    items: list[ScenarioComparisonItem] = []

    for index, scenario in enumerate(request.scenarios, start=1):
        result = _run_portfolio_scenario_from_base(
            ScenarioRequest(
                portfolio=request.portfolio,
                actions=scenario.actions,
                user_question=scenario.user_question,
            ),
            current,
            base_enrichment,
        )
        before_top = max(
            (holding.portfolio_weight_pct or 0 for holding in result.before.holdings),
            default=0.0,
        )
        after_top = max(
            (holding.portfolio_weight_pct or 0 for holding in result.after.holdings),
            default=0.0,
        )
        items.append(
            ScenarioComparisonItem(
                name=scenario.name,
                before_value=result.before.total_current_value,
                after_value=result.after.total_current_value,
                dividend_change=result.dividend_change,
                technology_exposure_change=round2(
                    result.after.theme_exposure.get("Technology / AI", 0.0)
                    - result.before.theme_exposure.get("Technology / AI", 0.0)
                ),
                defensive_allocation_change=round2(
                    (
                        result.after.theme_exposure.get("Defensive / Income", 0.0)
                        + result.after.theme_exposure.get("Bond / Rate-sensitive", 0.0)
                    )
                    - (
                        result.before.theme_exposure.get("Defensive / Income", 0.0)
                        + result.before.theme_exposure.get("Bond / Rate-sensitive", 0.0)
                    )
                ),
                concentration_change=round2(after_top - before_top),
                risk_flags_added=sorted(
                    set(result.after.risk_flags) - set(result.before.risk_flags)
                ),
                risk_flags_removed=sorted(
                    set(result.before.risk_flags) - set(result.after.risk_flags)
                ),
                overall_score_change=result.after.overall_score - result.before.overall_score,
                recommendation_rank=index,
                recommendation=result.recommendation,
            )
        )

    ranked = sorted(
        items,
        key=lambda item: (
            item.overall_score_change,
            item.dividend_change or 0.0,
            -(item.concentration_change or 0.0),
        ),
        reverse=True,
    )
    for rank, item in enumerate(ranked, start=1):
        item.recommendation_rank = rank

    return ScenarioComparisonResponse(current=current, scenarios=ranked)


def analyze_portfolio(request: PortfolioRequest) -> PortfolioAnalysisResponse:
    try:
        from .agent_runtime import execute_portfolio_analysis
    except ImportError:
        from pipeline.agent_runtime import execute_portfolio_analysis

    return execute_portfolio_analysis(request)


def run_portfolio_scenario(request: ScenarioRequest) -> ScenarioResponse:
    try:
        from .agent_runtime import execute_portfolio_scenario
    except ImportError:
        from pipeline.agent_runtime import execute_portfolio_scenario

    return execute_portfolio_scenario(request)


def compare_portfolio_scenarios(
    request: ScenarioComparisonRequest,
) -> ScenarioComparisonResponse:
    try:
        from .agent_runtime import execute_portfolio_scenarios_compare
    except ImportError:
        from pipeline.agent_runtime import execute_portfolio_scenarios_compare

    return execute_portfolio_scenarios_compare(request)
