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


if __name__ == "__main__":
    unittest.main()
