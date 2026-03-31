from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ApiPresentationTest(unittest.TestCase):
    def test_error_output_for_explain_has_safe_shape(self) -> None:
        from backend.api.presentation import error_output

        payload = error_output("explain tsla", RuntimeError("boom"))

        self.assertEqual(payload["ticker"], "TSLA")
        self.assertEqual(payload["overall_confidence"], 0)
        self.assertEqual(payload["ranked_causes"], [])
        self.assertIn("boom", payload["price_move_summary"])

    def test_partial_research_snapshot_has_expected_fields(self) -> None:
        from backend.api.presentation import partial_output_snapshot

        class _Plan:
            tool_calls = [object(), object(), object()]

        payload = partial_output_snapshot("research nvda", "planning", plan=_Plan())

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["ticker"], "NVDA")
        self.assertEqual(payload["overall_sentiment"], "NEUTRAL")
        self.assertIn("Collecting 3 evidence sources", payload["fundamental_summary"])


if __name__ == "__main__":
    unittest.main()
