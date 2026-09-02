from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RouteAdapterTest(unittest.TestCase):
    def test_security_request_adapters_build_agent_tasks(self) -> None:
        from backend.main import ExplainRequest, ResearchRequest, TradeRequest, WatchlistRequest
        from backend.pipeline.route_adapters import (
            explain_request_to_agent_task,
            research_request_to_agent_task,
            trade_request_to_agent_task,
            watchlist_request_to_agent_task,
        )
        from backend.schemas.agent import AgentTaskType

        research = research_request_to_agent_task(ResearchRequest(ticker="tsla"))
        explain = explain_request_to_agent_task(ExplainRequest(ticker="台積電"))
        trade = trade_request_to_agent_task(TradeRequest(ticker="2330"))
        watchlist = watchlist_request_to_agent_task(
            WatchlistRequest(tickers=["tsla", "台積電"])
        )

        self.assertEqual(research.task_type, AgentTaskType.RESEARCH)
        self.assertEqual(research.raw_query, "research TSLA")
        self.assertEqual(research.metadata["security_identity"]["symbol"], "TSLA")
        self.assertEqual(research.metadata["security_identity"]["currency"], "USD")
        self.assertEqual(explain.raw_query, "explain 2330.TW")
        self.assertEqual(trade.raw_query, "trade 2330.TW")
        self.assertEqual(watchlist.raw_query, "watchlist TSLA 2330.TW")

    def test_research_request_preserves_query_and_market_context(self) -> None:
        from backend.main import ResearchRequest
        from backend.pipeline.route_adapters import research_request_to_agent_task

        task = research_request_to_agent_task(
            ResearchRequest(
                ticker="2330",
                query="research 2330 earnings",
                exchange="TWSE",
                country="TW",
            )
        )

        self.assertEqual(task.raw_query, "research 2330 earnings")
        self.assertEqual(task.metadata["security_identity"]["symbol"], "2330.TW")
        self.assertEqual(task.metadata["security_identity"]["exchange"], "TWSE")

    def test_research_request_rejects_empty_ticker(self) -> None:
        from pydantic import ValidationError

        from backend.main import ResearchRequest

        with self.assertRaises(ValidationError):
            ResearchRequest(ticker="")

    def test_portfolio_request_adapters_build_agent_tasks(self) -> None:
        from backend.pipeline.route_adapters import (
            portfolio_agent_request_to_agent_task,
            portfolio_compare_request_to_agent_task,
            portfolio_request_to_agent_task,
            portfolio_scenario_request_to_agent_task,
        )
        from backend.schemas.agent import AgentTaskType
        from backend.schemas.portfolio import (
            NamedScenario,
            PortfolioAgentRequest,
            PortfolioRequest,
            ReallocationAction,
            ScenarioComparisonRequest,
            ScenarioRequest,
        )

        portfolio = PortfolioRequest(holdings=[{"ticker": "00878"}])
        analysis = portfolio_request_to_agent_task(portfolio)
        scenario = portfolio_scenario_request_to_agent_task(
            ScenarioRequest(
                portfolio=portfolio,
                actions=[ReallocationAction(action="sell", ticker="00878", percentage=50)],
                user_question="Trim half?",
            )
        )
        compare = portfolio_compare_request_to_agent_task(
            ScenarioComparisonRequest(
                portfolio=portfolio,
                scenarios=[NamedScenario(name="Hold", actions=[])],
            )
        )
        agent = portfolio_agent_request_to_agent_task(
            PortfolioAgentRequest(
                portfolio=portfolio,
                user_question="Should I rebalance?",
                target_ticker_or_fund="00922",
            )
        )

        self.assertEqual(analysis.task_type, AgentTaskType.PORTFOLIO_ANALYSIS)
        self.assertEqual(scenario.task_type, AgentTaskType.PORTFOLIO_SCENARIO)
        self.assertEqual(compare.task_type, AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE)
        self.assertEqual(agent.task_type, AgentTaskType.PORTFOLIO_AGENT)


if __name__ == "__main__":
    unittest.main()
