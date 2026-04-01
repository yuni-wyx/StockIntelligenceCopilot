from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FailingChain:
    def invoke(self, _payload):
        raise RuntimeError("Connection error.")


class TradeSynthesisFallbackTest(unittest.TestCase):
    def test_execute_pipeline_trade_uses_heuristic_setup_by_default(self) -> None:
        from backend.pipeline.orchestrator import execute_pipeline
        from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
        from backend.schemas.intent_schema import AnalysisMode, IntentOutput
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName

        intent = IntentOutput(
            mode=AnalysisMode.TRADE,
            tickers=["TSLA"],
            confidence=0.95,
            reasoning="trade verb detected",
        )
        plan = ExecutionPlan(
            mode=AnalysisMode.TRADE,
            tickers=["TSLA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.MARKET_DATA,
                    ticker="TSLA",
                    params={},
                    priority=1,
                    rationale="Need price context",
                ),
                ToolCallSpec(
                    tool=ToolName.NEWS,
                    ticker="TSLA",
                    params={},
                    priority=2,
                    rationale="Need catalyst context",
                ),
                ToolCallSpec(
                    tool=ToolName.FUNDAMENTALS,
                    ticker="TSLA",
                    params={},
                    priority=3,
                    rationale="Need company context",
                ),
                ToolCallSpec(
                    tool=ToolName.EARNINGS,
                    ticker="TSLA",
                    params={},
                    priority=4,
                    rationale="Need event risk context",
                ),
            ],
            analysis_focus="Generate a trade setup",
            expected_outputs=["bias", "buy_zone", "stop_loss", "take_profit"],
        )
        evidence = AggregatedEvidence(
            mode="trade",
            tickers_evidence={
                "TSLA": TickerEvidence(
                    ticker="TSLA",
                    market_data={
                        "current_price": 371.75,
                        "price_change_pct_1d": 1.2,
                        "price_change_pct_1m": 4.5,
                    },
                    fundamentals={
                        "competitive_advantages": ["Brand strength and scale"],
                        "key_risks": ["Execution risk"],
                    },
                    news=[
                        {"sentiment": "positive", "title": "Tesla delivery update"},
                    ],
                    earnings={
                        "days_to_next_earnings": 18,
                    },
                )
            },
            total_tool_calls=4,
            successful_calls=4,
        )

        with patch("backend.pipeline.orchestrator.classify_and_plan", return_value=(intent, plan)), patch(
            "backend.pipeline.orchestrator.retrieve_evidence", return_value=([], evidence)
        ):
            output = execute_pipeline("trade TSLA")

        self.assertEqual(output.ticker, "TSLA")
        self.assertEqual(output.buy_zone, "Current reference: $371.75")
        self.assertNotEqual(output.stop_loss, "N/A")
        self.assertNotEqual(output.take_profit, "N/A")
        self.assertNotIn("Final synthesis failed:", output.reasoning[-1])

    def test_execute_pipeline_trade_falls_back_to_aggregated_trade_setup_when_llm_fails(self) -> None:
        from backend.pipeline.orchestrator import execute_pipeline
        from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
        from backend.schemas.intent_schema import AnalysisMode, IntentOutput
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName

        intent = IntentOutput(
            mode=AnalysisMode.TRADE,
            tickers=["TSLA"],
            confidence=0.95,
            reasoning="trade verb detected",
        )
        plan = ExecutionPlan(
            mode=AnalysisMode.TRADE,
            tickers=["TSLA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.MARKET_DATA,
                    ticker="TSLA",
                    params={},
                    priority=1,
                    rationale="Need price context",
                )
            ],
            analysis_focus="Generate a trade setup",
            expected_outputs=["bias", "buy_zone", "stop_loss", "take_profit"],
        )
        evidence = AggregatedEvidence(
            mode="trade",
            tickers_evidence={
                "TSLA": TickerEvidence(
                    ticker="TSLA",
                    market_data={
                        "current_price": 371.75,
                        "price_change_pct_1d": 1.2,
                        "price_change_pct_1m": 4.5,
                    },
                )
            },
            total_tool_calls=1,
            successful_calls=1,
        )

        with patch.dict("os.environ", {"ENABLE_LLM_TRADE_SYNTHESIS": "true"}, clear=False), patch(
            "backend.pipeline.orchestrator.classify_and_plan", return_value=(intent, plan)
        ), patch(
            "backend.pipeline.orchestrator.retrieve_evidence", return_value=([], evidence)
        ), patch(
            "backend.chains.synthesis_chain.build_llm_synthesis_chain", return_value=_FailingChain()
        ):
            output = execute_pipeline("trade TSLA")

        self.assertEqual(output.buy_zone, "Current reference: $371.75")
        self.assertIn("Final synthesis failed: Connection error.", output.reasoning[-1])


if __name__ == "__main__":
    unittest.main()
