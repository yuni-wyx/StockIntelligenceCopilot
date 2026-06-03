from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioScenarioTest(unittest.TestCase):
    def test_run_portfolio_scenario_reduces_dividend_when_selling_income_holding(self) -> None:
        from backend.pipeline.portfolio_orchestrator import run_portfolio_scenario
        from backend.schemas.portfolio import (
            HoldingInput,
            PortfolioRequest,
            ReallocationAction,
            ScenarioRequest,
        )

        request = ScenarioRequest(
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(
                        ticker="00878",
                        name="Income ETF",
                        avg_cost=21.76,
                        current_price=32.06,
                        shares=2239,
                        asset_type="ETF",
                        category="High Dividend",
                    )
                ]
            ),
            actions=[
                ReallocationAction(action="sell", ticker="00878", percentage=50),
                ReallocationAction(action="buy", ticker="2204.TW", amount=35890),
            ],
            user_question="Should I redeploy half of my income ETF?",
        )

        def fake_enrich(holding):
            canonical = holding.ticker if holding.ticker.endswith(".TW") else f"{holding.ticker}.TW"
            price = 32.06 if "00878" in canonical else 53.1
            name = holding.name or ("Income ETF" if "00878" in canonical else "中華")
            category = holding.category or ("High Dividend" if "00878" in canonical else "Auto")
            theme = "Defensive / Income" if "00878" in canonical else "Industrials / Auto"
            updated = holding.model_copy(
                update={
                    "ticker": canonical,
                    "name": name,
                    "current_price": price,
                    "asset_type": (
                        holding.asset_type
                        or ("ETF" if "00878" in canonical else "Stock")
                    ),
                    "category": category,
                }
            )
            return updated, {
                "name": name,
                "current_price": price,
                "sector": category,
                "theme": theme,
                "dividend_yield": 0.06 if "00878" in canonical else 0.0,
                "annual_dividend_per_share": 1.8 if "00878" in canonical else None,
                "category": category,
                "asset_type": updated.asset_type,
                "news": [],
            }

        with patch(
            "backend.pipeline.portfolio_orchestrator._enrich_holding",
            side_effect=fake_enrich,
        ):
            response = run_portfolio_scenario(request)

        self.assertIsNotNone(response.dividend_change)
        assert response.dividend_change is not None
        self.assertLess(response.dividend_change, 0)
        self.assertIn("reasonable", response.recommendation.lower())


if __name__ == "__main__":
    unittest.main()
