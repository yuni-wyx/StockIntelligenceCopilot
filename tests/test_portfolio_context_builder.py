from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioContextBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        from backend.services.portfolio_context_builder import PortfolioChatGeneration

        self.llm_patcher = patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(
                answer=None,
                mode="deterministic",
            ),
        )
        self.llm_patcher.start()
        self.tool_patchers = [
            patch(
                "backend.services.portfolio_context_builder.fetch_market_data",
                side_effect=lambda request: SimpleNamespace(
                    ticker=request.ticker,
                    market="TW" if request.ticker.endswith(".TW") else "US",
                    current_price={
                        "2204.TW": 91.0,
                        "3548.TW": 165.0,
                        "00878.TW": 22.5,
                    }.get(request.ticker, 100.0),
                    as_of="2026-07-13T00:00:00+00:00",
                ),
            ),
            patch(
                "backend.services.portfolio_context_builder.fetch_signal",
                side_effect=RuntimeError("signal unavailable"),
            ),
            patch(
                "backend.services.portfolio_context_builder.fetch_news",
                side_effect=RuntimeError("news unavailable"),
            ),
            patch(
                "backend.services.portfolio_context_builder.fetch_earnings",
                side_effect=RuntimeError("earnings unavailable"),
            ),
        ]
        for patcher in self.tool_patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.tool_patchers:
            patcher.stop()
        self.llm_patcher.stop()

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

    def test_saved_workspace_reload_preserves_all_three_demo_holdings(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(self._portfolio_request(), name="current")
            loaded = store.load_portfolio("current")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            tickers = [holding.ticker for holding in loaded.portfolio.holdings]

            builder = PortfolioContextBuilder(store=store)
            context = builder.build_context(
                PortfolioChatRequest(
                    question="我目前有哪些持股？",
                    workspace_id="current",
                    language="zh",
                )
            )

        self.assertEqual(tickers, ["00878.TW", "2204.TW", "3548.TW"])
        self.assertEqual(len(context.holdings), 3)
        self.assertEqual(
            [holding.ticker for holding in context.holdings],
            ["00878.TW", "2204.TW", "3548.TW"],
        )

    def test_leading_zero_ticker_remains_string_in_saved_workspace(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.services.portfolio_store import PortfolioStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = PortfolioStore(Path(tmp_dir) / "portfolio.sqlite3")
            store.save_portfolio(
                PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="00878.TW",
                            shares=2239,
                            avg_cost=21.76,
                        )
                    ]
                ),
                name="current",
            )
            loaded = store.load_portfolio("current")

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.portfolio.holdings[0].ticker, "00878.TW")
        self.assertIsInstance(loaded.portfolio.holdings[0].ticker, str)

    def test_distinct_questions_route_to_distinct_intents(self) -> None:
        from backend.services.portfolio_context_builder import classify_portfolio_chat_intent

        questions = {
            "我的投資組合是不是太集中？": "portfolio_concentration",
            "兆利和中華怎麼配置？": "holding_comparison",
            "如果科技股下跌，我該注意什麼？": "downside_scenario",
            "我的配息穩定嗎？": "income_review",
        }

        self.assertEqual(
            {question: classify_portfolio_chat_intent(question) for question in questions},
            questions,
        )

    def test_distinct_intents_produce_materially_different_answers(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        questions = [
            "我的投資組合是不是太集中？",
            "兆利和中華怎麼配置？",
            "如果科技股下跌，我該注意什麼？",
            "我的配息穩定嗎？",
        ]

        responses = [
            builder.build_response(
                PortfolioChatRequest(
                    question=question,
                    portfolio=self._portfolio_request(),
                    language="zh",
                )
            )
            for question in questions
        ]
        answers = [response.answer for response in responses]

        self.assertEqual(len(set(answers)), len(answers))
        self.assertIn("集中度判讀", answers[0])
        self.assertIn("持股比較", answers[1])
        self.assertIn("下行情境檢視", answers[2])
        self.assertIn("收益品質檢視", answers[3])

    def test_missing_current_prices_produce_caveat_not_fake_allocation(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="我的投資組合是不是太集中？",
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(ticker="2204.TW", shares=500, avg_cost=84.56),
                    HoldingInput(ticker="3548.TW", shares=410, avg_cost=180.49),
                    HoldingInput(ticker="00878.TW", shares=2239, avg_cost=21.76),
                ]
            ),
            language="zh",
        )

        with patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            side_effect=RuntimeError("network unavailable"),
        ):
            response = builder.build_response(request)

        self.assertIn("成本基礎占比", response.answer)
        self.assertIn("無法取得 2204.TW 的現價", response.answer)
        self.assertIn("成本基礎占比", response.answer)
        self.assertNotIn("Missing current value and price/shares", response.answer)
        self.assertTrue(response.portfolio_context.data_caveats)
        self.assertTrue(
            all(
                holding.weight_pct is None
                for holding in response.portfolio_context.holdings
            )
        )
        self.assertTrue(
            all(
                holding.unrealized_gain_loss is None
                for holding in response.portfolio_context.holdings
            )
        )

    def test_named_holding_comparison_references_both_requested_holdings(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="兆利和中華怎麼配置？",
                portfolio=self._portfolio_request(),
                language="zh",
            )
        )

        self.assertIn("3548.TW", response.answer)
        self.assertIn("2204.TW", response.answer)
        self.assertIn("named_holding_context", response.evidence_used)
        self.assertIn("目前無法取得 3548.TW 的相對訊號", response.answer)
        self.assertTrue(
            any("3548.TW 的相對訊號" in item for item in response.portfolio_context.data_caveats)
        )

    def test_missing_price_caveats_are_localized_and_deduplicated(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="兆利和中華目前可以怎麼配置？",
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(ticker="2204.TW", name="中華", shares=500, avg_cost=84.56),
                    HoldingInput(ticker="3548.TW", name="兆利", shares=410, avg_cost=180.49),
                ]
            ),
            language="zh",
        )

        with patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            side_effect=RuntimeError("market data unavailable"),
        ):
            response = builder.build_response(request)

        self.assertEqual(response.answer.count("目前無法取得 3548.TW 的現價"), 1)
        self.assertEqual(
            sum(
                "目前無法取得 3548.TW 的現價" in item
                for item in response.portfolio_context.data_caveats
            ),
            1,
        )
        combined = " ".join([response.answer, *response.portfolio_context.data_caveats])
        self.assertNotIn("Current price evidence was unavailable", combined)
        self.assertNotIn("Missing current value and price/shares", combined)

    def test_partial_price_coverage_does_not_show_false_full_weight(self) -> None:
        from types import SimpleNamespace

        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        def market_side_effect(request):
            if request.ticker == "2204.TW":
                return SimpleNamespace(
                    ticker="2204.TW",
                    market="TW",
                    current_price=91.0,
                    as_of="2026-07-13T00:00:00+00:00",
                )
            raise RuntimeError("market data unavailable")

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="兆利和中華目前可以怎麼配置？",
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(ticker="2204.TW", name="中華", shares=500, avg_cost=84.56),
                    HoldingInput(ticker="3548.TW", name="兆利", shares=410, avg_cost=180.49),
                ]
            ),
            language="zh",
        )

        with patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            side_effect=market_side_effect,
        ):
            response = builder.build_response(request)

        self.assertFalse(response.portfolio_context.coverage.allocation_complete)
        self.assertEqual(response.portfolio_context.coverage.priced_holdings_count, 1)
        self.assertEqual(response.portfolio_context.coverage.unpriced_holdings_count, 1)
        self.assertIn("無法可靠計算完整投資組合權重", response.answer)
        self.assertIn("中華（2204.TW）：成本基礎占比 36.36%", response.answer)
        self.assertIn("兆利（3548.TW）：成本基礎占比 63.64%", response.answer)
        self.assertNotIn("權重 100.00%", response.answer)
        self.assertNotIn("100% 的投資組合", response.answer)
        self.assertIsNone(response.portfolio_context.total_current_value)
        self.assertTrue(
            all(holding.weight_pct is None for holding in response.portfolio_context.holdings)
        )

    def test_all_current_price_case_still_calculates_current_weights(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="兆利和中華目前可以怎麼配置？",
                portfolio=self._portfolio_request(),
                language="zh",
            )
        )

        self.assertTrue(response.portfolio_context.coverage.allocation_complete)
        self.assertGreater(response.portfolio_context.total_current_value or 0, 0)
        self.assertTrue(
            any(holding.weight_pct is not None for holding in response.portfolio_context.holdings)
        )

    def test_llm_prompt_contains_partial_coverage_grounding_rules(self) -> None:
        source = Path("backend/services/portfolio_context_builder.py").read_text()

        self.assertIn("Never describe a priced subset as the full portfolio.", source)
        self.assertIn("coverage.allocation_complete", source)
        self.assertIn("Distinguish current-value weight from cost-basis exposure.", source)

    def test_missing_news_still_produces_useful_answer(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="最近有什麼新聞要注意？",
                portfolio=self._portfolio_request(),
                language="zh",
            )
        )

        self.assertIn("目前仍可用的投資組合脈絡", response.answer)
        self.assertIn("新聞工具目前未取得", response.answer)
        self.assertNotIn("目前可用結論：請以 evidence_used", response.answer)

    def test_missing_earnings_does_not_fabricate_dates(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="需要等 Q2 財報嗎？",
                portfolio=self._portfolio_request(),
                language="zh",
            )
        )

        self.assertIn("不會猜測 Q2", response.answer)
        self.assertIn("目前無法取得", response.answer)
        self.assertNotIn("2026-", response.answer)

    def test_incomplete_classification_adds_defensive_allocation_caveat(self) -> None:
        from backend.schemas.portfolio import HoldingInput, PortfolioRequest
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="哪些持股需要優先檢查？",
                portfolio=PortfolioRequest(
                    holdings=[
                        HoldingInput(
                            ticker="2204.TW",
                            name="中華",
                            shares=500,
                            avg_cost=84.56,
                            current_price=91,
                        )
                    ]
                ),
                language="zh",
            )
        )

        self.assertIn("防禦型配置判讀只能作為粗略檢查", response.answer)

    def test_saved_portfolio_answer_has_no_save_workspace_reminder(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import PortfolioContextBuilder

        builder = PortfolioContextBuilder()
        response = builder.build_response(
            PortfolioChatRequest(
                question="我的投資組合是不是太集中？",
                portfolio=self._portfolio_request(),
                language="zh",
            )
        )

        combined = " ".join([response.answer, *response.suggested_followups])
        self.assertNotIn("保存工作區", combined)
        self.assertNotIn("儲存工作區", combined)


if __name__ == "__main__":
    unittest.main()
