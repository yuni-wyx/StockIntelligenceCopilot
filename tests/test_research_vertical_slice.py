from __future__ import annotations

import unittest
from pathlib import Path

from backend.providers.registry import get_research_provider
from backend.providers.sec_edgar import FixtureSecEdgarProvider
from backend.schemas.agent import AgentEvidenceBundle
from backend.schemas.research import ResearchClaim
from backend.services.evidence_provenance import extract_source_metadata
from backend.services.research_evidence import load_fixture_research_evidence
from backend.services.security_resolver import resolve_security


class ResearchVerticalSliceTest(unittest.TestCase):
    def setUp(self) -> None:
        fixture = Path(__file__).parents[1] / "backend/data/fixtures/sec_edgar_nvda_10k.json"
        self.provider = FixtureSecEdgarProvider(fixture)

    def test_fixture_resolves_identity_and_filing_with_tier_one_provenance(self) -> None:
        identity = self.provider.resolve_security("nvda")
        filings = self.provider.get_filings(identity, form_types=["10-K"])

        self.assertEqual(identity.cik, "0001045810")
        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0].source.source_tier, "tier_1")
        self.assertEqual(filings[0].source.document_id, "0001045810-26-000012")
        self.assertEqual(filings[0].facts[0].source.source_id, filings[0].source.source_id)

    def test_provider_filters_form_type_and_limit(self) -> None:
        identity = self.provider.resolve_security("NVDA")
        self.assertEqual(self.provider.get_filings(identity, form_types=["10-Q"]), [])
        self.assertEqual(len(self.provider.get_filings(identity, limit=1)), 1)

    def test_registry_keeps_provider_boundary_fixture_only(self) -> None:
        provider = get_research_provider("NVDA")
        self.assertEqual(provider.provider_name, "sec_edgar_fixture")
        identity = provider.resolve_security("NVDA")
        self.assertEqual(
            {filing.form_type for filing in provider.get_filings(identity)},
            {"10-K", "10-Q", "8-K"},
        )

    def test_research_claim_rejects_invalid_confidence(self) -> None:
        with self.assertRaises(ValueError):
            ResearchClaim(claim_text="x", claim_type="fact", confidence=1.1)

    def test_runtime_research_evidence_exposes_filing_and_claims(self) -> None:
        evidence = load_fixture_research_evidence(resolve_security("NVDA"))
        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual(evidence.sources[0].source_tier, "tier_1")
        self.assertEqual(len(evidence.claims), 6)

        bundle = AgentEvidenceBundle(
            external_evidence={
                "research_evidence": evidence.model_dump(mode="json"),
            }
        )
        sources = extract_source_metadata(bundle)
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(source.source_type == "filing" for source in sources))
        self.assertTrue(all(source.source_tier == "tier_1" for source in sources))
        self.assertEqual(sources[0].url, evidence.sources[0].source_url)

    def test_research_evidence_flags_material_fundamental_conflicts(self) -> None:
        evidence = load_fixture_research_evidence(
            resolve_security("NVDA"),
            fundamentals={
                "income_statement": {
                    "revenue_billions": 100.0,
                    "net_income_billions": 98.5,
                }
            },
        )
        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual(len(evidence.conflicts), 1)
        self.assertIn("Revenue differs", evidence.conflicts[0])

    def test_research_evidence_includes_additional_facts_and_other_company(self) -> None:
        nvda = load_fixture_research_evidence(resolve_security("NVDA"))
        self.assertIsNotNone(nvda)
        assert nvda is not None
        self.assertEqual(len(nvda.filings), 3)
        self.assertEqual(
            {fact.metric for fact in nvda.facts},
            {"Revenue", "NetIncome", "OperatingCashFlow", "DilutedEPS"},
        )

        aapl = load_fixture_research_evidence(resolve_security("AAPL"))
        self.assertIsNotNone(aapl)
        assert aapl is not None
        self.assertEqual(aapl.identity.cik, "0000320193")
        self.assertEqual(
            {fact.metric for fact in aapl.facts},
            {"Revenue", "NetIncome", "OperatingCashFlow", "TotalAssets"},
        )

    def test_missing_company_fixture_is_reported_as_data_gap(self) -> None:
        evidence = load_fixture_research_evidence(resolve_security("TSLA"))
        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual(evidence.filings, [])
        self.assertTrue(evidence.data_gaps)


if __name__ == "__main__":
    unittest.main()
