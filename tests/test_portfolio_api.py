from __future__ import annotations

import sys
import tempfile
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
        from backend.schemas.portfolio_intelligence import (
            ConcentrationSnapshot,
            PortfolioIntelligenceSnapshot,
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
            portfolio_intelligence=PortfolioIntelligenceSnapshot(
                concentration=ConcentrationSnapshot(top_holding_weight_pct=55.0)
            ),
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
        self.assertIn("portfolio_intelligence", payload)
        self.assertEqual(
            payload["portfolio_intelligence"]["concentration"]["top_holding_weight_pct"],
            55.0,
        )

    def test_api_portfolio_analyze_keeps_working_when_intelligence_is_absent(self) -> None:
        from backend.main import PortfolioRequest, api_portfolio_analyze
        from backend.schemas.agent import (
            AgentEvidenceBundle,
            AgentPlan,
            AgentResult,
            AgentTask,
            AgentTaskType,
        )
        from backend.schemas.portfolio import HoldingMetrics, PortfolioAnalysisResponse

        mocked = PortfolioAnalysisResponse(
            total_cost_basis=50.0,
            total_current_value=50.0,
            total_unrealized_gain_loss=0.0,
            total_return_pct=0.0,
            estimated_annual_dividend=None,
            estimated_monthly_dividend=None,
            holdings=[HoldingMetrics(ticker="CASH", name="Cash")],
            category_exposure={},
            risk_flags=[],
            summary="base response",
            suggestions=[],
            portfolio_intelligence=None,
        )

        mocked_result = AgentResult(
            task=AgentTask(
                task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
                portfolio=PortfolioRequest(holdings=[{"ticker": "CASH"}]),
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

        req = PortfolioRequest(holdings=[{"ticker": "CASH"}])
        with patch("backend.main.execute_agent_task", return_value=mocked_result):
            payload = api_portfolio_analyze(req)

        self.assertEqual(payload["summary"], "base response")
        self.assertIn("portfolio_intelligence", payload)
        self.assertIsNone(payload["portfolio_intelligence"])

    def test_investor_profile_routes_persist_memory(self) -> None:
        import backend.main as main
        from backend.schemas.portfolio import InvestorProfileUpdate
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            with patch.object(main, "portfolio_store", store):
                saved = main.api_investor_profile_update(
                    InvestorProfileUpdate(
                        risk_tolerance="moderate",
                        investment_style="growth",
                        preferred_sectors=["Technology"],
                        time_horizon="5 years",
                    )
                )
                loaded = main.api_investor_profile()
                memory = main.api_investor_memory()

        self.assertEqual(saved["risk_tolerance"], "moderate")
        self.assertEqual(loaded["investment_style"], "growth")
        self.assertEqual(memory["profile"]["preferred_sectors"], ["Technology"])


if __name__ == "__main__":
    unittest.main()
