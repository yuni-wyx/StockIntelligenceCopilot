"""Provider adapter contracts used by Research orchestration."""

from __future__ import annotations

from typing import Protocol

from ..schemas.research import FilingDocument, SecurityIdentity


class ResearchProvider(Protocol):
    """Provider boundary; implementations must return canonical models."""

    provider_name: str

    def resolve_security(self, symbol: str) -> SecurityIdentity:
        ...

    def get_filings(
        self,
        identity: SecurityIdentity,
        *,
        form_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[FilingDocument]:
        ...
