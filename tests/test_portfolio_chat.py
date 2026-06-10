from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioChatApiTest(unittest.TestCase):
    def _portfolio_payload(self) -> dict:
        return {
            "holdings": [
                {
                    "ticker": "00878.TW",
                    "name": "國泰永續高股息",
                    "avg_cost": 21.76,
                    "current_price": 32.06,
                    "shares": 2239,
                    "asset_type": "ETF",
                    "category": "High Dividend",
                },
                {
                    "ticker": "2204.TW",
                    "name": "中華",
                    "avg_cost": 84.56,
                    "current_price": 53.1,
                    "shares": 500,
                    "asset_type": "Stock",
                    "category": "Auto",
                },
            ],
            "base_currency": "TWD",
        }

    def test_direct_portfolio_chat_success(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "我的風險是不是太集中？",
                "portfolio": self._portfolio_payload(),
                "language": "zh",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("portfolio_context", payload)
        self.assertIn("safety_disclaimer", payload)
        self.assertIn("evidence_used", payload)
        self.assertIn("suggested_followups", payload)
        self.assertEqual(payload["evidence_used"][0], "direct_portfolio")

    def test_saved_workspace_chat_success(self) -> None:
        import backend.main as main
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="00878.TW",
                            current_price=32.06,
                            shares=100,
                            avg_cost=21.76,
                        )
                    ]
                ),
                name="current",
            )
            with patch.object(main, "portfolio_store", store):
                response = TestClient(main.app).post(
                    "/api/portfolio/chat",
                    json={
                        "question": "What should I review first?",
                        "workspace_id": "current",
                        "language": "en",
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["evidence_used"][0], "saved_workspace")
        self.assertGreater(payload["portfolio_context"]["total_current_value"], 0)

    def test_missing_portfolio_or_workspace_returns_400(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={"question": "Help me review this"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "A portfolio or workspace_id is required to build portfolio context.",
        )

    def test_no_buy_or_sell_wording(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "How should I review this portfolio?",
                "portfolio": self._portfolio_payload(),
                "language": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        combined = " ".join(
            [
                payload["answer"],
                payload["safety_disclaimer"],
                *payload["suggested_followups"],
            ]
        ).lower()
        self.assertNotIn(" buy ", f" {combined} ")
        self.assertNotIn(" sell ", f" {combined} ")
        self.assertNotIn("target price", combined)
        self.assertNotIn("guaranteed", combined)

    def test_response_includes_portfolio_context_and_safety_fields(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "配息收入穩定嗎？",
                "portfolio": self._portfolio_payload(),
                "language": "zh",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("holdings", payload["portfolio_context"])
        self.assertIn("top_holdings", payload["portfolio_context"])
        self.assertTrue(payload["safety_disclaimer"])
        self.assertTrue(payload["suggested_followups"])

    def test_internal_failure_returns_500_without_traceback(self) -> None:
        from backend.main import app

        with patch(
            "backend.main.PortfolioChatOrchestrator.orchestrate",
            side_effect=RuntimeError("secret stack detail"),
        ):
            response = TestClient(app).post(
                "/api/portfolio/chat",
                json={
                    "question": "How should I review this portfolio?",
                    "portfolio": self._portfolio_payload(),
                    "language": "en",
                },
            )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["error"], "Portfolio-aware chat failed.")
        self.assertNotIn("secret stack detail", str(payload))


if __name__ == "__main__":
    unittest.main()
