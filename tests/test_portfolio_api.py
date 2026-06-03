from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioApiTest(unittest.TestCase):
    def test_api_portfolio_analyze_serializes_response(self) -> None:
        from backend.main import PortfolioRequest, api_portfolio_analyze
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.portfolio import (
            HoldingMetrics,
            PortfolioAnalysisResponse,
        )

        mocked = PortfolioAnalysisResponse(
            total_cost_basis=100.0,
            total_current_value=120.0,
            total_unrealized_gain_loss=20.0,
            total_return_pct=20.0,
            estimated_annual_dividend=6.0,
            estimated_monthly_dividend=0.5,
            holdings=[HoldingMetrics(ticker="00878.TW", name="ETF")],
            category_exposure={"High Dividend": 100.0},
            sector_exposure={"Income": 100.0},
            theme_exposure={"Defensive / Income": 100.0},
            risk_flags=[],
            summary="ok",
            suggestions=["keep diversified"],
        )

        mocked_result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
                portfolio=PortfolioRequest(holdings=[{"ticker": "00878"}]),
            ),
            plan=AgentPlan(
                task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
                summary="Portfolio analysis",
                expected_outputs=["portfolio_analysis"],
            ),
            evidence=AgentEvidenceBundle(context={"portfolio_name": "current"}),
            output=mocked,
            output_type="PortfolioAnalysisResponse",
        )

        req = PortfolioRequest(holdings=[{"ticker": "00878"}])
        with patch("backend.main.execute_agent_task", return_value=mocked_result):
            payload = api_portfolio_analyze(req)

        self.assertEqual(payload["total_current_value"], 120.0)
        self.assertEqual(payload["holdings"][0]["ticker"], "00878.TW")


if __name__ == "__main__":
    unittest.main()
