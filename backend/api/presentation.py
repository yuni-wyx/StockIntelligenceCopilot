from __future__ import annotations

import json
from typing import Any

from fastapi.responses import StreamingResponse

try:
    from ..symbols import normalize_symbol
except ImportError:
    from symbols import normalize_symbol


def serialize_output(output: Any) -> dict:
    if hasattr(output, "model_dump"):
        return output.model_dump(mode="json")
    if hasattr(output, "dict"):
        return output.dict()
    return {"result": str(output)}


def _normalized_query_tokens(raw_query: str) -> list[str]:
    parts = raw_query.strip().split()
    if not parts:
        return []
    verb = parts[0].lower()
    tickers = [normalize_symbol(part) for part in parts[1:]]
    return [verb, *tickers]


def query_parts(raw_query: str) -> tuple[str, str]:
    parts = _normalized_query_tokens(raw_query)
    verb = parts[0] if parts else ""
    ticker = parts[1] if len(parts) > 1 else ""
    return verb, ticker


def error_output(raw_query: str, exc: Exception) -> dict:
    verb, ticker = query_parts(raw_query)
    message = str(exc)

    if verb == "research":
        return {
            "error": message,
            "ticker": ticker,
            "generated_at": None,
            "fundamental_summary": f"Research failed: {message}",
            "recent_news_summary": "",
            "bull_case": "",
            "bear_case": "",
            "what_to_watch_next": [],
            "overall_sentiment": "NEUTRAL",
        }

    if verb == "explain":
        return {
            "error": message,
            "ticker": ticker,
            "price_change_pct": 0,
            "price_move_summary": f"Explain mode failed: {message}",
            "overall_confidence": 0,
            "ranked_causes": [],
            "what_to_watch_next": [],
        }

    if verb == "watchlist":
        tickers = _normalized_query_tokens(raw_query)[1:]
        return {
            "error": message,
            "tickers": tickers,
            "portfolio_summary": f"Watchlist failed: {message}",
            "ticker_summaries": [],
            "macro_risks": [],
            "top_opportunities": [],
        }

    return {
        "error": message,
        "ticker": ticker,
        "generated_at": None,
        "bias": "Neutral",
        "buy_zone": "N/A",
        "stop_loss": "N/A",
        "take_profit": "N/A",
        "confidence": 0,
        "reasoning": [f"Trade mode failed: {message}"],
    }


def partial_output_snapshot(
    raw_query: str,
    stage: str,
    plan: Any = None,
    tool_results: Any = None,
    evidence: Any = None,
) -> dict | None:
    verb, ticker = query_parts(raw_query)

    if verb == "research":
        if stage == "planning":
            count = len(plan.tool_calls) if plan else 0
            return {
                "ticker": ticker,
                "fundamental_summary": f"Research plan ready for {ticker}. Collecting {count} evidence sources.",
                "recent_news_summary": "Gathering recent headlines and catalyst context.",
                "bull_case": "",
                "bear_case": "",
                "what_to_watch_next": [],
                "overall_sentiment": "NEUTRAL",
            }
        if stage == "tools":
            successful = sum(1 for result in (tool_results or []) if getattr(result, "success", False))
            total = len(tool_results or [])
            return {
                "ticker": ticker,
                "fundamental_summary": f"Collected {successful}/{total} tool responses for {ticker}.",
                "recent_news_summary": "Combining fundamentals, market data, news, and earnings into a draft research view.",
                "bull_case": "",
                "bear_case": "",
                "what_to_watch_next": [],
                "overall_sentiment": "NEUTRAL",
            }
        if stage == "aggregation" and evidence:
            ev = evidence.get_ticker(ticker)
            news_count = len(ev.news) if ev and ev.news else 0
            return {
                "ticker": ticker,
                "fundamental_summary": (
                    f"Evidence aggregated for {ticker}. "
                    f"Fundamentals: {'yes' if ev and ev.fundamentals else 'no'}, "
                    f"market data: {'yes' if ev and ev.market_data else 'no'}, "
                    f"earnings: {'yes' if ev and ev.earnings else 'no'}."
                ),
                "recent_news_summary": f"Loaded {news_count} recent articles for synthesis.",
                "bull_case": "",
                "bear_case": "",
                "what_to_watch_next": [],
                "overall_sentiment": "NEUTRAL",
            }

    if verb == "explain":
        if stage == "planning":
            count = len(plan.tool_calls) if plan else 0
            return {
                "ticker": ticker,
                "price_change_pct": 0,
                "price_move_summary": f"Preparing an explanation for {ticker} using {count} evidence sources.",
                "overall_confidence": 0,
                "ranked_causes": [],
                "what_to_watch_next": [],
            }
        if stage == "tools":
            successful = sum(1 for result in (tool_results or []) if getattr(result, "success", False))
            return {
                "ticker": ticker,
                "price_change_pct": 0,
                "price_move_summary": (
                    f"Collected market context for {ticker}. "
                    f"{successful} tool calls completed; ranking candidate causes next."
                ),
                "overall_confidence": 0,
                "ranked_causes": [],
                "what_to_watch_next": [],
            }
        if stage == "aggregation" and evidence:
            ev = evidence.get_ticker(ticker)
            md = ev.market_data if ev else {}
            price_pct = md.get("price_change_pct_1d", 0) if md else 0
            news_count = len(ev.news) if ev and ev.news else 0
            return {
                "ticker": ticker,
                "price_change_pct": price_pct,
                "price_move_summary": (
                    f"{ticker} moved {price_pct:+.2f}% today. "
                    f"Analyzing {news_count} recent headlines against price and volume data."
                ),
                "overall_confidence": 0,
                "ranked_causes": [],
                "what_to_watch_next": [],
            }

    if verb == "trade":
        if stage == "planning":
            count = len(plan.tool_calls) if plan else 0
            return {
                "ticker": ticker,
                "bias": "Neutral",
                "buy_zone": "Gathering data...",
                "stop_loss": "Pending",
                "take_profit": "Pending",
                "confidence": 0,
                "reasoning": [f"Trade plan ready for {ticker}. Pulling {count} evidence sources."],
            }
        if stage == "tools":
            successful = sum(1 for result in (tool_results or []) if getattr(result, "success", False))
            return {
                "ticker": ticker,
                "bias": "Neutral",
                "buy_zone": "Evaluating setup",
                "stop_loss": "Evaluating risk",
                "take_profit": "Evaluating upside",
                "confidence": 0,
                "reasoning": [f"Collected {successful} tool responses. Drafting the trade setup."],
            }
        if stage == "aggregation" and evidence:
            ev = evidence.get_ticker(ticker)
            md = ev.market_data if ev else {}
            current = md.get("current_price", 0) if md else 0
            return {
                "ticker": ticker,
                "bias": "Neutral",
                "buy_zone": f"Current reference: ${current:.2f}" if current else "Current price unavailable",
                "stop_loss": "Finalizing",
                "take_profit": "Finalizing",
                "confidence": 0,
                "reasoning": ["Evidence aggregated. The final trade decision is being synthesized."],
            }

    return None


def build_sse_response(raw_query: str, event_source) -> StreamingResponse:
    def event_stream():
        try:
            for event in event_source(raw_query):
                if event["type"] == "final_output":
                    safe_event = {
                        "type": "final_output",
                        "elapsed": event["elapsed"],
                        "data": serialize_output(event["data"]),
                    }
                else:
                    safe_event = event
                yield f"data: {json.dumps(safe_event, default=str)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            safe_event = {
                "type": "final_output",
                "elapsed": 0,
                "data": error_output(raw_query, exc),
            }
            yield f"data: {json.dumps(safe_event, default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
