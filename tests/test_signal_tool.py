from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_market_data_response(ticker: str, closes: list[float]):
    from backend.tools.market_data_tool import (
        MarketDataResponse,
        OHLCBar,
        TechnicalIndicators,
    )

    bars = [
        OHLCBar(
            date=f"2026-01-{index + 1:02d}",
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1000 + index,
            vwap=close,
        )
        for index, close in enumerate(closes)
    ]

    technicals = TechnicalIndicators(
        rsi_14=50.0,
        sma_20=closes[-1],
        sma_50=closes[-1],
        ema_12=closes[-1],
        ema_26=closes[-1],
        macd=0.0,
        macd_signal=0.0,
        bollinger_upper=closes[-1],
        bollinger_lower=closes[-1],
        atr_14=1.0,
    )

    return MarketDataResponse(
        ticker=ticker,
        market="US",
        as_of="2026-01-31T00:00:00Z",
        current_price=closes[-1],
        price_change_1d=0.0,
        price_change_pct_1d=0.0,
        price_change_1w=0.0,
        price_change_pct_1w=0.0,
        price_change_1m=0.0,
        price_change_pct_1m=0.0,
        volume_today=bars[-1].volume,
        avg_volume_30d=1000,
        volume_ratio=1.0,
        market_cap_billions=100.0,
        beta=1.0,
        week_52_high=max(closes),
        week_52_low=min(closes),
        ohlc_history=bars,
        technicals=technicals,
    )


class SignalToolTest(unittest.TestCase):
    def test_research_and_explain_plans_include_signal_tool(self) -> None:
        from backend.chains.planner_chain import build_planner_chain
        from backend.schemas.intent_schema import AnalysisMode, IntentOutput
        from backend.schemas.planner_schema import ToolName

        chain = build_planner_chain()
        research_plan = chain.invoke(
            IntentOutput(
                mode=AnalysisMode.STOCK_RESEARCH,
                tickers=["NVDA"],
                confidence=0.9,
                reasoning="research query",
            )
        )
        explain_plan = chain.invoke(
            IntentOutput(
                mode=AnalysisMode.PRICE_MOVEMENT,
                tickers=["NVDA"],
                confidence=0.9,
                reasoning="explain query",
            )
        )

        self.assertIn(ToolName.SIGNAL, [call.tool for call in research_plan.tool_calls])
        self.assertIn(ToolName.SIGNAL, [call.tool for call in explain_plan.tool_calls])

    def test_tool_router_dispatches_signal_tool(self) -> None:
        from backend.schemas.intent_schema import AnalysisMode
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
        from backend.services.tool_router import ToolRouter

        plan = ExecutionPlan(
            mode=AnalysisMode.STOCK_RESEARCH,
            tickers=["NVDA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.SIGNAL,
                    ticker="NVDA",
                    params={"benchmark": "SPY", "horizon_days": 30},
                    priority=1,
                    rationale="Need relative signal estimate.",
                )
            ],
            analysis_focus="Research signal",
            expected_outputs=["signal"],
        )

        ticker_market_data = build_market_data_response("NVDA", list(range(100, 160)))
        benchmark_market_data = build_market_data_response(
            "SPY",
            list(range(100, 130)) + [129.0] * 30,
        )

        with patch(
            "backend.tools.signal_tool.fetch_market_data",
            side_effect=[ticker_market_data, benchmark_market_data],
        ):
            results = ToolRouter().execute(plan)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.success)
        self.assertEqual(result.tool, ToolName.SIGNAL.value)
        self.assertEqual(result.data["ticker"], "NVDA")
        self.assertEqual(result.data["benchmark"], "SPY")
        self.assertIn("signal_score", result.data)
        self.assertIn("feature_snapshot", result.data)
        self.assertIn("data_caveats", result.data)
        self.assertEqual(result.error, None)

    def test_evidence_aggregator_preserves_signal_payload(self) -> None:
        from backend.schemas.evidence_schema import ToolResult
        from backend.schemas.intent_schema import AnalysisMode
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
        from backend.services.evidence_aggregator import EvidenceAggregator

        plan = ExecutionPlan(
            mode=AnalysisMode.STOCK_RESEARCH,
            tickers=["NVDA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.SIGNAL,
                    ticker="NVDA",
                    params={},
                    priority=1,
                    rationale="Need signal",
                )
            ],
            analysis_focus="Research signal",
            expected_outputs=["signal"],
        )
        tool_result = ToolResult(
            tool=ToolName.SIGNAL.value,
            ticker="NVDA",
            success=True,
            data={
                "ticker": "NVDA",
                "benchmark": "SPY",
                "horizon_days": 30,
                "signal_score": 67.5,
                "signal_band": "Strong",
                "confidence": "Medium",
                "positive_signals": ["Relative strength is positive."],
                "negative_signals": [],
                "data_caveats": [],
                "disclaimer": "Deterministic signal only.",
                "feature_snapshot": {"relative_return_20d": 8.7},
            },
        )

        evidence = EvidenceAggregator().aggregate([tool_result], plan)

        self.assertEqual(
            evidence.tickers_evidence["NVDA"].signal["signal_score"], 67.5
        )
        self.assertEqual(evidence.source_metadata[0].source_type, "signal")

    def test_signal_tool_returns_safe_error_for_insufficient_history(self) -> None:
        from backend.schemas.intent_schema import AnalysisMode
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName
        from backend.services.tool_router import ToolRouter

        plan = ExecutionPlan(
            mode=AnalysisMode.STOCK_RESEARCH,
            tickers=["NVDA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.SIGNAL,
                    ticker="NVDA",
                    params={},
                    priority=1,
                    rationale="Need relative signal estimate.",
                )
            ],
            analysis_focus="Research signal",
            expected_outputs=["signal"],
        )

        short_history = build_market_data_response("NVDA", [100.0] * 19)
        benchmark_market_data = build_market_data_response("SPY", [100.0] * 60)

        with patch(
            "backend.tools.signal_tool.fetch_market_data",
            side_effect=[short_history, benchmark_market_data],
        ):
            results = ToolRouter().execute(plan)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertFalse(result.success)
        self.assertEqual(result.data, {})
        self.assertIn("ValueError: Insufficient ticker history", result.error or "")
        self.assertNotIn("Traceback", result.error or "")


if __name__ == "__main__":
    unittest.main()
