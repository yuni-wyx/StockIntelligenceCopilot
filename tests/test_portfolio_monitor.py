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


class PortfolioMonitorTest(unittest.TestCase):
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
                    "ticker": "2330.TW",
                    "name": "台積電",
                    "avg_cost": 850.0,
                    "current_price": 780.0,
                    "shares": 50,
                    "asset_type": "Stock",
                    "category": "Semiconductor",
                },
            ],
            "base_currency": "TWD",
        }

    def _signal_response(self, ticker: str, *, band: str = "Weak", confidence: str = "Low"):
        from backend.schemas.signal import SignalFeatureSnapshot, SignalResponse

        return SignalResponse(
            ticker=ticker,
            benchmark="SPY",
            horizon_days=30,
            signal_score=35.0 if band == "Weak" else 68.0,
            signal_band=band,
            confidence=confidence,
            positive_signals=["Relative trend support"] if band != "Weak" else [],
            negative_signals=["Weak 20d relative return"] if band == "Weak" else [],
            data_caveats=["Short history"] if confidence == "Low" else [],
            disclaimer="Heuristic signal only.",
            feature_snapshot=SignalFeatureSnapshot(
                return_5d=1.0,
                return_20d=2.0,
                benchmark_return_20d=1.0,
                relative_return_20d=1.0,
                price_vs_sma20_pct=1.0,
                sma20_vs_sma50_pct=1.0,
                realized_volatility_20d=20.0,
                drawdown_from_60d_high_pct=-5.0,
                volume_ratio_5d_vs_20d=1.1,
            ),
        )

    def _news_response(self, ticker: str, *, sentiment: str = "negative"):
        from backend.tools.news_tool import NewsArticle, NewsResponse

        return NewsResponse(
            ticker=ticker,
            market="TW",
            query_window_days=7,
            total_articles=1,
            articles=[
                NewsArticle(
                    article_id=f"{ticker}-1",
                    published_at="2026-06-11T00:00:00+00:00",
                    title=f"{ticker} headline",
                    source="Test",
                    url="https://example.com",
                    summary="headline summary",
                    sentiment=sentiment,
                    sentiment_score=-0.4 if sentiment == "negative" else 0.3,
                    relevance_score=0.8,
                    tickers_mentioned=[ticker],
                    topics=["general"],
                )
            ],
            overall_sentiment=sentiment,
            avg_sentiment_score=-0.4 if sentiment == "negative" else 0.3,
        )

    def _earnings_response(self, ticker: str, *, days_to_next: int = 12):
        from backend.tools.earnings_tool import (
            EarningsEstimate,
            EarningsResponse,
            EarningsResult,
        )

        return EarningsResponse(
            ticker=ticker,
            next_earnings=EarningsEstimate(
                period="Q3 FY2026",
                report_date="2026-06-23",
                report_time="AMC",
                eps_estimate_consensus=1.0,
                eps_estimate_high=1.1,
                eps_estimate_low=0.9,
                revenue_estimate_billions=10.0,
                num_analysts=20,
            ),
            days_to_next_earnings=days_to_next,
            earnings_history=[
                EarningsResult(
                    period="Q2 FY2026",
                    report_date="2026-03-20",
                    eps_actual=1.1,
                    eps_estimate=1.0,
                    eps_surprise=0.1,
                    eps_surprise_pct=10.0,
                    revenue_actual_billions=9.0,
                    revenue_estimate_billions=8.8,
                    revenue_surprise_pct=2.27,
                    guidance_raised=False,
                    post_earnings_move_pct=1.2,
                    key_metrics={},
                    management_commentary="steady",
                )
            ],
            avg_eps_surprise_pct=10.0,
            avg_post_earnings_move_pct=1.2,
            beat_rate=0.75,
        )

    def test_generate_uses_saved_current_workspace_by_default(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_monitor import PortfolioMonitorRequest
        from backend.services.portfolio_monitor import PortfolioMonitorService
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="00878.TW",
                            current_price=32.06,
                            shares=2239,
                            avg_cost=21.76,
                            category="High Dividend",
                            asset_type="ETF",
                        )
                    ]
                ),
                name="current",
            )
            service = PortfolioMonitorService(store=store)
            with patch(
                "backend.services.portfolio_monitor.fetch_signal",
                return_value=self._signal_response("00878.TW"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_news",
                return_value=self._news_response("00878.TW"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_earnings",
                return_value=self._earnings_response("00878.TW"),
            ):
                response = service.generate(PortfolioMonitorRequest())

        self.assertEqual(response.workspace_id, "current")
        self.assertTrue(response.holdings)
        self.assertIn("heuristic review prompts", response.safety_disclaimer)

    def test_direct_portfolio_takes_priority_over_workspace_id(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_monitor import PortfolioMonitorRequest
        from backend.services.portfolio_monitor import PortfolioMonitorService
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[HoldingInput(ticker="AAPL", current_price=100, shares=1)]
                ),
                name="income",
            )
            service = PortfolioMonitorService(store=store)
            with patch(
                "backend.services.portfolio_monitor.fetch_signal",
                return_value=self._signal_response("2330.TW", band="Strong", confidence="High"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_news",
                return_value=self._news_response("2330.TW", sentiment="positive"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_earnings",
                return_value=self._earnings_response("2330.TW", days_to_next=45),
            ):
                response = service.generate(
                    PortfolioMonitorRequest(
                        workspace_id="income",
                        portfolio=PortfolioRequest(
                            holdings=[
                                HoldingInput(
                                    ticker="2330.TW",
                                    current_price=780.0,
                                    shares=10,
                                    avg_cost=850.0,
                                    category="Semiconductor",
                                    asset_type="Stock",
                                )
                            ]
                        ),
                    )
                )

        self.assertEqual(response.workspace_id, "income")
        self.assertEqual(response.holdings[0].ticker, "2330.TW")

    def test_tool_failures_add_caveats_without_failing_generation(self) -> None:
        from backend.schemas.portfolio_monitor import PortfolioMonitorRequest
        from backend.services.portfolio_monitor import PortfolioMonitorService
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            service = PortfolioMonitorService(
                store=PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            )
            with patch(
                "backend.services.portfolio_monitor.fetch_signal",
                side_effect=RuntimeError("signal down"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_news",
                side_effect=RuntimeError("news down"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_earnings",
                side_effect=RuntimeError("earnings down"),
            ):
                response = service.generate(
                    PortfolioMonitorRequest(portfolio=self._portfolio_payload())
                )

        first = response.holdings[0]
        self.assertIsNone(first.signal_score)
        self.assertIsNone(first.news_sentiment)
        self.assertTrue(
            any("Signal evidence was unavailable" in item for item in first.caveats)
        )
        self.assertTrue(
            any("Recent news evidence was unavailable" in item for item in first.caveats)
        )
        self.assertTrue(
            any("Earnings timing was unavailable" in item for item in first.caveats)
        )

    def test_monitor_route_returns_non_404_and_payload(self) -> None:
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
                            shares=2239,
                            avg_cost=21.76,
                            category="High Dividend",
                            asset_type="ETF",
                        )
                    ]
                ),
                name="current",
            )
            with patch.object(main, "portfolio_store", store), patch(
                "backend.services.portfolio_monitor.fetch_signal",
                return_value=self._signal_response("00878.TW"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_news",
                return_value=self._news_response("00878.TW"),
            ), patch(
                "backend.services.portfolio_monitor.fetch_earnings",
                return_value=self._earnings_response("00878.TW"),
            ):
                response = TestClient(main.app).post("/api/portfolio/monitor", json={})

        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("holdings", payload)
        self.assertIn("top_portfolio_alerts", payload)

    def test_monitor_route_returns_400_when_no_portfolio_is_available(self) -> None:
        import backend.main as main
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            with patch.object(main, "portfolio_store", store):
                response = TestClient(main.app).post("/api/portfolio/monitor", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "No saved current portfolio was found. Save holdings in Wealth Studio or provide "
            "a portfolio payload.",
        )


if __name__ == "__main__":
    unittest.main()
