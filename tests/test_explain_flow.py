from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ExplainFlowRegressionTest(unittest.TestCase):
    def test_api_explain_works_via_package_import(self) -> None:
        from backend.main import ExplainRequest, api_explain
        from backend.schemas.output_schema import PriceMovementOutput, RankedCause, WatchPoint

        mocked_output = PriceMovementOutput(
            ticker="TSLA",
            price_move_summary="TSLA rallied after a product update.",
            price_change_pct=4.2,
            volume_context="Volume was elevated versus the 30-day average.",
            ranked_causes=[
                RankedCause(
                    rank=1,
                    cause="News catalyst",
                    explanation="A product announcement drove the move.",
                    supporting_evidence=["Headline matched the ticker move."],
                    confidence=0.82,
                    confidence_label="HIGH",
                )
            ],
            overall_confidence=0.82,
            what_to_watch_next=[
                WatchPoint(
                    item="Next session volume",
                    reason="Confirms whether the move has follow-through.",
                    timeframe="1 day",
                )
            ],
        )

        with patch("backend.main.execute_pipeline", return_value=mocked_output) as execute_mock:
            response = api_explain(ExplainRequest(ticker="tsla"))

        execute_mock.assert_called_once_with("explain TSLA")
        self.assertEqual(response["ticker"], "TSLA")
        self.assertEqual(response["price_move_summary"], mocked_output.price_move_summary)
        self.assertEqual(response["ranked_causes"][0]["cause"], "News catalyst")
        self.assertEqual(response["what_to_watch_next"][0]["item"], "Next session volume")

    def test_api_explain_normalizes_taiwan_aliases(self) -> None:
        from backend.main import ExplainRequest, api_explain
        from backend.schemas.output_schema import PriceMovementOutput

        mocked_output = PriceMovementOutput(
            ticker="2330.TW",
            price_move_summary="2330.TW moved on semiconductor demand expectations.",
            price_change_pct=1.8,
            volume_context="Volume was steady.",
            ranked_causes=[],
            overall_confidence=0.4,
            what_to_watch_next=[],
        )

        with patch("backend.main.execute_pipeline", return_value=mocked_output) as execute_mock:
            response = api_explain(ExplainRequest(ticker="台積電"))

        execute_mock.assert_called_once_with("explain 2330.TW")
        self.assertEqual(response["ticker"], "2330.TW")


if __name__ == "__main__":
    unittest.main()
