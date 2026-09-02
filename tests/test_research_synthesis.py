from __future__ import annotations

import unittest

from backend.chains.synthesis_chain import _synthesise_research
from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
from backend.schemas.planner_schema import ExecutionPlan


class ResearchSynthesisEvidenceGapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = ExecutionPlan(
            mode="stock_research",
            tickers=["NVDA"],
            tool_calls=[],
            analysis_focus="Research evidence quality",
            expected_outputs=["bull_case", "bear_case"],
        )

    def test_directional_cases_explain_missing_current_context(self) -> None:
        evidence = AggregatedEvidence(
            mode="stock_research",
            tickers_evidence={
                "NVDA": TickerEvidence(
                    ticker="NVDA",
                    news=[{"title": "Recent headline", "sentiment": "neutral"}],
                )
            },
            total_tool_calls=5,
            successful_calls=1,
        )

        output = _synthesise_research(
            evidence,
            self.plan,
            runtime_signals={
                "__research_evidence": {
                    "facts": [{"metric": "Revenue", "value": 215.9}]
                }
            },
        )

        self.assertIn(
            "Available evidence: historical SEC filing facts, recent news.",
            output.bull_case,
        )
        self.assertIn(
            "Missing: current fundamentals, market context, earnings context.",
            output.bull_case,
        )
        self.assertIn("not sufficient to establish this case", output.bear_case)
        self.assertNotEqual(output.bull_case, "Insufficient data for bull case.")
        self.assertNotEqual(output.bear_case, "Insufficient data for bear case.")

    def test_grounded_positive_driver_still_takes_precedence(self) -> None:
        evidence = AggregatedEvidence(
            mode="stock_research",
            tickers_evidence={
                "NVDA": TickerEvidence(
                    ticker="NVDA",
                    fundamentals={"competitive_advantages": ["Scale advantage"]},
                )
            },
            total_tool_calls=1,
            successful_calls=1,
        )

        output = _synthesise_research(evidence, self.plan)

        self.assertEqual(output.bull_case, "BULL CASE: Scale advantage")


if __name__ == "__main__":
    unittest.main()
