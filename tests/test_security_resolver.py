from __future__ import annotations

import unittest

from backend.services.security_resolver import resolve_security


class SecurityResolverTest(unittest.TestCase):
    def test_resolves_us_symbol_without_inventing_company_name(self) -> None:
        identity = resolve_security("NVDA")
        self.assertEqual(identity.canonical_id, "US:NVDA")
        self.assertEqual(identity.currency, "USD")
        self.assertIsNone(identity.company_name)

    def test_resolves_taiwan_alias_and_preserves_input_alias(self) -> None:
        identity = resolve_security("台積電", exchange="TWSE")
        self.assertEqual(identity.symbol, "2330.TW")
        self.assertEqual(identity.company_name, "台積電")
        self.assertEqual(identity.currency, "TWD")
        self.assertEqual(identity.aliases, ["台積電"])


if __name__ == "__main__":
    unittest.main()
