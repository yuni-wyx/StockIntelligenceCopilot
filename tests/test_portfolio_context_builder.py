from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioContextBuilderTest(unittest.TestCase):
    def _portfolio_request(self):
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest

        return PortfolioRequest(
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
                HoldingInput(
                    ticker="3548.TW",
                    name="兆利",
                    avg_cost=180.49,
                    current_price=96.4,
                    shares=410,
                    asset_type="Stock",
                    category="Electronics",
                ),
            ],
            base_currency="TWD",
        )

    def test_builds_context_from_direct_portfolio_input(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="我的風險是不是太集中？",
            portfolio=self._portfolio_request(),
            language="zh",
        )

        context = builder.build_context(request)

        self.assertGreater(context.total_current_value or 0, 0)
        self.assertEqual(len(context.holdings), 3)
        self.assertEqual(context.top_holdings[0].ticker, "00878.TW")
        self.assertTrue(context.concentration_summary)
        self.assertTrue(context.income_summary)

    def test_loads_context_from_saved_workspace_when_workspace_id_is_provided(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(self._portfolio_request(), name="wealth-demo")
            builder = PortfolioContextBuilder(store=store)

            request = PortfolioChatRequest(
                question="What should I review first?",
                workspace_id="wealth-demo",
                language="en",
            )

            context = builder.build_context(request)

            self.assertGreater(context.total_current_value or 0, 0)
            self.assertEqual(context.holdings[0].ticker, "00878.TW")

    def test_direct_portfolio_takes_priority_over_workspace_id(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder
        from backend.services.portfolio_store import PortfolioStore

        direct = PortfolioRequest(
            holdings=[
                HoldingInput(
                    ticker="NVDA",
                    name="NVIDIA",
                    avg_cost=800,
                    current_price=1000,
                    shares=10,
                    asset_type="Stock",
                    category="Technology",
                )
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(self._portfolio_request(), name="wealth-demo")
            builder = PortfolioContextBuilder(store=store)

            request = PortfolioChatRequest(
                question="Use my direct portfolio",
                workspace_id="wealth-demo",
                portfolio=direct,
                language="en",
            )

            resolved = builder.resolve_portfolio(request)

            self.assertEqual(resolved.source, "direct_portfolio")
            self.assertEqual(resolved.portfolio.holdings[0].ticker, "NVDA")

    def test_missing_portfolio_and_workspace_returns_safe_error(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()

        with self.assertRaisesRegex(
            ValueError,
            "portfolio or workspace_id is required",
        ):
            builder.build_context(PortfolioChatRequest(question="Help me"))

    def test_top_holdings_are_sorted_by_weight(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="排序看看",
            portfolio=self._portfolio_request(),
            language="zh",
        )

        context = builder.build_context(request)
        weights = [item.weight_pct or 0 for item in context.top_holdings]

        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_suggested_review_items_are_included_from_portfolio_intelligence(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="哪些部位要先檢視？",
            portfolio=self._portfolio_request(),
            language="zh",
        )

        context = builder.build_context(request)

        self.assertGreaterEqual(len(context.suggested_review_items), 1)
        titles = " ".join(item.title for item in context.suggested_review_items).lower()
        self.assertIn("review", titles)

    def test_deterministic_answer_uses_non_advisory_wording(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="我的風險是不是太集中？",
            portfolio=self._portfolio_request(),
            language="zh",
        )

        response = builder.build_response(request)

        self.assertIn("不構成投資建議", response.safety_disclaimer)
        self.assertIn("檢視", response.answer)
        self.assertIn("情境", response.answer)

    def test_no_buy_or_sell_wording_is_generated(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="Should I rebalance my current holdings?",
            portfolio=self._portfolio_request(),
            language="en",
        )

        response = builder.build_response(request)
        combined = " ".join(
            [response.answer, *response.suggested_followups, response.safety_disclaimer]
        ).lower()

        self.assertNotIn(" buy ", f" {combined} ")
        self.assertNotIn(" sell ", f" {combined} ")
        self.assertNotIn("guaranteed", combined)
        self.assertNotIn("target price", combined)
        self.assertNotIn(" must ", f" {combined} ")


if __name__ == "__main__":
    unittest.main()
