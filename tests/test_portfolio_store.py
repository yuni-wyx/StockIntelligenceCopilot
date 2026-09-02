from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioStoreTest(unittest.TestCase):
    def test_save_load_update_delete_and_list(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            initial = PortfolioRequest(
                holdings=[HoldingInput(ticker="00878", shares=100)],
                goal="Income",
            )
            saved = store.save_portfolio(initial, name="current")
            self.assertEqual(saved.name, "current")
            self.assertEqual(saved.version, 1)

            loaded = store.load_portfolio("current")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.portfolio.holdings[0].ticker, "00878.TW")

            updated_request = PortfolioRequest(
                holdings=[HoldingInput(ticker="2330", shares=50)],
                goal="Growth",
            )
            updated = store.update_portfolio(updated_request, name="current")
            self.assertEqual(updated.portfolio.goal, "Growth")
            self.assertEqual(updated.version, 2)

            listed = store.list_saved_portfolios()
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].holding_count, 1)

            deleted = store.delete_portfolio("current")
            self.assertTrue(deleted)
            self.assertIsNone(store.load_portfolio("current"))

    def test_investor_profile_memory_and_history_are_persistent(self) -> None:
        from backend.schemas.portfolio import InvestorProfileUpdate
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            profile = store.update_investor_profile(
                InvestorProfileUpdate(
                    risk_tolerance="low",
                    investment_style="income",
                    preferred_sectors=["Technology", "Healthcare"],
                    time_horizon="3-5 years",
                )
            )
            store.record_investor_history(
                "research",
                ["NVDA"],
                raw_query="research NVDA",
            )
            store.record_investor_history(
                "watchlist",
                ["NVDA", "2330.TW"],
                raw_query="watchlist NVDA 2330.TW",
            )

            snapshot = store.get_investor_memory_snapshot()

            self.assertEqual(profile.risk_tolerance, "low")
            self.assertEqual(snapshot.profile.investment_style, "income")
            self.assertEqual(snapshot.prior_research_history[0].tickers, ["NVDA"])
            self.assertEqual(snapshot.watchlist_history[0].tickers, ["NVDA", "2330.TW"])

    def test_load_migrates_known_stale_chinese_workspace_aliases(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="我有中華",
                            name="我有中華",
                            shares=500,
                            avg_cost=84.56,
                        ),
                        HoldingInput(
                            ticker="兆利",
                            name="兆利",
                            shares=410,
                            avg_cost=180.49,
                        ),
                        HoldingInput(
                            ticker="00878",
                            name="00878",
                            shares=2239,
                            avg_cost=21.76,
                        ),
                    ]
                ),
                name="current",
            )

            loaded = store.load_portfolio("current")

        self.assertIsNotNone(loaded)
        assert loaded is not None
        holdings = loaded.portfolio.holdings
        self.assertEqual(
            [
                (holding.ticker, holding.name, holding.shares, holding.avg_cost)
                for holding in holdings
            ],
            [
                ("2204.TW", "中華", 500.0, 84.56),
                ("3548.TW", "兆利", 410.0, 180.49),
                ("00878.TW", "國泰永續高股息", 2239.0, 21.76),
            ],
        )
        self.assertIn("Normalized from saved workspace alias", holdings[0].notes or "")

    def test_unknown_chinese_holding_is_not_silently_mapped(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="未知公司",
                            name="未知公司",
                            shares=100,
                            avg_cost=10,
                        )
                    ]
                ),
                name="current",
            )

            loaded = store.load_portfolio("current")

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.portfolio.holdings[0].ticker, "未知公司")
        self.assertEqual(loaded.portfolio.holdings[0].name, "未知公司")


if __name__ == "__main__":
    unittest.main()
