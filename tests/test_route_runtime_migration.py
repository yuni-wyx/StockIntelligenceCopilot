from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _agent_result_for_output(task_type, raw_query, tickers, output):
    from backend.schemas.agent import (
        AgentEvidenceBundle,
        AgentPlan,
        AgentResult,
        AgentTask,
    )

    return AgentResult(
        task=AgentTask(task_type=task_type, raw_query=raw_query, tickers=tickers),
        plan=AgentPlan(task_type=task_type, summary=raw_query, expected_outputs=["output"]),
        evidence=AgentEvidenceBundle(context={"raw_query": raw_query}),
        output=output,
        output_type=type(output).__name__,
    )


class RouteRuntimeMigrationTest(unittest.TestCase):
    def test_research_route_uses_runtime(self) -> None:
        from backend.main import ResearchRequest, api_research
        from backend.schemas.agent import AgentTaskType
        from backend.schemas.output_schema import StockResearchOutput

        output = StockResearchOutput(
            ticker="TSLA",
            fundamental_summary="Summary",
            recent_news_summary="News",
            bull_case="Bull",
            bear_case="Bear",
            what_to_watch_next=[],
            overall_sentiment="NEUTRAL",
        )
        result = _agent_result_for_output(
            AgentTaskType.RESEARCH,
            "research TSLA",
            ["TSLA"],
            output,
        )

        with patch("backend.main.execute_agent_task", return_value=result) as runtime_mock, patch(
            "backend.main.execute_pipeline"
        ) as legacy_mock:
            payload = api_research(ResearchRequest(ticker="tsla"))

        self.assertEqual(payload["ticker"], "TSLA")
        runtime_mock.assert_called_once()
        legacy_mock.assert_not_called()

    def test_trade_route_uses_runtime(self) -> None:
        from backend.main import TradeRequest, api_trade
        from backend.schemas.agent import AgentTaskType
        from backend.schemas.output_schema import TradingDecisionOutput

        output = TradingDecisionOutput(
            ticker="TSLA",
            bias="Neutral",
            buy_zone="Current reference: $100.00",
            stop_loss="$95.00",
            take_profit="$108.00",
            confidence=42,
            reasoning=["Grounded setup."],
        )
        result = _agent_result_for_output(
            AgentTaskType.TRADE,
            "trade TSLA",
            ["TSLA"],
            output,
        )

        with patch("backend.main.execute_agent_task", return_value=result) as runtime_mock:
            payload = api_trade(TradeRequest(ticker="tsla"))

        self.assertEqual(payload["ticker"], "TSLA")
        task = runtime_mock.call_args.args[0]
        self.assertEqual(task.raw_query, "trade TSLA")

    def test_watchlist_route_uses_runtime(self) -> None:
        from backend.main import WatchlistRequest, api_watchlist
        from backend.schemas.agent import AgentTaskType
        from backend.schemas.output_schema import WatchlistMonitorOutput

        output = WatchlistMonitorOutput(
            tickers=["TSLA", "2330.TW"],
            portfolio_summary="Summary",
            ticker_summaries=[],
            macro_risks=[],
            top_opportunities=[],
        )
        result = _agent_result_for_output(
            AgentTaskType.WATCHLIST,
            "watchlist TSLA 2330.TW",
            ["TSLA", "2330.TW"],
            output,
        )

        with patch("backend.main.execute_agent_task", return_value=result):
            payload = api_watchlist(WatchlistRequest(tickers=["tsla", "台積電"]))

        self.assertEqual(payload["tickers"], ["TSLA", "2330.TW"])

    def test_runtime_failure_falls_back_to_legacy_pipeline(self) -> None:
        from backend.main import ExplainRequest, api_explain
        from backend.schemas.output_schema import PriceMovementOutput

        legacy_output = PriceMovementOutput(
            ticker="TSLA",
            price_move_summary="Fallback explain result.",
            price_change_pct=2.0,
            volume_context="Above average volume.",
            ranked_causes=[],
            overall_confidence=0.4,
            what_to_watch_next=[],
        )

        with patch(
            "backend.main.execute_agent_task",
            side_effect=RuntimeError("runtime down"),
        ), patch(
            "backend.main.execute_pipeline",
            return_value=legacy_output,
        ) as legacy_mock:
            payload = api_explain(ExplainRequest(ticker="tsla"))

        legacy_mock.assert_called_once_with("explain TSLA")
        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["price_move_summary"], "Fallback explain result.")

    def test_runtime_and_fallback_failure_returns_500(self) -> None:
        from fastapi.testclient import TestClient

        from backend.main import app

        with patch(
            "backend.main.execute_agent_task",
            side_effect=RuntimeError("runtime down"),
        ), patch(
            "backend.main.execute_pipeline",
            side_effect=RuntimeError("fallback down"),
        ):
            response = TestClient(app).post("/api/explain", json={"ticker": "tsla"})

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["error"], "runtime down")
        self.assertIn("Explain mode failed", payload["price_move_summary"])

    def test_fallback_provider_failure_returns_502(self) -> None:
        from fastapi.testclient import TestClient

        from backend.main import app

        with patch(
            "backend.main.execute_agent_task",
            side_effect=RuntimeError("runtime down"),
        ), patch(
            "backend.main.execute_pipeline",
            side_effect=ConnectionError("provider unavailable"),
        ):
            response = TestClient(app).post("/api/research", json={"ticker": "tsla"})

        self.assertEqual(response.status_code, 502)
        payload = response.json()
        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["error"], "runtime down")
        self.assertIn("Research failed", payload["fundamental_summary"])

    def test_user_input_runtime_error_returns_400_without_fallback(self) -> None:
        from fastapi.testclient import TestClient

        from backend.main import app

        with patch(
            "backend.main.execute_agent_task",
            side_effect=ValueError("No current portfolio is saved."),
        ):
            response = TestClient(app).post(
                "/api/portfolio/analyze",
                json={"holdings": [{"ticker": "00878"}]},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"], "No current portfolio is saved.")
        self.assertEqual(payload["ticker"], "")

    def test_streaming_routes_and_portfolio_routes_remain_available(self) -> None:
        from backend.main import app

        routes = {
            (method, route.path)
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
        }

        expected = {
            ("POST", "/api/research/stream"),
            ("POST", "/api/explain/stream"),
            ("POST", "/api/trade/stream"),
            ("POST", "/api/portfolio/analyze"),
            ("POST", "/api/portfolio/scenario"),
            ("POST", "/api/portfolio/scenarios/compare"),
            ("POST", "/api/portfolio/agent"),
        }
        self.assertTrue(expected.issubset(routes))

    def test_research_stream_route_uses_runtime_streaming_adapter(self) -> None:
        from backend.main import ResearchRequest, api_research_stream

        sentinel = object()
        request = object()
        with patch(
            "backend.main.build_agent_streaming_response",
            return_value=sentinel,
        ) as streaming_mock:
            response = api_research_stream(ResearchRequest(ticker="tsla"), request)

        self.assertIs(response, sentinel)
        task = streaming_mock.call_args.args[0]
        self.assertEqual(task.raw_query, "research TSLA")
        self.assertIs(streaming_mock.call_args.kwargs["request"], request)

    def test_explain_stream_route_uses_runtime_streaming_adapter(self) -> None:
        from backend.main import ExplainRequest, api_explain_stream

        sentinel = object()
        request = object()
        with patch(
            "backend.main.build_agent_streaming_response",
            return_value=sentinel,
        ) as streaming_mock:
            response = api_explain_stream(ExplainRequest(ticker="台積電"), request)

        self.assertIs(response, sentinel)
        task = streaming_mock.call_args.args[0]
        self.assertEqual(task.raw_query, "explain 2330.TW")
        self.assertIs(streaming_mock.call_args.kwargs["request"], request)

    def test_trade_stream_route_uses_runtime_streaming_adapter(self) -> None:
        from backend.main import TradeRequest, api_trade_stream

        sentinel = object()
        request = object()
        with patch(
            "backend.main.build_agent_streaming_response",
            return_value=sentinel,
        ) as streaming_mock:
            response = api_trade_stream(TradeRequest(ticker="2330"), request)

        self.assertIs(response, sentinel)
        task = streaming_mock.call_args.args[0]
        self.assertEqual(task.raw_query, "trade 2330.TW")
        self.assertIs(streaming_mock.call_args.kwargs["request"], request)

    def test_no_watchlist_stream_route_is_added(self) -> None:
        from backend.main import app

        routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "POST" in route.methods
        }
        self.assertNotIn("/api/watchlist/stream", routes)


if __name__ == "__main__":
    unittest.main()
