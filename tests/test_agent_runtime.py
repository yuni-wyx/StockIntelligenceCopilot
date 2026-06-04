from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AgentRuntimeTest(unittest.TestCase):
    def test_execute_portfolio_analysis_returns_runtime_output(self) -> None:
        from backend.pipeline.agent_runtime import execute_portfolio_analysis
        from backend.schemas.portfolio import (
            HoldingMetrics,
            PortfolioAnalysisResponse,
            PortfolioRequest,
        )

        mocked = PortfolioAnalysisResponse(
            total_cost_basis=100.0,
            total_current_value=120.0,
            total_unrealized_gain_loss=20.0,
            total_return_pct=20.0,
            estimated_annual_dividend=6.0,
            estimated_monthly_dividend=0.5,
            overall_score=78,
            diversification_score=70,
            concentration_score=72,
            income_score=80,
            defensive_score=75,
            growth_score=65,
            holdings=[HoldingMetrics(ticker="00878.TW", name="ETF")],
            asset_type_exposure={"ETF": 100.0},
            category_exposure={"High Dividend": 100.0},
            sector_exposure={"Income": 100.0},
            theme_exposure={"Defensive / Income": 100.0},
            market_exposure={"TW": 100.0},
            risk_flags=[],
            summary="Stable income-heavy portfolio.",
            suggestions=["Keep position sizing disciplined."],
        )

        request = PortfolioRequest(holdings=[{"ticker": "00878"}])
        with patch(
            "backend.pipeline.agent_runtime.analyze_portfolio_with_evidence",
            return_value=(mocked, {"00878.TW": {"news": []}}),
        ):
            result = execute_portfolio_analysis(request)

        self.assertEqual(result.overall_score, 78)
        self.assertEqual(result.holdings[0].ticker, "00878.TW")

    def test_execute_agent_task_supports_security_contract(self) -> None:
        from backend.pipeline.agent_runtime import execute_agent_task
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentStep,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.output_schema import TradingDecisionOutput

        task = AgentTask(task_type=AgentTaskType.TRADE, tickers=["TSLA"])
        plan = AgentPlan(
            task_type=AgentTaskType.TRADE,
            summary="Trade TSLA",
            steps=[AgentStep(name="planner", summary="Build trade plan.")],
            expected_outputs=["trade_setup"],
        )
        bundle = AgentEvidenceBundle(context={"raw_query": "trade TSLA"})
        mocked_output = TradingDecisionOutput(
            ticker="TSLA",
            bias="Neutral",
            buy_zone="Current reference: $100.00",
            stop_loss="$95.00",
            take_profit="$108.00",
            confidence=45,
            reasoning=["Heuristic setup."],
        )

        with patch(
            "backend.pipeline.agent_runtime.classify_and_plan",
            return_value=("intent", object()),
        ), patch(
            "backend.pipeline.agent_runtime.retrieve_evidence",
            return_value=([], object()),
        ), patch(
            "backend.pipeline.agent_runtime.build_agent_plan_from_execution_plan",
            return_value=plan,
        ), patch(
            "backend.pipeline.agent_runtime.build_agent_evidence_from_aggregated_evidence",
            return_value=bundle,
        ), patch(
            "backend.pipeline.agent_runtime.synthesise_agent_output",
            return_value=mocked_output,
        ):
            result = execute_agent_task(task)

        self.assertEqual(result.output.ticker, "TSLA")
        self.assertEqual(result.output_type, "TradingDecisionOutput")

    def test_execute_agent_task_records_research_history(self) -> None:
        from backend.pipeline.agent_runtime import execute_agent_task
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.output_schema import TradingDecisionOutput
        from backend.services.portfolio_store import PortfolioStore

        task = AgentTask(task_type=AgentTaskType.RESEARCH, tickers=["TSLA"])
        plan = AgentPlan(
            task_type=AgentTaskType.RESEARCH,
            summary="Research TSLA",
            expected_outputs=["fundamental_summary"],
        )
        mocked_output = TradingDecisionOutput(
            ticker="TSLA",
            bias="Neutral",
            buy_zone="Current reference: $100.00",
            stop_loss="$95.00",
            take_profit="$108.00",
            confidence=45,
            reasoning=["Grounded setup."],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            with patch(
                "backend.pipeline.agent_runtime.classify_and_plan",
                return_value=("intent", object()),
            ), patch(
                "backend.pipeline.agent_runtime.retrieve_evidence",
                return_value=([], object()),
            ), patch(
                "backend.pipeline.agent_runtime.build_agent_plan_from_execution_plan",
                return_value=plan,
            ), patch(
                "backend.pipeline.agent_runtime.build_agent_evidence_from_aggregated_evidence",
                return_value=AgentEvidenceBundle(context={"raw_query": "research TSLA"}),
            ), patch(
                "backend.pipeline.agent_runtime.synthesise_agent_output",
                return_value=mocked_output,
            ):
                execute_agent_task(task, store=store)

            snapshot = store.get_investor_memory_snapshot()

        self.assertEqual(snapshot.prior_research_history[0].event_type, "research")
        self.assertEqual(snapshot.prior_research_history[0].tickers, ["TSLA"])

    def test_stream_agent_task_emits_start_final_and_done_events(self) -> None:
        from backend.pipeline.agent_runtime import stream_agent_task
        from backend.schemas.agent import AgentTask, AgentTaskType
        from backend.schemas.evidence_schema import AggregatedEvidence, ToolResult
        from backend.schemas.intent_schema import IntentOutput
        from backend.schemas.output_schema import TradingDecisionOutput
        from backend.schemas.planner_schema import ExecutionPlan, ToolCallSpec, ToolName

        task = AgentTask(task_type=AgentTaskType.TRADE, tickers=["TSLA"])
        intent = IntentOutput(
            mode="trade",
            tickers=["TSLA"],
            confidence=0.99,
            reasoning="trade task",
        )
        plan = ExecutionPlan(
            mode="trade",
            tickers=["TSLA"],
            tool_calls=[
                ToolCallSpec(
                    tool=ToolName.MARKET_DATA,
                    ticker="TSLA",
                    priority=1,
                    rationale="Need price context.",
                )
            ],
            analysis_focus="Trade TSLA",
            expected_outputs=["trade_setup"],
        )
        tool_results = [
            ToolResult(
                tool="market_data",
                ticker="TSLA",
                success=True,
                data={"current_price": 100.0},
            )
        ]
        evidence = AggregatedEvidence(
            mode="trade",
            tickers_evidence={},
            total_tool_calls=1,
            successful_calls=1,
        )
        final_output = TradingDecisionOutput(
            ticker="TSLA",
            bias="Neutral",
            buy_zone="Current reference: $100.00",
            stop_loss="$95.00",
            take_profit="$108.00",
            confidence=45,
            reasoning=["Heuristic setup."],
        )

        with patch("backend.pipeline.planning.trace_intent", return_value=intent), patch(
            "backend.pipeline.planning.plan_from_intent",
            return_value=plan,
        ), patch(
            "backend.pipeline.retrieval.trace_tool_routing",
            return_value=tool_results,
        ), patch(
            "backend.pipeline.retrieval.trace_aggregate",
            return_value=evidence,
        ), patch(
            "backend.pipeline.agent_runtime.synthesise_agent_output",
            return_value=final_output,
        ):
            events = list(stream_agent_task(task))

        event_types = [event.type for event in events]
        self.assertEqual(event_types[0], "status")
        self.assertIn("final_output", event_types)
        self.assertEqual(events[-1].type, "final_output")


if __name__ == "__main__":
    unittest.main()
