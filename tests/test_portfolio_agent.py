from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioAgentTest(unittest.TestCase):
    def test_api_portfolio_agent_works_with_mocked_agent(self) -> None:
        from backend.main import PortfolioAgentRequest, api_portfolio_agent
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.portfolio import PortfolioAgentResponse, PortfolioRequest

        mocked = PortfolioAgentResponse(
            conclusion="Conclusion",
            current_portfolio_diagnosis="Diagnosis",
            key_numbers={"overall_score": 72},
            evidence_used=["Holding weights", "Theme exposure"],
            bull_case="Bull",
            bear_case="Bear",
            base_case="Base",
            suggested_next_actions=["Trim concentration"],
            risks=["Technology concentration"],
            missing_data=[],
        )

        request = PortfolioAgentRequest(
            portfolio=PortfolioRequest(holdings=[{"ticker": "00878"}]),
            user_question="Should I rebalance?",
        )

        mocked_result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.PORTFOLIO_AGENT,
                portfolio=request.portfolio,
                user_question=request.user_question,
            ),
            plan=AgentPlan(
                task_type=AgentTaskType.PORTFOLIO_AGENT,
                summary="Portfolio agent",
                expected_outputs=["portfolio_agent_recommendation"],
            ),
            evidence=AgentEvidenceBundle(context={"portfolio_name": "current"}),
            output=mocked,
            output_type="PortfolioAgentResponse",
        )

        with patch("backend.main.execute_agent_task", return_value=mocked_result):
            payload = api_portfolio_agent(request)

        self.assertEqual(payload["conclusion"], "Conclusion")
        self.assertEqual(payload["key_numbers"]["overall_score"], 72)
