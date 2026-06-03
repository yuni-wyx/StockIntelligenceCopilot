from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AgentSchemaTest(unittest.TestCase):
    def test_agent_models_support_security_and_portfolio_tasks(self) -> None:
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentStep,
            AgentStreamEvent,
            AgentTask,
            AgentTaskType,
            AgentToolCall,
        )
        from backend.schemas.portfolio import NamedScenario, PortfolioRequest

        security_task = AgentTask(
            task_type=AgentTaskType.RESEARCH,
            raw_query="research TSLA",
            tickers=["TSLA"],
        )
        portfolio_task = AgentTask(
            task_type=AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE,
            portfolio=PortfolioRequest(holdings=[{"ticker": "00878"}]),
            scenarios=[NamedScenario(name="Hold", actions=[])],
        )
        plan = AgentPlan(
            task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
            summary="Unified plan",
            steps=[
                AgentStep(
                    name="metrics",
                    summary="Calculate deterministic metrics.",
                    tool_calls=[
                        AgentToolCall(
                            name="calculate_portfolio_metrics",
                            rationale="Need health scores and exposures.",
                        )
                    ],
                )
            ],
            expected_outputs=["portfolio_analysis"],
        )
        bundle = AgentEvidenceBundle(
            context={"portfolio_name": "current"},
            derived_metrics={"portfolio_analysis": {"overall_score": 80}},
            external_evidence={"market_data": {"TSLA": {"current_price": 100.0}}},
        )

        self.assertEqual(security_task.task_type, AgentTaskType.RESEARCH)
        self.assertEqual(portfolio_task.task_type, AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE)
        self.assertEqual(plan.expected_outputs, ["portfolio_analysis"])
        self.assertIn("portfolio_analysis", bundle.derived_metrics)
        self.assertEqual(
            AgentStreamEvent(type="status", message="Starting").type,
            "status",
        )


if __name__ == "__main__":
    unittest.main()
