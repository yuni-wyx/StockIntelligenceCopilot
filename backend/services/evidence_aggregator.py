"""
Evidence Aggregator
--------------------
Stage 5 of the pipeline.

Input  : List[ToolResult] + ExecutionPlan
Output : AggregatedEvidence

Groups raw tool results by ticker and tool type into structured
TickerEvidence bundles, ready for the Synthesis Chain.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

try:
    from ..schemas.evidence_schema import (
        AggregatedEvidence,
        SourceMetadata,
        TickerEvidence,
        ToolResult,
    )
    from ..schemas.planner_schema import ExecutionPlan, ToolName
except ImportError:
    from schemas.evidence_schema import (
        AggregatedEvidence,
        SourceMetadata,
        TickerEvidence,
        ToolResult,
    )
    from schemas.planner_schema import ExecutionPlan, ToolName


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_id(source_type: str, ticker: str, suffix: str = "primary") -> str:
    return f"{source_type}:{ticker}:{suffix}"


def _source_metadata_for_result(result: ToolResult) -> list[SourceMetadata]:
    if not result.success:
        return []

    ticker = result.ticker.upper()
    retrieved_at = _now_iso()
    if result.tool == ToolName.MARKET_DATA.value:
        return [
            SourceMetadata(
                source_id=_source_id("market_data", ticker),
                source_type="market_data",
                ticker=ticker,
                provider="market data tool",
                tool=result.tool,
                confidence=0.85,
                retrieved_at=retrieved_at,
                fields=sorted(result.data.keys()),
            )
        ]

    if result.tool == ToolName.FUNDAMENTALS.value:
        sources = [
            SourceMetadata(
                source_id=_source_id("fundamentals", ticker),
                source_type="fundamentals",
                ticker=ticker,
                provider="yfinance",
                tool=result.tool,
                confidence=0.75,
                retrieved_at=retrieved_at,
                fields=sorted(result.data.keys()),
            )
        ]
        estimates = result.data.get("estimates")
        if estimates:
            sources.append(
                SourceMetadata(
                    source_id=_source_id("analyst_signal", ticker),
                    source_type="analyst_signal",
                    ticker=ticker,
                    provider="yfinance analyst estimates",
                    tool=result.tool,
                    confidence=0.65,
                    retrieved_at=retrieved_at,
                    fields=sorted(estimates.keys()) if isinstance(estimates, dict) else [],
                )
            )
        return sources

    if result.tool == ToolName.NEWS.value:
        sources = []
        for index, article in enumerate(result.data.get("articles", []), start=1):
            relevance = article.get("relevance_score", 0.6)
            sources.append(
                SourceMetadata(
                    source_id=_source_id("news", ticker, str(index)),
                    source_type="news",
                    ticker=ticker,
                    provider=article.get("source"),
                    title=article.get("title"),
                    url=article.get("url"),
                    published_at=article.get("published_at"),
                    tool=result.tool,
                    confidence=max(0.35, min(float(relevance or 0.6), 0.9)),
                    retrieved_at=retrieved_at,
                    fields=["title", "source", "url", "published_at", "sentiment"],
                )
            )
        return sources

    if result.tool == ToolName.EARNINGS.value:
        return [
            SourceMetadata(
                source_id=_source_id("earnings", ticker),
                source_type="earnings",
                ticker=ticker,
                provider="earnings tool",
                tool=result.tool,
                confidence=0.7,
                retrieved_at=retrieved_at,
                fields=sorted(result.data.keys()),
            )
        ]

    return []


class EvidenceAggregator:
    """
    Merges a flat list of ToolResults into a ticker-keyed AggregatedEvidence.

    Usage:
        aggregator = EvidenceAggregator()
        evidence = aggregator.aggregate(tool_results, plan)
    """

    def aggregate(
        self, results: List[ToolResult], plan: ExecutionPlan
    ) -> AggregatedEvidence:
        # Initialise one TickerEvidence per ticker in scope
        ticker_map: dict[str, TickerEvidence] = {
            t: TickerEvidence(ticker=t) for t in plan.tickers
        }

        successful = 0
        source_metadata: list[SourceMetadata] = []
        for result in results:
            ticker = result.ticker.upper()

            # Guard: ensure ticker is in scope (shouldn't fail, but be safe)
            if ticker not in ticker_map:
                ticker_map[ticker] = TickerEvidence(ticker=ticker)

            ev = ticker_map[ticker]

            if not result.success:
                ev.tool_errors.append(
                    f"[{result.tool}] {result.error or 'Unknown error'}"
                )
                continue

            successful += 1
            result_sources = _source_metadata_for_result(result)
            source_metadata.extend(result_sources)
            ev.source_metadata.extend(result_sources)
            tool = ToolName(result.tool)

            if tool == ToolName.MARKET_DATA:
                ev.market_data = result.data

            elif tool == ToolName.FUNDAMENTALS:
                ev.fundamentals = result.data

            elif tool == ToolName.NEWS:
                ev.news = result.data.get("articles", [])
                # Attach top-level sentiment fields alongside raw articles
                if ev.news is not None:
                    # Merge sentiment metadata into news dict so synthesis
                    # can access overall_sentiment / avg_sentiment_score easily.
                    ev.news = result.data.get("articles", [])
                    ev.market_data = ev.market_data or {}
                    # Store news metadata separately in market_data to avoid
                    # schema conflicts — or just keep articles list on ev.news.

            elif tool == ToolName.EARNINGS:
                ev.earnings = result.data

        return AggregatedEvidence(
            mode=plan.mode,
            tickers_evidence=ticker_map,
            total_tool_calls=len(results),
            successful_calls=successful,
            source_metadata=source_metadata,
            confidence_score=round(successful / len(results), 2) if results else 0.0,
        )
