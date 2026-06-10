from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioIntelligenceTest(unittest.TestCase):
    def _holding(self, **overrides):
        from backend.schemas.portfolio import HoldingMetrics

        payload = {
            "ticker": "TEST",
            "name": "Test Holding",
            "current_value": 100.0,
            "unrealized_gain_loss": 0.0,
            "return_pct": 0.0,
            "portfolio_weight_pct": 10.0,
            "estimated_annual_dividend": None,
            "estimated_monthly_dividend": None,
            "theme": "General Equity",
            "sector": "General",
            "market": "US",
        }
        payload.update(overrides)
        return HoldingMetrics(**payload)

    def test_concentration_formulas_and_flags(self) -> None:
        from backend.services.portfolio_intelligence import (
            calculate_concentration_snapshot,
        )

        holdings = [
            self._holding(
                ticker="AAA",
                current_value=400,
                portfolio_weight_pct=40,
                theme="Technology / AI",
                market="US",
            ),
            self._holding(
                ticker="BBB",
                current_value=200,
                portfolio_weight_pct=20,
                theme="Technology / AI",
                market="US",
            ),
            self._holding(
                ticker="CCC",
                current_value=150,
                portfolio_weight_pct=15,
                theme="General Equity",
                market="TW",
            ),
            self._holding(
                ticker="DDD",
                current_value=150,
                portfolio_weight_pct=15,
                theme="General Equity",
                market="TW",
            ),
            self._holding(
                ticker="EEE",
                current_value=100,
                portfolio_weight_pct=10,
                theme="Defensive / Income",
                market="TW",
            ),
        ]

        snapshot = calculate_concentration_snapshot(
            holdings,
            theme_exposure={"Technology / AI": 60.0, "Defensive / Income": 10.0},
            sector_exposure={"Technology": 60.0, "Income": 10.0},
            market_exposure={"US": 60.0, "TW": 40.0},
        )

        self.assertAlmostEqual(snapshot.top_holding_weight_pct or 0, 40.0, places=2)
        self.assertAlmostEqual(snapshot.top_3_weight_pct or 0, 75.0, places=2)
        self.assertAlmostEqual(snapshot.top_5_weight_pct or 0, 100.0, places=2)
        self.assertEqual(snapshot.top_tickers[0].ticker, "AAA")
        joined_flags = " ".join(snapshot.flags).lower()
        self.assertIn("35%", joined_flags)
        self.assertIn("top 3", joined_flags)
        self.assertIn("top 5", joined_flags)
        self.assertIn("theme concentration", joined_flags)

    def test_risk_attribution_ranks_downside_losers_winners_and_stress(self) -> None:
        from backend.services.portfolio_intelligence import (
            calculate_risk_attribution_snapshot,
        )

        holdings = [
            self._holding(
                ticker="LOSER1",
                current_value=300,
                unrealized_gain_loss=-100,
                return_pct=-40,
                portfolio_weight_pct=30,
            ),
            self._holding(
                ticker="LOSER2",
                current_value=200,
                unrealized_gain_loss=-50,
                return_pct=-20,
                portfolio_weight_pct=20,
            ),
            self._holding(
                ticker="WINNER",
                current_value=500,
                unrealized_gain_loss=150,
                return_pct=30,
                portfolio_weight_pct=50,
            ),
        ]

        snapshot = calculate_risk_attribution_snapshot(
            holdings,
            stress_test_impacts={"LOSER2": 30.0, "LOSER1": 70.0},
        )

        self.assertEqual(snapshot.top_downside_weighted_holdings[0].ticker, "LOSER1")
        self.assertEqual(snapshot.top_unrealized_losers[0].ticker, "LOSER1")
        self.assertEqual(snapshot.top_unrealized_winners[0].ticker, "WINNER")
        self.assertEqual(snapshot.top_stress_test_contributors[0].ticker, "LOSER1")
        self.assertGreater(
            snapshot.top_unrealized_losers[0].contribution_pct or 0,
            snapshot.top_unrealized_losers[1].contribution_pct or 0,
        )

    def test_income_quality_ranks_dividend_contributors_and_adds_caveats(self) -> None:
        from backend.services.portfolio_intelligence import calculate_income_quality_snapshot

        holdings = [
            self._holding(
                ticker="HIGHYIELD",
                current_value=500,
                portfolio_weight_pct=50,
                estimated_annual_dividend=60,
                estimated_monthly_dividend=5,
            ),
            self._holding(
                ticker="LOWYIELD",
                current_value=300,
                portfolio_weight_pct=30,
                estimated_annual_dividend=20,
                estimated_monthly_dividend=1.67,
            ),
            self._holding(
                ticker="MISSING",
                current_value=200,
                portfolio_weight_pct=20,
                estimated_annual_dividend=None,
                estimated_monthly_dividend=None,
            ),
        ]

        snapshot = calculate_income_quality_snapshot(holdings)

        self.assertAlmostEqual(snapshot.estimated_annual_dividend or 0, 80.0, places=2)
        self.assertAlmostEqual(snapshot.estimated_monthly_dividend or 0, 80.0 / 12, places=2)
        self.assertEqual(snapshot.top_dividend_contributors[0].ticker, "HIGHYIELD")
        self.assertAlmostEqual(snapshot.dividend_concentration_pct or 0, 75.0, places=2)
        self.assertIn("MISSING", snapshot.holdings_missing_dividend_data)
        joined_caveats = " ".join(snapshot.caveats).lower()
        self.assertIn("missing dividend data", joined_caveats)
        self.assertIn("guaranteed income", joined_caveats)

    def test_suggested_review_items_trigger_from_thresholds(self) -> None:
        from backend.services.portfolio_intelligence import (
            build_portfolio_intelligence_snapshot,
        )

        holdings = [
            self._holding(
                ticker="CORE",
                current_value=500,
                portfolio_weight_pct=50,
                unrealized_gain_loss=-120,
                return_pct=-24,
                estimated_annual_dividend=50,
                estimated_monthly_dividend=4.17,
                theme="Technology / AI",
                market="US",
            ),
            self._holding(
                ticker="SECOND",
                current_value=150,
                portfolio_weight_pct=15,
                unrealized_gain_loss=-20,
                return_pct=-10,
                estimated_annual_dividend=10,
                estimated_monthly_dividend=0.83,
                theme="Technology / AI",
                market="US",
            ),
            self._holding(
                ticker="THIRD",
                current_value=100,
                portfolio_weight_pct=10,
                unrealized_gain_loss=30,
                return_pct=12,
                estimated_annual_dividend=None,
                estimated_monthly_dividend=None,
                theme="Technology / AI",
                market="US",
            ),
            self._holding(
                ticker="FOURTH",
                current_value=250,
                portfolio_weight_pct=25,
                unrealized_gain_loss=10,
                return_pct=4,
                estimated_annual_dividend=5,
                estimated_monthly_dividend=0.42,
                theme="Defensive / Income",
                market="US",
            ),
        ]

        snapshot = build_portfolio_intelligence_snapshot(
            holdings,
            theme_exposure={"Technology / AI": 75.0, "Defensive / Income": 25.0},
            sector_exposure={"Technology": 75.0, "Income": 25.0},
            market_exposure={"US": 100.0},
            stress_test_impacts={"CORE": 80.0, "SECOND": 20.0},
        )

        titles = " | ".join(item.title for item in snapshot.suggested_review_items)
        evidence_keys = {
            key
            for item in snapshot.suggested_review_items
            for key in item.evidence_keys
        }

        self.assertIn("CORE", titles)
        self.assertIn("theme concentration", titles.lower())
        self.assertIn("market concentration", titles.lower())
        self.assertIn("income concentration", titles.lower())
        self.assertIn("stress sensitivity", titles.lower())
        self.assertIn("review", titles.lower())
        self.assertIn("concentration.top_holding_weight_pct", evidence_keys)
        self.assertIn("income_quality.dividend_concentration_pct", evidence_keys)

    def test_zero_empty_portfolio_handling(self) -> None:
        from backend.services.portfolio_intelligence import (
            build_portfolio_intelligence_snapshot,
        )

        snapshot = build_portfolio_intelligence_snapshot([])

        self.assertEqual(snapshot.concentration.top_tickers, [])
        self.assertEqual(snapshot.risk_attribution.top_unrealized_losers, [])
        self.assertEqual(snapshot.income_quality.top_dividend_contributors, [])
        self.assertGreaterEqual(len(snapshot.income_quality.caveats), 1)
        self.assertEqual(snapshot.suggested_review_items, [])


if __name__ == "__main__":
    unittest.main()
