"""Fixture-backed SEC provider for offline Research development.

This adapter intentionally does not make network requests.  It establishes the
canonical filing contract before a live SEC adapter is introduced.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..schemas.research import (
    FilingDocument,
    FundamentalFact,
    SecurityIdentity,
    SourceMetadata,
)


class FixtureSecEdgarProvider:
    provider_name = "sec_edgar_fixture"

    def __init__(self, fixture_path: str | Path) -> None:
        self.fixture_path = Path(fixture_path)

    @staticmethod
    def _parse_optional_datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    def _load_payloads(self) -> list[dict]:
        paths = (
            sorted(self.fixture_path.glob("*.json"))
            if self.fixture_path.is_dir()
            else [self.fixture_path]
        )
        with_paths = []
        for path in paths:
            with path.open(encoding="utf-8") as handle:
                with_paths.append(json.load(handle))
        return with_paths

    def resolve_security(self, symbol: str) -> SecurityIdentity:
        for payload in self._load_payloads():
            identity = payload["identity"]
            if identity["symbol"].upper() == symbol.upper():
                return SecurityIdentity.model_validate(identity)
        raise ValueError(f"Fixture has no identity for symbol {symbol}")

    def get_filings(
        self,
        identity: SecurityIdentity,
        *,
        form_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[FilingDocument]:
        requested = {value.upper() for value in form_types or []}
        retrieved_at = datetime.now(timezone.utc)
        filings: list[FilingDocument] = []
        for payload in self._load_payloads():
            if payload.get("identity", {}).get("symbol", "").upper() != identity.symbol.upper():
                continue
            for raw in payload.get("filings", []):
                if requested and raw["form_type"].upper() not in requested:
                    continue
                source = SourceMetadata(
                    source_id=f"sec:{raw['accession_number']}",
                    provider="SEC EDGAR",
                    source_tier="tier_1",
                    source_url=raw["url"],
                    document_id=raw["accession_number"],
                    published_at=datetime.fromisoformat(raw["filing_date"]),
                    retrieved_at=retrieved_at,
                    data_as_of=self._parse_optional_datetime(raw.get("period_end")),
                    timezone="UTC",
                    freshness="historical_filing",
                    license_note=(
                        "SEC public filing; verify current SEC usage requirements "
                        "for production."
                    ),
                )
                facts = [
                    FundamentalFact(
                        **{key: value for key, value in fact.items() if key != "period_end"},
                        source=source,
                        period_end=self._parse_optional_datetime(fact.get("period_end")),
                    )
                    for fact in raw.get("facts", [])
                ]
                filing_fields = {
                    key: value
                    for key, value in raw.items()
                    if key not in {"filing_date", "period_end", "facts"}
                }
                filings.append(
                    FilingDocument(
                        **filing_fields,
                        filing_date=datetime.fromisoformat(raw["filing_date"]),
                        period_end=self._parse_optional_datetime(raw.get("period_end")),
                        identity=identity,
                        source=source,
                        facts=facts,
                    )
                )
        return filings[:limit]
