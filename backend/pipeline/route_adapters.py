from __future__ import annotations

from typing import Iterable

try:
    from ..schemas.agent import AgentTask, AgentTaskType
    from ..schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioRequest,
        ScenarioComparisonRequest,
        ScenarioRequest,
    )
    from ..services.security_resolver import resolve_security
    from ..symbols import normalize_symbol
except ImportError:
    from schemas.agent import AgentTask, AgentTaskType
    from schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioRequest,
        ScenarioComparisonRequest,
        ScenarioRequest,
    )
    from services.security_resolver import resolve_security
    from symbols import normalize_symbol


def _normalize_tickers(tickers: Iterable[str]) -> list[str]:
    return [normalize_symbol(ticker) for ticker in tickers]


def research_request_to_agent_task(request) -> AgentTask:
    ticker = normalize_symbol(request.ticker)
    identity = resolve_security(
        request.ticker,
        exchange=request.exchange,
        country=request.country,
    )
    return AgentTask(
        task_type=AgentTaskType.RESEARCH,
        raw_query=request.query or f"research {ticker}",
        tickers=[ticker],
        metadata={"security_identity": identity.model_dump(mode="json")},
    )


def explain_request_to_agent_task(request) -> AgentTask:
    ticker = normalize_symbol(request.ticker)
    return AgentTask(
        task_type=AgentTaskType.EXPLAIN,
        raw_query=f"explain {ticker}",
        tickers=[ticker],
    )


def trade_request_to_agent_task(request) -> AgentTask:
    ticker = normalize_symbol(request.ticker)
    return AgentTask(
        task_type=AgentTaskType.TRADE,
        raw_query=f"trade {ticker}",
        tickers=[ticker],
    )


def watchlist_request_to_agent_task(request) -> AgentTask:
    tickers = _normalize_tickers(request.tickers)
    return AgentTask(
        task_type=AgentTaskType.WATCHLIST,
        raw_query=f"watchlist {' '.join(tickers)}",
        tickers=tickers,
    )


def portfolio_request_to_agent_task(request: PortfolioRequest) -> AgentTask:
    return AgentTask(
        task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
        portfolio=request,
    )


def portfolio_scenario_request_to_agent_task(request: ScenarioRequest) -> AgentTask:
    return AgentTask(
        task_type=AgentTaskType.PORTFOLIO_SCENARIO,
        portfolio=request.portfolio,
        actions=request.actions,
        user_question=request.user_question,
        metadata={
            "target_name": request.target_name,
            "target_ticker": request.target_ticker,
        },
    )


def portfolio_compare_request_to_agent_task(
    request: ScenarioComparisonRequest,
) -> AgentTask:
    return AgentTask(
        task_type=AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE,
        portfolio=request.portfolio,
        scenarios=request.scenarios,
    )


def portfolio_agent_request_to_agent_task(
    request: PortfolioAgentRequest,
) -> AgentTask:
    return AgentTask(
        task_type=AgentTaskType.PORTFOLIO_AGENT,
        portfolio=request.portfolio,
        user_question=request.user_question,
        target_ticker_or_fund=request.target_ticker_or_fund,
    )
