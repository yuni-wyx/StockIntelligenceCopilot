from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ToolRouterFundamentalsTest(unittest.TestCase):
    def test_handle_fundamentals_tolerates_partial_fields(self) -> None:
        from backend.schemas.planner_schema import ToolCallSpec, ToolName
        from backend.services.tool_router import _handle_fundamentals
        from backend.tools.fundamentals_tool import CompanyProfile

        result = SimpleNamespace(
            profile=CompanyProfile(
                name="Taiwan Semiconductor Manufacturing Co.",
                market="TW",
                sector="Technology",
                industry="Semiconductors",
                exchange="TAI",
                description="Chip foundry.",
                employees=0,
                founded="Unknown",
                headquarters="Hsinchu, Taiwan",
                ceo="Unknown",
            ),
            valuation=None,
            income_statement=None,
            balance_sheet=None,
            estimates=None,
            competitive_advantages=None,
            key_risks=None,
        )

        spec = ToolCallSpec(
            tool=ToolName.FUNDAMENTALS,
            ticker="2330.TW",
            params={},
            priority=1,
            rationale="Need company context",
        )

        with patch("backend.services.tool_router.fetch_fundamentals", return_value=result):
            payload = _handle_fundamentals(spec)

        self.assertEqual(payload["market"], "TW")
        self.assertEqual(payload["profile"]["market"], "TW")
        self.assertEqual(payload["valuation"], {})
        self.assertEqual(payload["income_statement"], {})
        self.assertEqual(payload["balance_sheet"], {})
        self.assertIsNone(payload["estimates"])
        self.assertEqual(payload["competitive_advantages"], [])
        self.assertEqual(payload["key_risks"], [])

    def test_transient_provider_failure_retries_then_succeeds(self) -> None:
        from backend.schemas.planner_schema import ToolCallSpec, ToolName
        from backend.services.tool_router import ToolRouter

        spec = ToolCallSpec(
            tool=ToolName.MARKET_DATA,
            ticker="NVDA",
            params={},
            priority=1,
            rationale="test retry",
        )
        handler = unittest.mock.Mock(side_effect=[ConnectionError("temporary"), {"ok": True}])
        with patch.dict(
            "backend.services.tool_router._HANDLERS", {ToolName.MARKET_DATA: handler}
        ), patch(
            "backend.services.tool_router.PROVIDER_MAX_RETRIES", 1
        ), patch("backend.services.tool_router.time.sleep") as sleep:
            result = ToolRouter()._dispatch(spec)

        self.assertTrue(result.success)
        self.assertEqual(handler.call_count, 2)
        sleep.assert_called_once()

    def test_non_transient_provider_failure_is_not_retried(self) -> None:
        from backend.schemas.planner_schema import ToolCallSpec, ToolName
        from backend.services.tool_router import ToolRouter

        spec = ToolCallSpec(
            tool=ToolName.MARKET_DATA,
            ticker="NVDA",
            params={},
            priority=1,
            rationale="test no retry",
        )
        handler = unittest.mock.Mock(side_effect=ValueError("invalid provider payload"))
        with patch.dict(
            "backend.services.tool_router._HANDLERS", {ToolName.MARKET_DATA: handler}
        ), patch(
            "backend.services.tool_router.PROVIDER_MAX_RETRIES", 3
        ), patch("backend.services.tool_router.time.sleep") as sleep:
            result = ToolRouter()._dispatch(spec)

        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "provider")
        handler.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
