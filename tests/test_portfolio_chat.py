from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioChatApiTest(unittest.TestCase):
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
                    "ticker": "2204.TW",
                    "name": "中華",
                    "avg_cost": 84.56,
                    "current_price": 53.1,
                    "shares": 500,
                    "asset_type": "Stock",
                    "category": "Auto",
                },
            ],
            "base_currency": "TWD",
        }

    def _three_holding_payload(self) -> dict:
        return {
            "holdings": [
                {
                    "ticker": "2204.TW",
                    "name": "中華",
                    "shares": 500,
                    "avg_cost": 84.56,
                    "current_price": 91,
                },
                {
                    "ticker": "3548.TW",
                    "name": "兆利",
                    "shares": 410,
                    "avg_cost": 180.49,
                    "current_price": 165,
                },
                {
                    "ticker": "00878.TW",
                    "name": "國泰永續高股息",
                    "shares": 2239,
                    "avg_cost": 21.76,
                    "current_price": 22.5,
                },
            ],
            "base_currency": "TWD",
        }

    def test_direct_portfolio_chat_success(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "我的風險是不是太集中？",
                "portfolio": self._portfolio_payload(),
                "language": "zh",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("portfolio_context", payload)
        self.assertIn("safety_disclaimer", payload)
        self.assertIn("evidence_used", payload)
        self.assertIn("suggested_followups", payload)
        self.assertEqual(payload["evidence_used"][0], "direct_portfolio")

    def test_saved_workspace_chat_success(self) -> None:
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
                            shares=100,
                            avg_cost=21.76,
                        )
                    ]
                ),
                name="current",
            )
            with patch.object(main, "portfolio_store", store):
                response = TestClient(main.app).post(
                    "/api/portfolio/chat",
                    json={
                        "question": "What should I review first?",
                        "workspace_id": "current",
                        "language": "en",
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["evidence_used"][0], "saved_workspace")
        self.assertGreater(payload["portfolio_context"]["total_current_value"], 0)

    def test_missing_portfolio_or_workspace_returns_400(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={"question": "Help me review this"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "A portfolio or workspace_id is required to build portfolio context.",
        )

    def test_no_buy_or_sell_wording(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "How should I review this portfolio?",
                "portfolio": self._portfolio_payload(),
                "language": "en",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        combined = " ".join(
            [
                payload["answer"],
                payload["safety_disclaimer"],
                *payload["suggested_followups"],
            ]
        ).lower()
        self.assertNotIn(" buy ", f" {combined} ")
        self.assertNotIn(" sell ", f" {combined} ")
        self.assertNotIn("target price", combined)
        self.assertNotIn("guaranteed", combined)

    def test_llm_portfolio_chat_path_is_used_when_enabled(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="What should I review first?",
            portfolio=self._portfolio_payload(),
            language="en",
        )

        with patch(
            "backend.services.portfolio_context_builder.llm_portfolio_chat_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder.OPENAI_API_KEY",
            "sk-test",
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(
                answer="LLM answer",
                mode="llm",
                provider="openai",
                model="gpt-4o-mini",
                fallback_used=False,
            ),
        ):
            response = builder.build_response(request)

        self.assertEqual(response.answer, "LLM answer")
        self.assertIn("llm_portfolio_chat", response.evidence_used)

    def test_generation_metadata_reports_llm_path_when_enabled(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="What should I review first?",
            portfolio=self._portfolio_payload(),
            language="en",
        )

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(
                answer="LLM answer",
                mode="llm",
                provider="openai",
                model="gpt-4o-mini",
                fallback_used=False,
            ),
        ):
            response = builder.build_response(request)

        self.assertEqual(response.generation_metadata["mode"], "llm")
        self.assertEqual(response.generation_metadata["provider"], "openai")
        self.assertEqual(response.generation_metadata["model"], "gpt-4o-mini")
        self.assertFalse(response.generation_metadata["fallback_used"])

    def test_generation_metadata_reports_deterministic_path(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="What holdings do I have?",
            portfolio=self._portfolio_payload(),
            language="en",
        )

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(answer=None, mode="deterministic"),
        ):
            response = builder.build_response(request)

        self.assertEqual(response.generation_metadata["mode"], "deterministic")
        self.assertIsNone(response.generation_metadata["provider"])
        self.assertFalse(response.generation_metadata["fallback_used"])

    def test_generation_metadata_reports_provider_failure_fallback(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()
        request = PortfolioChatRequest(
            question="What holdings do I have?",
            portfolio=self._portfolio_payload(),
            language="en",
        )

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(
                answer=None,
                mode="deterministic",
                provider="openai",
                model="gpt-4o-mini",
                fallback_used=True,
            ),
        ):
            response = builder.build_response(request)

        self.assertEqual(response.generation_metadata["mode"], "deterministic")
        self.assertEqual(response.generation_metadata["provider"], "openai")
        self.assertTrue(response.generation_metadata["fallback_used"])
        self.assertNotIn("sk-", str(response.model_dump()))
        self.assertNotIn("provider stack", str(response.model_dump()).lower())

    def test_holding_comparison_metadata_lists_planned_and_called_tools(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(answer=None, mode="deterministic"),
        ):
            response = builder.build_response(
                PortfolioChatRequest(
                    question="兆利跟中華目前可以怎麼配置？需要等 Q2 財報嗎？",
                    portfolio=self._three_holding_payload(),
                    language="zh",
                )
            )

        metadata = response.generation_metadata
        self.assertEqual(metadata["intent"], "holding_comparison")
        self.assertIn("market_data", metadata["tools_planned"])
        self.assertIn("signal", metadata["tools_planned"])
        self.assertIn("news", metadata["tools_planned"])
        self.assertIn("earnings", metadata["tools_planned"])
        self.assertIn("market_data", metadata["tools_called"])
        self.assertIn("signal", metadata["tools_called"])
        self.assertIn("news", metadata["tools_called"])
        self.assertIn("earnings", metadata["tools_called"])

    def test_unsafe_llm_name_ticker_mismatch_falls_back(self) -> None:
        from backend.schemas.portfolio_chat import PortfolioChatRequest
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        builder = PortfolioContextBuilder()

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            return_value=PortfolioChatGeneration(
                answer="兆利（2204.TW）表現較強，中華（3548.TW）需要監控。",
                mode="llm",
                provider="openai",
                model="gpt-4o-mini",
                fallback_used=False,
            ),
        ):
            response = builder.build_response(
                PortfolioChatRequest(
                    question="兆利和中華怎麼配置？",
                    portfolio=self._three_holding_payload(),
                    language="zh",
                )
            )

        self.assertEqual(response.generation_metadata["mode"], "deterministic")
        self.assertTrue(response.generation_metadata["fallback_used"])
        self.assertNotIn("兆利（2204.TW）", response.answer)

    def test_llm_receives_structured_evidence_bundle_with_computed_values(self) -> None:
        from backend.schemas.portfolio_chat import (
            PortfolioChatEvidenceBundle,
            PortfolioChatRequest,
        )
        from backend.services.portfolio_context_builder import (
            PortfolioChatGeneration,
            PortfolioContextBuilder,
        )

        captured = {}

        def fake_llm(*args, **kwargs):
            captured["bundle"] = args[1]
            return PortfolioChatGeneration(
                answer="grounded answer",
                mode="llm",
                provider="openai",
                model="gpt-4o-mini",
                fallback_used=False,
            )

        builder = PortfolioContextBuilder()

        with patch(
            "backend.services.portfolio_context_builder._build_llm_answer",
            side_effect=fake_llm,
        ):
            response = builder.build_response(
                PortfolioChatRequest(
                    question="兆利和中華怎麼配置？",
                    portfolio=self._three_holding_payload(),
                    language="zh",
                )
            )

        bundle = captured["bundle"]
        self.assertIsInstance(bundle, PortfolioChatEvidenceBundle)
        self.assertEqual(response.answer, "grounded answer")
        self.assertEqual(bundle.calculations["3548.TW"].current_value, 67650.0)
        self.assertEqual(bundle.calculations["2204.TW"].weight_pct, 27.82)

    def test_response_includes_portfolio_context_and_safety_fields(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "配息收入穩定嗎？",
                "portfolio": self._portfolio_payload(),
                "language": "zh",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("holdings", payload["portfolio_context"])
        self.assertIn("top_holdings", payload["portfolio_context"])
        self.assertTrue(payload["safety_disclaimer"])
        self.assertTrue(payload["suggested_followups"])

    def test_portfolio_chat_context_includes_all_three_demo_holdings(self) -> None:
        from backend.main import app

        response = TestClient(app).post(
            "/api/portfolio/chat",
            json={
                "question": "我目前有哪些持股？",
                "portfolio": self._three_holding_payload(),
                "language": "zh",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        tickers = [
            holding["ticker"]
            for holding in payload["portfolio_context"]["holdings"]
        ]
        self.assertEqual(tickers, ["2204.TW", "3548.TW", "00878.TW"])
        self.assertIn("00878.TW", payload["answer"])

    def test_tool_failure_does_not_fail_chat_or_fabricate_price(self) -> None:
        from backend.main import app

        portfolio = {
            "holdings": [
                {"ticker": "2204.TW", "shares": 500, "avg_cost": 84.56},
                {"ticker": "3548.TW", "shares": 410, "avg_cost": 180.49},
            ],
            "base_currency": "TWD",
        }

        with patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            side_effect=RuntimeError("market data unavailable"),
        ):
            response = TestClient(app).post(
                "/api/portfolio/chat",
                json={
                    "question": "我的投資組合是不是太集中？",
                    "portfolio": portfolio,
                    "language": "zh",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("成本基礎占比", payload["answer"])
        self.assertIn("目前無法取得 2204.TW 的現價", str(payload))
        self.assertNotIn("Current price evidence was unavailable", str(payload))
        self.assertNotIn("Missing current value and price/shares", str(payload))
        self.assertIsNone(payload["portfolio_context"]["holdings"][0]["current_price"])
        self.assertIsNone(payload["portfolio_context"]["holdings"][0]["weight_pct"])

    def test_generation_metadata_reports_caveat_dedup_counts(self) -> None:
        from backend.main import app

        portfolio = {
            "holdings": [
                {"ticker": "2204.TW", "shares": 500, "avg_cost": 84.56},
                {"ticker": "3548.TW", "shares": 410, "avg_cost": 180.49},
            ],
            "base_currency": "TWD",
        }

        with patch(
            "backend.services.portfolio_context_builder._generation_metadata_enabled",
            return_value=True,
        ), patch(
            "backend.services.portfolio_context_builder.fetch_market_data",
            side_effect=RuntimeError("market data unavailable"),
        ):
            response = TestClient(app).post(
                "/api/portfolio/chat",
                json={
                    "question": "我的投資組合是不是太集中？",
                    "portfolio": portfolio,
                    "language": "zh",
                },
            )

        self.assertEqual(response.status_code, 200)
        metadata = response.json()["generation_metadata"]
        self.assertIn("caveats_before_dedup", metadata)
        self.assertIn("caveats_after_dedup", metadata)
        self.assertIn("目前無法取得 3548.TW 的現價", " ".join(metadata["caveats_after_dedup"]))

    def test_internal_failure_returns_500_without_traceback(self) -> None:
        from backend.main import app

        with patch(
            "backend.main.PortfolioChatOrchestrator.orchestrate",
            side_effect=RuntimeError("secret stack detail"),
        ):
            response = TestClient(app).post(
                "/api/portfolio/chat",
                json={
                    "question": "How should I review this portfolio?",
                    "portfolio": self._portfolio_payload(),
                    "language": "en",
                },
            )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["error"], "Portfolio-aware chat failed.")
        self.assertNotIn("secret stack detail", str(payload))


if __name__ == "__main__":
    unittest.main()
