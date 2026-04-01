"""
Tool Router
------------
Stage 3 + 4 of the pipeline.

Receives an ExecutionPlan and dispatches each ToolCallSpec to the
appropriate tool function.  Returns a list of ToolResults.

Design:
- Synchronous execution (extend to asyncio / ThreadPoolExecutor for parallelism)
- Each tool is called through a registered handler
- Errors are caught per-call and stored in ToolResult, not re-raised
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, List

try:
    from ..schemas.evidence_schema import ToolResult
    from ..schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
    from ..symbols import detect_market
    from ..tools.earnings_tool import EarningsRequest, fetch_earnings
    from ..tools.fundamentals_tool import FundamentalsRequest, fetch_fundamentals
    from ..tools.market_data_tool import MarketDataRequest, fetch_market_data
    from ..tools.news_tool import NewsRequest, fetch_news
except ImportError:
    from schemas.evidence_schema import ToolResult
    from schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
    from symbols import detect_market
    from tools.earnings_tool import EarningsRequest, fetch_earnings
    from tools.fundamentals_tool import FundamentalsRequest, fetch_fundamentals
    from tools.market_data_tool import MarketDataRequest, fetch_market_data
    from tools.news_tool import NewsRequest, fetch_news


# ── Tool handler registry ─────────────────────────────────────────────────────

def _dump_model(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return default


def _handle_market_data(spec: ToolCallSpec) -> Dict[str, Any]:
    req = MarketDataRequest(
        ticker=spec.ticker,
        lookback_days=spec.params.get("lookback_days", 30),
        include_technicals=spec.params.get("include_technicals", True),
    )
    result = fetch_market_data(req)
    # Flatten to dict for evidence aggregation
    d = result.model_dump(exclude={"ohlc_history"})  # exclude heavy OHLC list
    if result.technicals:
        d["technicals"] = result.technicals.model_dump()
    return d


def _handle_fundamentals(spec: ToolCallSpec) -> Dict[str, Any]:
    req = FundamentalsRequest(
        ticker=spec.ticker,
        include_estimates=spec.params.get("include_estimates", True),
        include_segments=spec.params.get("include_segments", False),
    )
    result = fetch_fundamentals(req)
    profile = _dump_model(getattr(result, "profile", None), {})
    market = profile.get("market") or detect_market(spec.ticker)

    return {
        "market": market,
        "profile": profile,
        "valuation": _dump_model(getattr(result, "valuation", None), {}),
        "income_statement": _dump_model(getattr(result, "income_statement", None), {}),
        "balance_sheet": _dump_model(getattr(result, "balance_sheet", None), {}),
        "estimates": _dump_model(getattr(result, "estimates", None), None),
        "competitive_advantages": list(getattr(result, "competitive_advantages", []) or []),
        "key_risks": list(getattr(result, "key_risks", []) or []),
    }


def _handle_news(spec: ToolCallSpec) -> Dict[str, Any]:
    req = NewsRequest(
        ticker=spec.ticker,
        lookback_days=spec.params.get("lookback_days", 7),
        max_articles=spec.params.get("max_articles", 10),
        sentiment_filter=spec.params.get("sentiment_filter", None),
    )
    result = fetch_news(req)
    return {
        "market": result.market,
        "overall_sentiment": result.overall_sentiment,
        "avg_sentiment_score": result.avg_sentiment_score,
        "total_articles": result.total_articles,
        "articles": [a.model_dump() for a in result.articles],
    }


def _handle_earnings(spec: ToolCallSpec) -> Dict[str, Any]:
    req = EarningsRequest(
        ticker=spec.ticker,
        include_history=spec.params.get("include_history", True),
        history_quarters=spec.params.get("history_quarters", 4),
    )
    result = fetch_earnings(req)
    return {
        "next_earnings": result.next_earnings.model_dump() if result.next_earnings else None,
        "days_to_next_earnings": result.days_to_next_earnings,
        "earnings_history": [r.model_dump() for r in result.earnings_history],
        "avg_eps_surprise_pct": result.avg_eps_surprise_pct,
        "avg_post_earnings_move_pct": result.avg_post_earnings_move_pct,
        "beat_rate": result.beat_rate,
    }


_HANDLERS: Dict[ToolName, Callable[[ToolCallSpec], Dict[str, Any]]] = {
    ToolName.MARKET_DATA:  _handle_market_data,
    ToolName.FUNDAMENTALS: _handle_fundamentals,
    ToolName.NEWS:         _handle_news,
    ToolName.EARNINGS:     _handle_earnings,
}


# ── Router ────────────────────────────────────────────────────────────────────

class ToolRouter:
    """
    Dispatches tool calls from an ExecutionPlan to their handler functions.

    Usage:
        router = ToolRouter()
        results = router.execute(plan)
    """

    def execute(self, plan: ExecutionPlan) -> List[ToolResult]:
        """Execute all tool calls in the plan, sorted by priority."""
        ordered = sorted(plan.tool_calls, key=lambda c: c.priority)
        results: List[ToolResult] = []

        for spec in ordered:
            results.append(self._dispatch(spec))

        return results

    def _dispatch(self, spec: ToolCallSpec) -> ToolResult:
        tool = ToolName(spec.tool)
        handler = _HANDLERS.get(tool)

        if handler is None:
            return ToolResult(
                tool=spec.tool,
                ticker=spec.ticker,
                success=False,
                data={},
                error=f"No handler registered for tool '{spec.tool}'",
            )

        try:
            data = handler(spec)
            return ToolResult(
                tool=spec.tool,
                ticker=spec.ticker,
                success=True,
                data=data,
            )
        except Exception as exc:
            return ToolResult(
                tool=spec.tool,
                ticker=spec.ticker,
                success=False,
                data={},
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            )
