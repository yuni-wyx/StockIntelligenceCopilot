from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioCalculatorTest(unittest.TestCase):
    def test_calculate_portfolio_metrics_handles_mixed_holdings(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_calculator import calculate_portfolio_metrics

        request = PortfolioRequest(
            holdings=[
                HoldingInput(
                    ticker="00878.TW",
                    name="國泰永續高股息",
                    avg_cost=21.76,
                    current_price=32.06,
                    shares=2239,
                    asset_type="ETF",
                    category="High Dividend",
                ),
                HoldingInput(
                    ticker="2204.TW",
                    name="中華",
                    avg_cost=84.56,
                    current_price=53.1,
                    shares=500,
                    asset_type="Stock",
                    category="Auto",
                ),
            ],
            base_currency="TWD",
        )
        enrichment = {
            "00878.TW": {
                "theme": "Defensive / Income",
                "sector": "Income",
                "dividend_yield": 0.06,
                "asset_type": "ETF",
                "category": "High Dividend",
            },
            "2204.TW": {
                "theme": "Industrials / Auto",
                "sector": "Auto",
                "asset_type": "Stock",
                "category": "Auto",
            },
        }

        result = calculate_portfolio_metrics(request, enrichment=enrichment)

        self.assertAlmostEqual(result.total_current_value or 0, 98332.34, places=2)
        self.assertGreater(result.estimated_annual_dividend or 0, 0)
        self.assertAlmostEqual(
            result.estimated_monthly_dividend or 0,
            (result.estimated_annual_dividend or 0) / 12,
            places=1,
        )
        self.assertIn("High Dividend", result.category_exposure)
        self.assertIn("Defensive / Income", result.theme_exposure)
        self.assertGreater(result.overall_score, 0)
        self.assertIn("TW", result.market_exposure)
        self.assertIsNotNone(result.portfolio_intelligence)
        self.assertGreater(
            result.portfolio_intelligence.concentration.top_holding_weight_pct or 0,
            0,
        )
        self.assertIsInstance(
            result.portfolio_intelligence.suggested_review_items,
            list,
        )

    def test_avg_cost_without_shares_does_not_fake_cost_basis(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_calculator import calculate_portfolio_metrics

        request = PortfolioRequest(
            holdings=[
                HoldingInput(
                    ticker="TEST",
                    avg_cost=10,
                    current_value=500,
                    asset_type="Stock",
                    category="General",
                )
            ],
        )

        result = calculate_portfolio_metrics(request)
        holding = result.holdings[0]

        self.assertIsNone(holding.cost_basis)
        self.assertIsNone(holding.return_pct)
        self.assertIsNone(result.total_return_pct)
        self.assertIn("Missing average cost or shares", " ".join(result.missing_data))

    def test_calculate_portfolio_metrics_flags_concentration_and_losers(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_calculator import calculate_portfolio_metrics

        request = PortfolioRequest(
            holdings=[
                HoldingInput(
                    ticker="NVDA",
                    name="NVIDIA",
                    avg_cost=500,
                    current_price=900,
                    shares=100,
                    asset_type="Stock",
                    category="Technology",
                ),
                HoldingInput(
                    ticker="2204.TW",
                    name="中華",
                    avg_cost=84.56,
                    current_price=53.1,
                    shares=500,
                    asset_type="Stock",
                    category="Auto",
                ),
            ],
        )
        enrichment = {
            "NVDA": {"theme": "Technology / AI", "sector": "Technology"},
            "2204.TW": {"theme": "Industrials / Auto", "sector": "Auto"},
        }

        result = calculate_portfolio_metrics(request, enrichment=enrichment)

        combined_flags = " ".join(result.risk_flags)
        self.assertIn("concentration", combined_flags.lower())
        self.assertIn("technology", combined_flags.lower())
        self.assertIn("2204.TW", combined_flags)
        self.assertLess(result.concentration_score, 100)
        self.assertIn("single_position_concentration", result.risk_attribution)
        self.assertIn("technology_theme_exposure", result.risk_attribution)
        self.assertGreater(result.risk_attribution["single_position_concentration"], 0)
        self.assertAlmostEqual(sum(result.risk_attribution.values()), 100.0, places=1)

    def test_calculate_portfolio_metrics_survives_intelligence_failure(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_calculator import calculate_portfolio_metrics

        request = PortfolioRequest(
            holdings=[
                HoldingInput(
                    ticker="00878.TW",
                    current_price=32.06,
                    shares=100,
                    avg_cost=21.76,
                )
            ],
            base_currency="TWD",
        )

        with patch(
            "backend.services.portfolio_calculator.build_portfolio_intelligence_snapshot",
            side_effect=RuntimeError("boom"),
        ):
            result = calculate_portfolio_metrics(request)

        self.assertIsNone(result.portfolio_intelligence)
        self.assertIsNotNone(result.total_current_value)
        self.assertTrue(
            any(
                "Portfolio intelligence details were unavailable" in item
                for item in result.missing_data
            )
        )


if __name__ == "__main__":
    unittest.main()
