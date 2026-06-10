from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .portfolio import PortfolioRequest
from .portfolio_intelligence import ReviewItem


class PortfolioContextHolding(BaseModel):
    ticker: str
    name: str | None = None
    shares: float | None = None
    avg_cost: float | None = None
    current_price: float | None = None
    current_value: float | None = None
    cost_basis: float | None = None
    unrealized_gain_loss: float | None = None
    return_pct: float | None = None
    weight_pct: float | None = None


class PortfolioContext(BaseModel):
    total_current_value: float | None = None
    total_cost_basis: float | None = None
    total_unrealized_gain_loss: float | None = None
    total_return_pct: float | None = None
    top_holdings: list[PortfolioContextHolding] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    suggested_review_items: list[ReviewItem] = Field(default_factory=list)
    concentration_summary: str = ""
    income_summary: str = ""
    holdings: list[PortfolioContextHolding] = Field(default_factory=list)
    data_caveats: list[str] = Field(default_factory=list)


class PortfolioChatRequest(BaseModel):
    question: str
    workspace_id: str | None = None
    portfolio: PortfolioRequest | None = None
    language: Literal["en", "zh"] | None = None


class PortfolioChatResponse(BaseModel):
    answer: str
    portfolio_context: PortfolioContext
    evidence_used: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    safety_disclaimer: str
