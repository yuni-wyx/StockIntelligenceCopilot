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

            loaded = store.load_portfolio("current")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.portfolio.holdings[0].ticker, "00878")

            updated_request = PortfolioRequest(
                holdings=[HoldingInput(ticker="2330", shares=50)],
                goal="Growth",
            )
            updated = store.update_portfolio(updated_request, name="current")
            self.assertEqual(updated.portfolio.goal, "Growth")

            listed = store.list_saved_portfolios()
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].holding_count, 1)

            deleted = store.delete_portfolio("current")
            self.assertTrue(deleted)
            self.assertIsNone(store.load_portfolio("current"))


if __name__ == "__main__":
    unittest.main()
