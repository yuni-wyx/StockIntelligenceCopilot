from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AgentEvidenceAdapterTest(unittest.TestCase):
    def test_build_security_evidence_bundle_keeps_legacy_evidence(self) -> None:
        from backend.pipeline.agent_runtime import (
            build_agent_evidence_from_aggregated_evidence,
        )
        from backend.schemas.agent import AgentTask, AgentTaskType
        from backend.schemas.evidence_schema import AggregatedEvidence
        from backend.schemas.planner_schema import ExecutionPlan

        task = AgentTask(task_type=AgentTaskType.RESEARCH, tickers=["TSLA"])
        legacy_plan = ExecutionPlan(
            mode="stock_research",
            tickers=["TSLA"],
            tool_calls=[],
            analysis_focus="Research TSLA",
            expected_outputs=["fundamental_summary"],
        )
        from backend.pipeline.agent_runtime import build_agent_plan_from_execution_plan

        plan = build_agent_plan_from_execution_plan(task, legacy_plan)
        legacy_evidence = AggregatedEvidence(
            mode="stock_research",
            tickers_evidence={},
            total_tool_calls=0,
            successful_calls=0,
        )

        bundle = build_agent_evidence_from_aggregated_evidence(
            task,
            plan,
            raw_query="research TSLA",
            tool_results=[],
            aggregated_evidence=legacy_evidence,
        )

        self.assertIsNotNone(bundle.legacy_evidence)
        self.assertEqual(bundle.context["raw_query"], "research TSLA")

    def test_build_portfolio_evidence_bundle_layers_context_and_metrics(self) -> None:
        from backend.pipeline.agent_runtime import (
            build_portfolio_agent_plan,
            build_portfolio_evidence_bundle,
        )
        from backend.schemas.agent import AgentTask, AgentTaskType
        from backend.schemas.portfolio import (
            HoldingMetrics,
            PortfolioAnalysisResponse,
            PortfolioRequest,
        )

        task = AgentTask(
            task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
            portfolio=PortfolioRequest(holdings=[{"ticker": "00878"}]),
            user_question="How healthy is my portfolio?",
        )
        plan = build_portfolio_agent_plan(task)
        analysis = PortfolioAnalysisResponse(
            total_cost_basis=100.0,
            total_current_value=120.0,
            total_unrealized_gain_loss=20.0,
            total_return_pct=20.0,
            estimated_annual_dividend=6.0,
            estimated_monthly_dividend=0.5,
            overall_score=81,
            diversification_score=78,
            concentration_score=74,
            income_score=82,
            defensive_score=80,
            growth_score=60,
            holdings=[HoldingMetrics(ticker="00878.TW", name="ETF")],
            asset_type_exposure={"ETF": 100.0},
            category_exposure={"High Dividend": 100.0},
            sector_exposure={"Income": 100.0},
            theme_exposure={"Defensive / Income": 100.0},
            market_exposure={"TW": 100.0},
            risk_flags=[],
            summary="Income-oriented mix.",
            suggestions=["Review concentration quarterly."],
        )

        bundle = build_portfolio_evidence_bundle(
            task,
            plan,
            portfolio=task.portfolio,
            analysis=analysis,
            enrichment={
                "00878.TW": {
                    "market_data": {"current_price": 32.06},
                    "fundamentals": {"profile": {"name": "ETF"}},
                    "news_articles": [{"title": "Headline"}],
                }
            },
        )

        self.assertIn("portfolio", bundle.context)
        self.assertIn("portfolio_analysis", bundle.derived_metrics)
        self.assertIn("market_data", bundle.external_evidence)


if __name__ == "__main__":
    unittest.main()
