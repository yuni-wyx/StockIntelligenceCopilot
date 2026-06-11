from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioImporterTest(unittest.TestCase):
    def test_preview_portfolio_csv_parses_generic_columns(self) -> None:
        from backend.services.portfolio_importer import preview_portfolio_csv

        content = (
            "Ticker,Name,Shares,Avg Cost,Current Price,Asset Type,Category\n"
            "00878,國泰永續高股息,2239,21.76,32.06,ETF,High Dividend\n"
            "2204.TW,中華,500,84.56,53.1,Stock,Auto\n"
        ).encode("utf-8")

        preview = preview_portfolio_csv(content)

        self.assertEqual(preview.imported_count, 2)
        self.assertEqual(preview.total_rows, 2)
        self.assertEqual(preview.holdings[0].ticker, "00878")
        self.assertEqual(preview.holdings[1].shares, 500)
        self.assertEqual(preview.errors, [])

    def test_preview_portfolio_csv_returns_row_errors_and_warnings(self) -> None:
        from backend.services.portfolio_importer import preview_portfolio_csv

        content = (
            "Ticker,Shares,Current Price\n"
            ",10,100\n"
            "TSLA,0,200\n"
            "AAPL,5,\n"
        ).encode("utf-8")

        preview = preview_portfolio_csv(content)

        self.assertEqual(preview.imported_count, 1)
        self.assertEqual(len(preview.errors), 2)
        self.assertEqual(len(preview.warnings), 1)
        self.assertEqual(preview.holdings[0].ticker, "AAPL")

    def test_preview_route_accepts_csv_and_returns_non_empty_preview(self) -> None:
        from backend.main import app

        client = TestClient(app)
        response = client.post(
            "/api/portfolio/import/preview",
            files={
                "file": (
                    "holdings.csv",
                    (
                        "Ticker,Shares,Current Price\n"
                        "00878,100,32.06\n"
                    ).encode("utf-8"),
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["imported_count"], 1)
        self.assertEqual(payload["holdings"][0]["ticker"], "00878")

    def test_preview_route_rejects_non_csv_file(self) -> None:
        from backend.main import app

        client = TestClient(app)
        response = client.post(
            "/api/portfolio/import/preview",
            files={"file": ("holdings.txt", b"Ticker,Shares\nTSLA,10", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Please upload a CSV file.")


if __name__ == "__main__":
    unittest.main()
