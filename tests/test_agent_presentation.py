from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AgentPresentationTest(unittest.TestCase):
    def test_agent_result_to_api_response_serializes_existing_shape(self) -> None:
        from backend.api.agent_presentation import agent_result_to_api_response
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.output_schema import TradingDecisionOutput

        result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.TRADE,
                raw_query="trade TSLA",
                tickers=["TSLA"],
            ),
            plan=AgentPlan(
                task_type=AgentTaskType.TRADE,
                summary="Trade TSLA",
                expected_outputs=["trade_setup"],
            ),
            evidence=AgentEvidenceBundle(context={"raw_query": "trade TSLA"}),
            output=TradingDecisionOutput(
                ticker="TSLA",
                bias="Neutral",
                buy_zone="Current reference: $100.00",
                stop_loss="$95.00",
                take_profit="$108.00",
                confidence=40,
                reasoning=["Grounded setup."],
            ),
            output_type="TradingDecisionOutput",
        )

        payload = agent_result_to_api_response(result)
        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["buy_zone"], "Current reference: $100.00")
        self.assertIn("evidence_provenance", payload)
        self.assertIn("claim_evidence", payload)
        self.assertIn("unsupported_claims", payload)
        self.assertIn("confidence_score", payload)

    def test_agent_exception_to_api_error_preserves_legacy_error_shape(self) -> None:
        from backend.api.agent_presentation import agent_exception_to_api_error
        from backend.schemas.agent import AgentTask, AgentTaskType

        payload = agent_exception_to_api_error(
            AgentTask(
                task_type=AgentTaskType.EXPLAIN,
                raw_query="explain TSLA",
                tickers=["TSLA"],
            ),
            RuntimeError("boom"),
        )

        self.assertEqual(payload["ticker"], "TSLA")
        self.assertIn("Explain mode failed", payload["price_move_summary"])

    def test_agent_result_links_generated_fields_to_evidence(self) -> None:
        from backend.api.agent_presentation import agent_result_to_api_response
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
        from backend.schemas.output_schema import TradingDecisionOutput

        result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.TRADE,
                raw_query="trade TSLA",
                tickers=["TSLA"],
            ),
            plan=AgentPlan(
                task_type=AgentTaskType.TRADE,
                summary="Trade TSLA",
                expected_outputs=["trade_setup"],
            ),
            evidence=AgentEvidenceBundle(
                context={"raw_query": "trade TSLA"},
                legacy_evidence=AggregatedEvidence(
                    mode="trade",
                    tickers_evidence={
                        "TSLA": TickerEvidence(
                            ticker="TSLA",
                            market_data={"current_price": 100.0},
                            fundamentals={"profile": {"name": "Tesla"}},
                            news=[
                                {
                                    "title": "Tesla update",
                                    "source": "Example News",
                                    "url": "https://example.com/tsla",
                                    "published_at": "2026-06-03T00:00:00Z",
                                    "relevance_score": 0.8,
                                }
                            ],
                            signal={
                                "ticker": "TSLA",
                                "benchmark": "SPY",
                                "horizon_days": 30,
                                "signal_score": 61.0,
                                "signal_band": "Strong",
                                "confidence": "Medium",
                                "positive_signals": ["Relative strength is positive."],
                                "negative_signals": [],
                                "data_caveats": [],
                                "disclaimer": "Deterministic signal only.",
                                "feature_snapshot": {"relative_return_20d": 7.1},
                            },
                        )
                    },
                    total_tool_calls=3,
                    successful_calls=3,
                ),
            ),
            output=TradingDecisionOutput(
                ticker="TSLA",
                bias="Neutral",
                buy_zone="Current reference: $100.00",
                stop_loss="$95.00",
                take_profit="$108.00",
                confidence=40,
                reasoning=["Grounded setup."],
            ),
            output_type="TradingDecisionOutput",
        )

        payload = agent_result_to_api_response(result)

        self.assertGreaterEqual(len(payload["evidence_provenance"]), 3)
        linked_fields = {
            item["output_field"]
            for item in payload["claim_evidence"]
            if item["evidence_ids"]
        }
        self.assertIn("buy_zone", linked_fields)
        self.assertIn("reasoning", linked_fields)
        source_types = {item["source_type"] for item in payload["evidence_provenance"]}
        self.assertIn("signal", source_types)

    def test_unsupported_claim_detection_flags_unsafe_certainty(self) -> None:
        from backend.services.evidence_provenance import build_claim_evidence

        claims, unsupported, confidence = build_claim_evidence(
            {"summary": "This trade is guaranteed to work."},
            [],
        )

        self.assertEqual(confidence, 0.0)
        self.assertTrue(claims[0].unsupported)
        self.assertGreaterEqual(len(unsupported), 2)
        self.assertTrue(any("guarantee" in item.reason for item in unsupported))

    def test_all_provider_failures_return_http_502(self) -> None:
        from backend.api.agent_presentation import agent_result_to_api_response
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.evidence_schema import AggregatedEvidence, TickerEvidence
        from backend.schemas.output_schema import StockResearchOutput

        result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.RESEARCH,
                raw_query="research TSLA",
                tickers=["TSLA"],
            ),
            plan=AgentPlan(task_type=AgentTaskType.RESEARCH, summary="Research TSLA"),
            evidence=AgentEvidenceBundle(
                legacy_evidence=AggregatedEvidence(
                    mode="stock_research",
                    tickers_evidence={"TSLA": TickerEvidence(ticker="TSLA")},
                    total_tool_calls=2,
                    successful_calls=0,
                )
            ),
            output=StockResearchOutput(
                ticker="TSLA",
                fundamental_summary="Unavailable",
                recent_news_summary="Unavailable",
                bull_case="Unavailable",
                bear_case="Unavailable",
                what_to_watch_next=[],
                overall_sentiment="NEUTRAL",
            ),
            output_type="StockResearchOutput",
        )

        response = agent_result_to_api_response(result)
        self.assertEqual(response.status_code, 502)
        self.assertIn("no grounded result", response.body.decode())


if __name__ == "__main__":
    unittest.main()
