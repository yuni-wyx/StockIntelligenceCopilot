from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SymbolNormalizationTest(unittest.TestCase):
    def test_normalize_taiwan_inputs(self) -> None:
        from backend.symbols import detect_market, normalize_symbol

        self.assertEqual(normalize_symbol("2330"), "2330.TW")
        self.assertEqual(normalize_symbol("2330.TW"), "2330.TW")
        self.assertEqual(normalize_symbol("台積電"), "2330.TW")
        self.assertEqual(detect_market("2330"), "TW")
        self.assertEqual(detect_market("NVDA"), "US")

    def test_extract_symbols_from_text_supports_tw_aliases(self) -> None:
        from backend.symbols import extract_symbols_from_text

        self.assertEqual(extract_symbols_from_text("explain 台積電"), ["2330.TW"])
        self.assertEqual(extract_symbols_from_text("research 2330"), ["2330.TW"])
        self.assertEqual(extract_symbols_from_text("watchlist NVDA 台積電"), ["NVDA", "2330.TW"])


if __name__ == "__main__":
    unittest.main()
