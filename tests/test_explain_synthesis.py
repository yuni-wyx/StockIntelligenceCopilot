from __future__ import annotations

import unittest

from backend.chains.synthesis_chain import _synthesise_price_movement
from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
from backend.schemas.planner_schema import ExecutionPlan


class ExplainSynthesisDataHonestyTest(unittest.TestCase):
    def test_missing_market_data_does_not_become_zero_price_move(self) -> None:
        evidence = AggregatedEvidence(
            mode="price_movement",
            tickers_evidence={"AAPL": TickerEvidence(ticker="AAPL")},
            total_tool_calls=5,
            successful_calls=0,
        )
        plan = ExecutionPlan(
            mode="price_movement",
            tickers=["AAPL"],
            tool_calls=[],
            analysis_focus="Explain the price move",
            expected_outputs=["price_move_summary"],
        )

        output = _synthesise_price_movement(evidence, plan)

        self.assertIn("current price movement unavailable", output.price_move_summary)
        self.assertIn("could not be determined", output.price_move_summary)
        self.assertNotIn("$0.00", output.price_move_summary)
        self.assertNotIn("rallied +0.00%", output.price_move_summary)
        self.assertEqual(
            output.volume_context,
            "Volume context unavailable because market data was not available.",
        )


if __name__ == "__main__":
    unittest.main()
