"""Canonical data contracts for the Research vertical slice."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SecurityIdentity(BaseModel):
    canonical_id: str
    symbol: str
    exchange: str | None = None
    mic: str | None = None
    company_name: str | None = None
    asset_type: str | None = None
    country: str | None = None
    currency: str | None = None
    isin: str | None = None
    cik: str | None = None
    lei: str | None = None
    provider_identifiers: dict[str, str] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    source_id: str
    provider: str
    source_tier: Literal["tier_1", "tier_2", "tier_3", "tier_4"]
    source_url: str | None = None
    document_id: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    effective_at: datetime | None = None
    data_as_of: datetime | None = None
    timezone: str | None = None
    freshness: str | None = None
    license_note: str | None = None


class FundamentalFact(BaseModel):
    metric: str
    value: float | str | None = None
    unit: str | None = None
    currency: str | None = None
    fiscal_period: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    filed_at: datetime | None = None
    form_type: str | None = None
    amended: bool | None = None
    source: SourceMetadata


class FilingDocument(BaseModel):
    document_id: str
    form_type: str
    filing_date: datetime
    period_end: datetime | None = None
    accession_number: str | None = None
    title: str
    url: str
    identity: SecurityIdentity
    source: SourceMetadata
    facts: list[FundamentalFact] = Field(default_factory=list)


class ResearchClaim(BaseModel):
    claim_text: str
    claim_type: Literal["fact", "calculation", "inference", "opinion"]
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    data_as_of: datetime | None = None
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ResearchConflict(BaseModel):
    message: str
    metric: str
    severity: Literal["low", "medium", "high"]
    filing_value: float
    fundamentals_value: float
    source_id: str


class ResearchEvidence(BaseModel):
    identity: SecurityIdentity
    filings: list[FilingDocument] = Field(default_factory=list)
    facts: list[FundamentalFact] = Field(default_factory=list)
    sources: list[SourceMetadata] = Field(default_factory=list)
    claims: list[ResearchClaim] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    conflict_details: list[ResearchConflict] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
