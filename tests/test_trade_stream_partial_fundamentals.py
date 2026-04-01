from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TradeStreamPartialFundamentalsTest(unittest.TestCase):
    def test_trade_stream_completes_when_fundamentals_lack_top_level_market(self) -> None:
        from backend.pipeline.orchestrator import stream_pipeline_events
        from backend.schemas.intent_schema import AnalysisMode, IntentOutput
        from backend.schemas.output_schema import TradingDecisionOutput
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
        from backend.tools.fundamentals_tool import CompanyProfile
        from backend.tools.market_data_tool import MarketDataResponse

        intent = IntentOutput(
            mode=AnalysisMode.TRADE,
            tickers=["2330.TW"],
            confidence=0.96,
            reasoning="trade verb detected",
        )
        plan = ExecutionPlan(
            mode=AnalysisMode.TRADE,
            tickers=["2330.TW"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.MARKET_DATA,
                    ticker="2330.TW",
                    params={},
                    priority=1,
                    rationale="Need price context",
                ),
                ToolCallSpec(
                    tool=ToolName.FUNDAMENTALS,
                    ticker="2330.TW",
                    params={},
                    priority=2,
                    rationale="Need company context",
                ),
            ],
            analysis_focus="Generate a trade setup",
            expected_outputs=["bias", "buy_zone", "stop_loss", "take_profit"],
        )

        market_data = MarketDataResponse(
            ticker="2330.TW",
            market="TW",
            as_of="2026-03-31T00:00:00Z",
            current_price=950.0,
            price_change_1d=12.0,
            price_change_pct_1d=1.28,
            price_change_1w=24.0,
            price_change_pct_1w=2.59,
            price_change_1m=35.0,
            price_change_pct_1m=3.82,
            volume_today=1000000,
            avg_volume_30d=800000,
            volume_ratio=1.25,
            market_cap_billions=750.0,
            beta=1.1,
            week_52_high=980.0,
            week_52_low=620.0,
            ohlc_history=[],
            technicals=None,
        )
        fundamentals = SimpleNamespace(
            profile=CompanyProfile(
                name="Taiwan Semiconductor Manufacturing Co.",
                market="TW",
                sector="Technology",
                industry="Semiconductors",
                exchange="TAI",
                description="Chip foundry.",
                employees=0,
                founded="Unknown",
                headquarters="Hsinchu, Taiwan",
                ceo="Unknown",
            ),
            valuation=None,
            income_statement=None,
            balance_sheet=None,
            estimates=None,
            competitive_advantages=["Scale and process leadership"],
            key_risks=["Cyclical semiconductor demand"],
        )
        output = TradingDecisionOutput(
            ticker="2330.TW",
            bias="Bullish",
            buy_zone="930-945",
            stop_loss="905",
            take_profit="980-1000",
            confidence=68,
            reasoning=["Strong price trend", "Fundamentals remain constructive"],
        )

        with patch("backend.pipeline.orchestrator.trace_intent", return_value=intent), patch(
            "backend.pipeline.orchestrator.plan_from_intent", return_value=plan
        ), patch(
            "backend.services.tool_router.fetch_market_data", return_value=market_data
        ), patch(
            "backend.services.tool_router.fetch_fundamentals", return_value=fundamentals
        ), patch(
            "backend.pipeline.orchestrator.trace_synthesis", return_value=output
        ):
            events = list(stream_pipeline_events("trade 2330.TW"))

        tool_results = [event for event in events if event["type"] == "tool_result"]
        fundamentals_event = next(event for event in tool_results if event["tool"] == "fundamentals")
        final_event = next(event for event in events if event["type"] == "final_output")

        self.assertTrue(fundamentals_event["success"])
        self.assertEqual(fundamentals_event["data"]["data"]["market"], "TW")
        self.assertEqual(final_event["data"].ticker, "2330.TW")
        self.assertEqual(final_event["data"].bias, "Bullish")


if __name__ == "__main__":
    unittest.main()
