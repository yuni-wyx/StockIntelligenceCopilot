from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import pandas as pd


class Phase1DataHonestyTest(unittest.TestCase):
    def test_news_returns_empty_when_provider_has_no_articles(self) -> None:
        from backend.tools.news_tool import NewsRequest, fetch_news

        with patch("backend.tools.news_tool.yf.Ticker") as ticker_factory:
            ticker_factory.return_value.news = []
            result = fetch_news(NewsRequest(ticker="2330.TW"))

        self.assertEqual(result.articles, [])
        self.assertEqual(result.total_articles, 0)
        self.assertTrue(result.data_caveats)
        self.assertNotIn("Local market fallback", str(result.model_dump()))

    def test_earnings_does_not_create_zero_estimates_when_missing(self) -> None:
        from backend.tools.earnings_tool import EarningsRequest, fetch_earnings

        ticker = Mock()
        ticker.info = {}
        ticker.calendar = None
        ticker.get_earnings_dates.return_value = pd.DataFrame()
        ticker.quarterly_income_stmt = pd.DataFrame()
        ticker.quarterly_financials = pd.DataFrame()

        with patch("backend.tools.earnings_tool.yf.Ticker", return_value=ticker):
            result = fetch_earnings(EarningsRequest(ticker="AAPL"))

        self.assertIsNone(result.next_earnings)
        self.assertEqual(result.earnings_history, [])
        self.assertIsNone(result.avg_eps_surprise_pct)
        self.assertIsNone(result.avg_post_earnings_move_pct)
        self.assertIsNone(result.beat_rate)

    def test_market_metadata_is_null_when_yahoo_does_not_supply_it(self) -> None:
        from backend.tools.market_data_tool import MarketDataRequest, fetch_market_data

        dates = pd.date_range("2026-01-01", periods=60, freq="D", tz="UTC")
        history = pd.DataFrame(
            {
                "Open": range(100, 160),
                "High": range(101, 161),
                "Low": range(99, 159),
                "Close": range(100, 160),
                "Volume": [1000] * 60,
            },
            index=dates,
        )
        ticker = Mock()
        ticker.history.return_value = history
        ticker.info = {}

        with patch("backend.tools.market_data_tool.yf.Ticker", return_value=ticker):
            result = fetch_market_data(MarketDataRequest(ticker="AAPL"))

        self.assertIsNone(result.market_cap_billions)
        self.assertIsNone(result.beta)
        self.assertIsNone(result.week_52_high)
        self.assertIsNone(result.week_52_low)
        self.assertTrue(result.data_caveats)
        self.assertNotEqual(result.technicals.rsi_14, 50.0)


if __name__ == "__main__":
    unittest.main()
