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

    def test_fallback_agent_response_uses_investor_profile_memory(self) -> None:
        from backend.pipeline.portfolio_agent import _fallback_agent_response
        from backend.schemas.portfolio import HoldingMetrics, PortfolioAnalysisResponse

        analysis = PortfolioAnalysisResponse(
            total_cost_basis=100.0,
            total_current_value=120.0,
            total_unrealized_gain_loss=20.0,
            total_return_pct=20.0,
            estimated_annual_dividend=6.0,
            estimated_monthly_dividend=0.5,
            holdings=[HoldingMetrics(ticker="NVDA", portfolio_weight_pct=55.0)],
            asset_type_exposure={"Stock": 100.0},
            category_exposure={"Technology": 100.0},
            sector_exposure={"Technology": 100.0},
            theme_exposure={"Technology / AI": 100.0},
            market_exposure={"US": 100.0},
            risk_flags=["Single-position concentration is high."],
            summary="Technology-heavy portfolio.",
            suggestions=["Review NVDA sizing."],
        )
        evidence = {
            "targets": {"top_holdings": ["NVDA"]},
            "investor_memory": {
                "profile": {
                    "risk_tolerance": "low",
                    "investment_style": "income",
                    "preferred_sectors": ["Healthcare"],
                    "time_horizon": "3-5 years",
                },
                "prior_research_history": [
                    {"event_type": "research", "tickers": ["NVDA"], "raw_query": "research NVDA"}
                ],
            },
        }

        response = _fallback_agent_response(analysis, evidence, "What should I do?")

        self.assertEqual(response.key_numbers["risk_tolerance"], "low")
        self.assertTrue(
            any("lower risk tolerance" in item for item in response.suggested_next_actions)
        )
        self.assertTrue(any("Preferred sectors" in item for item in response.evidence_used))
