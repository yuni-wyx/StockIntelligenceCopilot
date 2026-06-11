from __future__ import annotations

from pydantic import BaseModel, Field

from .portfolio import HoldingInput


class PortfolioImportIssue(BaseModel):
    row_number: int
    message: str


class PortfolioImportPreviewResponse(BaseModel):
    holdings: list[HoldingInput] = Field(default_factory=list)
    errors: list[PortfolioImportIssue] = Field(default_factory=list)
    warnings: list[PortfolioImportIssue] = Field(default_factory=list)
    detected_columns: list[str] = Field(default_factory=list)
    imported_count: int = 0
    total_rows: int = 0
