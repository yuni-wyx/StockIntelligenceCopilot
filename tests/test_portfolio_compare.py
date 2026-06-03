from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PortfolioCompareTest(unittest.TestCase):
    def test_compare_portfolio_scenarios_returns_ranked_items(self) -> None:
        from backend.pipeline.portfolio_orchestrator import compare_portfolio_scenarios
        from backend.schemas.portfolio import (
            HoldingInput,
            NamedScenario,
            PortfolioRequest,
            ReallocationAction,
            ScenarioComparisonRequest,
        )

        request = ScenarioComparisonRequest(
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(
                        ticker="00878",
                        name="Income ETF",
                        avg_cost=21.76,
                        current_price=32.06,
                        shares=2239,
                        asset_type="ETF",
                        category="High Dividend",
                    )
                ]
            ),
            scenarios=[
                NamedScenario(
                    name="Scenario A",
                    actions=[
                        ReallocationAction(action="sell", ticker="00878", percentage=50),
                        ReallocationAction(action="buy", ticker="2330", amount=35000),
                    ],
                ),
                NamedScenario(
                    name="Scenario B",
                    actions=[ReallocationAction(action="hold_cash", ticker="CASH", amount=5000)],
                ),
            ],
        )

        def fake_enrich(holding):
            canonical = holding.ticker if holding.ticker.endswith(".TW") else f"{holding.ticker}.TW"
            price = 32.06 if "00878" in canonical else 900.0
            category = (
                holding.category
                or ("High Dividend" if "00878" in canonical else "Technology")
            )
            theme = "Defensive / Income" if "00878" in canonical else "Technology / AI"
            updated = holding.model_copy(
                update={
                    "ticker": canonical,
                    "name": holding.name or canonical,
                    "current_price": price,
                    "asset_type": (
                        holding.asset_type
                        or ("ETF" if "00878" in canonical else "Stock")
                    ),
                    "category": category,
                }
            )
            return updated, {
                "name": updated.name,
                "current_price": price,
                "sector": category,
                "theme": theme,
                "dividend_yield": 0.06 if "00878" in canonical else 0.0,
                "annual_dividend_per_share": 1.8 if "00878" in canonical else None,
                "category": category,
                "asset_type": updated.asset_type,
                "news": [],
            }

        with patch(
            "backend.pipeline.portfolio_orchestrator._enrich_holding",
            side_effect=fake_enrich,
        ):
            result = compare_portfolio_scenarios(request)

        self.assertEqual(len(result.scenarios), 2)
        self.assertEqual(
            sorted(item.recommendation_rank for item in result.scenarios),
            [1, 2],
        )

    def test_compare_impl_reuses_base_analysis_for_scenarios(self) -> None:
        from backend.pipeline import portfolio_orchestrator
        from backend.schemas.portfolio import (
            HoldingInput,
            NamedScenario,
            PortfolioRequest,
            ReallocationAction,
            ScenarioComparisonRequest,
        )

        request = ScenarioComparisonRequest(
            portfolio=PortfolioRequest(
                holdings=[
                    HoldingInput(
                        ticker="00878",
                        name="Income ETF",
                        avg_cost=21.76,
                        current_price=32.06,
                        shares=2239,
                        asset_type="ETF",
                        category="High Dividend",
                    )
                ]
            ),
            scenarios=[
                NamedScenario(
                    name="Trim income",
                    actions=[ReallocationAction(action="sell", ticker="00878", percentage=10)],
                ),
                NamedScenario(
                    name="Hold cash",
                    actions=[ReallocationAction(action="hold_cash", ticker="CASH", amount=5000)],
                ),
            ],
        )

        def fake_enrich(holding):
            canonical = holding.ticker if holding.ticker.endswith(".TW") else f"{holding.ticker}.TW"
            updated = holding.model_copy(
                update={
                    "ticker": canonical,
                    "name": holding.name or canonical,
                    "current_price": holding.current_price or 32.06,
                    "asset_type": holding.asset_type or "ETF",
                    "category": holding.category or "High Dividend",
                }
            )
            return updated, {
                "name": updated.name,
                "current_price": updated.current_price,
                "sector": updated.category,
                "theme": "Defensive / Income",
                "dividend_yield": 0.06,
                "annual_dividend_per_share": 1.8,
                "category": updated.category,
                "asset_type": updated.asset_type,
                "news": [],
            }

        with patch(
            "backend.pipeline.portfolio_orchestrator._enrich_holding",
            side_effect=fake_enrich,
        ), patch(
            "backend.pipeline.portfolio_orchestrator.run_portfolio_scenario",
            side_effect=AssertionError("compare impl should not call the runtime wrapper"),
        ), patch.object(
            portfolio_orchestrator,
            "analyze_portfolio_with_evidence",
            wraps=portfolio_orchestrator.analyze_portfolio_with_evidence,
        ) as analyze_mock:
            result = portfolio_orchestrator._compare_portfolio_scenarios_impl(request)

        self.assertEqual(len(result.scenarios), 2)
        self.assertEqual(analyze_mock.call_count, 1 + len(request.scenarios))
