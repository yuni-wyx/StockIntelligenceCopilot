"""
Planning Chain
---------------
Stage 2 of the pipeline.

Input  : IntentOutput  (mode, tickers)
Output : ExecutionPlan (ordered list of tool calls + metadata)

Uses a strategy pattern — one planner per mode — so the logic is declarative
and easy to extend.  An LLM could generate the plan instead; the output schema
(ExecutionPlan) remains unchanged either way.
"""

from __future__ import annotations

from typing import List

from langchain_core.runnables import RunnableLambda

try:
    from ..schemas.intent_schema import AnalysisMode, IntentOutput
    from ..schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
except ImportError:
    from schemas.intent_schema import AnalysisMode, IntentOutput
    from schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName


# ── Mode planners ─────────────────────────────────────────────────────────────

def _plan_stock_research(intent: IntentOutput) -> ExecutionPlan:
    """Full-depth research: fundamentals + news + earnings + price data."""
    ticker = intent.tickers[0]
    tool_calls: List[ToolCallSpec] = [
        ToolCallSpec(
            tool=ToolName.FUNDAMENTALS, ticker=ticker, priority=1,
            params={"include_estimates": True},
            rationale="Fundamentals are the backbone of the research report.",
        ),
        ToolCallSpec(
            tool=ToolName.MARKET_DATA, ticker=ticker, priority=2,
            params={"lookback_days": 60, "include_technicals": True},
            rationale="Price/volume history and technicals provide context for the bull/bear case.",
        ),
        ToolCallSpec(
            tool=ToolName.NEWS, ticker=ticker, priority=3,
            params={"lookback_days": 14, "max_articles": 10},
            rationale="Recent headlines inform the narrative and upcoming catalysts.",
        ),
        ToolCallSpec(
            tool=ToolName.EARNINGS, ticker=ticker, priority=4,
            params={"include_history": True, "history_quarters": 4},
            rationale="Earnings cadence and surprise history feed into the bull/bear case.",
        ),
    ]
    return ExecutionPlan(
        mode=intent.mode,
        tickers=[ticker],
        tool_calls=tool_calls,
        analysis_focus=f"Comprehensive fundamental and qualitative analysis of {ticker}",
        expected_outputs=[
            "fundamental_summary",
            "recent_news_summary",
            "bull_case",
            "bear_case",
            "what_to_watch_next",
            "overall_sentiment",
        ],
    )


def _plan_price_movement(intent: IntentOutput) -> ExecutionPlan:
    """Explain today's move: price data + news + earnings catalyst check."""
    ticker = intent.tickers[0]
    tool_calls: List[ToolCallSpec] = [
        ToolCallSpec(
            tool=ToolName.MARKET_DATA, ticker=ticker, priority=1,
            params={"lookback_days": 5, "include_technicals": True},
            rationale="Need today's price action and volume vs average.",
        ),
        ToolCallSpec(
            tool=ToolName.NEWS, ticker=ticker, priority=2,
            params={"lookback_days": 3, "max_articles": 15},
            rationale="Recent headlines are the primary candidate causes for the move.",
        ),
        ToolCallSpec(
            tool=ToolName.EARNINGS, ticker=ticker, priority=3,
            params={"include_history": False},
            rationale="Check if the move is earnings-related or near an earnings date.",
        ),
        ToolCallSpec(
            tool=ToolName.FUNDAMENTALS, ticker=ticker, priority=4,
            params={"include_estimates": True, "include_segments": False},
            rationale="Valuation context helps assess if move is warranted.",
        ),
    ]
    return ExecutionPlan(
        mode=intent.mode,
        tickers=[ticker],
        tool_calls=tool_calls,
        analysis_focus=f"Explain today's price movement in {ticker} with ranked causes",
        expected_outputs=[
            "price_move_summary",
            "ranked_causes",
            "overall_confidence",
            "what_to_watch_next",
        ],
    )


def _plan_watchlist_monitor(intent: IntentOutput) -> ExecutionPlan:
    """Weekly digest: lightweight scan across multiple tickers."""
    tickers = intent.tickers
    tool_calls: List[ToolCallSpec] = []
    priority = 1

    for ticker in tickers:
        # Market data: 7-day lookback, no heavy technicals
        tool_calls.append(ToolCallSpec(
            tool=ToolName.MARKET_DATA, ticker=ticker, priority=priority,
            params={"lookback_days": 7, "include_technicals": False},
            rationale=f"Weekly price performance for {ticker}.",
        ))
        priority += 1

        tool_calls.append(ToolCallSpec(
            tool=ToolName.NEWS, ticker=ticker, priority=priority,
            params={"lookback_days": 7, "max_articles": 6},
            rationale=f"Top weekly news for {ticker}.",
        ))
        priority += 1

        tool_calls.append(ToolCallSpec(
            tool=ToolName.EARNINGS, ticker=ticker, priority=priority,
            params={"include_history": False},
            rationale=f"Upcoming earnings for {ticker} as an event risk.",
        ))
        priority += 1

    return ExecutionPlan(
        mode=intent.mode,
        tickers=tickers,
        tool_calls=tool_calls,
        analysis_focus=(
            f"Weekly monitoring digest for watchlist: {', '.join(tickers)}"
        ),
        expected_outputs=[
            "portfolio_summary",
            "ticker_summaries",
            "macro_risks",
            "top_opportunities",
        ],
    )

def _plan_trade(intent: IntentOutput) -> ExecutionPlan:
    """
    Trading decision mode:
    Reuses research-style data but outputs a structured trade setup.
    """
    ticker = intent.tickers[0]

    tool_calls: List[ToolCallSpec] = [
        ToolCallSpec(
            tool=ToolName.MARKET_DATA,
            ticker=ticker,
            priority=1,
            params={"lookback_days": 30, "include_technicals": True},
            rationale="Price action and technicals determine entry/exit zones.",
        ),
        ToolCallSpec(
            tool=ToolName.NEWS,
            ticker=ticker,
            priority=2,
            params={"lookback_days": 7, "max_articles": 10},
            rationale="Recent news drives short-term sentiment.",
        ),
        ToolCallSpec(
            tool=ToolName.FUNDAMENTALS,
            ticker=ticker,
            priority=3,
            params={"include_estimates": True},
            rationale="Fundamentals provide baseline conviction.",
        ),
        ToolCallSpec(
            tool=ToolName.EARNINGS,
            ticker=ticker,
            priority=4,
            params={"include_history": False},
            rationale="Earnings timing is a major risk/catalyst.",
        ),
    ]

    return ExecutionPlan(
        mode=AnalysisMode.TRADE,
        tickers=[ticker],
        tool_calls=tool_calls,
        analysis_focus=f"Generate a structured trading decision for {ticker}",
        expected_outputs=[
            "bias",
            "buy_zone",
            "stop_loss",
            "take_profit",
            "confidence",
            "reasoning",
        ],
    )

# ── Strategy dispatcher ───────────────────────────────────────────────────────

_PLANNERS = {
    AnalysisMode.STOCK_RESEARCH:    _plan_stock_research,
    AnalysisMode.PRICE_MOVEMENT:    _plan_price_movement,
    AnalysisMode.WATCHLIST_MONITOR: _plan_watchlist_monitor,
    AnalysisMode.TRADE: _plan_trade,
}


# ── LCEL Runnable ─────────────────────────────────────────────────────────────

def build_planner_chain() -> RunnableLambda:
    """
    Returns the Planning Chain as a LangChain Runnable.

    Usage:
        chain = build_planner_chain()
        plan: ExecutionPlan = chain.invoke(intent_output)
    """
    def _run(intent: IntentOutput) -> ExecutionPlan:
        mode = AnalysisMode(intent.mode)
        planner = _PLANNERS.get(mode)
        if planner is None:
            raise ValueError(f"No planner registered for mode: {intent.mode}")
        return planner(intent)

    return RunnableLambda(_run).with_config(run_name="PlanningChain")
