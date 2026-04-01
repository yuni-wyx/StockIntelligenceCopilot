from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ReasoningTimelineTest(unittest.TestCase):
    def test_stream_pipeline_events_emits_high_level_timeline_steps(self) -> None:
        from backend.pipeline.orchestrator import stream_pipeline_events
        from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence, ToolResult
        from backend.schemas.intent_schema import AnalysisMode, IntentOutput
        from backend.schemas.output_schema import PriceMovementOutput
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName

        intent = IntentOutput(
            mode=AnalysisMode.PRICE_MOVEMENT,
            tickers=["TSLA"],
            confidence=0.95,
            reasoning="explain verb detected",
        )
        plan = ExecutionPlan(
            mode=AnalysisMode.PRICE_MOVEMENT,
            tickers=["TSLA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.MARKET_DATA,
                    ticker="TSLA",
                    params={},
                    priority=1,
                    rationale="Need price action",
                )
            ],
            analysis_focus="Explain the move",
            expected_outputs=["price_move_summary"],
        )
        tool_results = [
            ToolResult(
                tool="market_data",
                ticker="TSLA",
                success=True,
                data={"price_change_pct_1d": 1.2},
            )
        ]
        evidence = AggregatedEvidence(
            mode="price_movement",
            tickers_evidence={
                "TSLA": TickerEvidence(
                    ticker="TSLA",
                    market_data={"price_change_pct_1d": 1.2},
                )
            },
            total_tool_calls=1,
            successful_calls=1,
        )
        output = PriceMovementOutput(
            ticker="TSLA",
            price_move_summary="TSLA rose on strong deliveries.",
            price_change_pct=1.2,
            volume_context="Volume was healthy.",
            ranked_causes=[],
            overall_confidence=0.4,
            what_to_watch_next=[],
        )

        with (
            patch("backend.pipeline.orchestrator.trace_intent", return_value=intent),
            patch("backend.pipeline.orchestrator.plan_from_intent", return_value=plan),
            patch(
                "backend.pipeline.orchestrator.trace_tool_routing",
                return_value=tool_results,
            ),
            patch("backend.pipeline.orchestrator.trace_aggregate", return_value=evidence),
            patch("backend.pipeline.orchestrator.trace_synthesis", return_value=output),
        ):
            events = list(stream_pipeline_events("explain TSLA"))

        timeline = [event for event in events if event["type"] == "timeline_step"]
        self.assertEqual(
            [event["step"] for event in timeline if event["status"] == "completed"],
            [
                "query_interpretation",
                "planning",
                "evidence_retrieval",
                "synthesis",
                "final_answer",
            ],
        )
        self.assertTrue(all("summary" in event for event in timeline))
        self.assertTrue(all("timestamp" in event for event in timeline))


if __name__ == "__main__":
    unittest.main()
