from __future__ import annotations

import unittest
from unittest.mock import patch


class SourceTTLCacheTest(unittest.TestCase):
    def test_cache_returns_copy_and_expires(self) -> None:
        from backend.services.source_cache import SourceTTLCache

        cache = SourceTTLCache()
        now = 100.0
        with patch("backend.services.source_cache.time.monotonic", return_value=now):
            cache.set("market_data:key", {"price": 10}, ttl_seconds=60)
            cached = cache.get("market_data:key")
        self.assertEqual(cached, {"price": 10})
        cached["price"] = 999

        with patch("backend.services.source_cache.time.monotonic", return_value=now + 30):
            self.assertEqual(cache.get("market_data:key"), {"price": 10})
        with patch("backend.services.source_cache.time.monotonic", return_value=now + 61):
            self.assertIsNone(cache.get("market_data:key"))

    def test_portfolio_market_source_call_is_reused_within_ttl(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioContextBuilder,
            clear_portfolio_evidence_cache,
        )
        from backend.tools.market_data_tool import MarketDataResponse

        response = MarketDataResponse(
            ticker="2330.TW",
            market="TW",
            as_of="2026-09-01T00:00:00+00:00",
            current_price=100,
            price_change_1d=0,
            price_change_pct_1d=0,
            price_change_1w=0,
            price_change_pct_1w=0,
            price_change_1m=0,
            price_change_pct_1m=0,
            volume_today=1,
            avg_volume_30d=1,
            volume_ratio=1,
            market_cap_billions=None,
            beta=None,
            week_52_high=None,
            week_52_low=None,
            ohlc_history=[],
            technicals=None,
        )
        request = PortfolioChatRequest(
            portfolio=PortfolioRequest(
                holdings=[HoldingInput(ticker="2330.TW", shares=10, avg_cost=90)]
            ),
            question="投資組合是不是太集中？",
        )
        clear_portfolio_evidence_cache()
        with patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            return_value=response,
        ) as fetch:
            builder = PortfolioContextBuilder()
            builder.build_evidence(request, request.portfolio)
            # Clear only the higher-level response cache. The source cache
            # should still prevent a second provider call.
            from backend.services import portfolio_context_builder as module

            module._evidence_cache.clear()
            builder.build_evidence(request, request.portfolio)
        self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
