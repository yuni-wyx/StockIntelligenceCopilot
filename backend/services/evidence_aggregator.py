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

from typing import List

try:
    from ..schemas.evidence_schema import AggregatedEvidence, TickerEvidence, ToolResult
    from ..schemas.planner_schema import ExecutionPlan, ToolName
except ImportError:
    from schemas.evidence_schema import AggregatedEvidence, TickerEvidence, ToolResult
    from schemas.planner_schema import ExecutionPlan, ToolName


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
        )
