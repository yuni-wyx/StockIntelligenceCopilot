from __future__ import annotations

from datetime import datetime
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


class MarketEvidence(BaseModel):
    ticker: str
    market: str | None = None
    current_price: float | None = None
    currency: str | None = None
    as_of: str | None = None


class HoldingCalculation(BaseModel):
    ticker: str
    cost_basis: float | None = None
    current_value: float | None = None
    unrealized_gain_loss: float | None = None
    return_pct: float | None = None
    weight_pct: float | None = None


class NewsEvidence(BaseModel):
    ticker: str
    title: str
    published_at: str | None = None
    source: str | None = None
    summary: str | None = None
    url: str | None = None
    sentiment: str | None = None
    retrieved_at: str


class EarningsEvidence(BaseModel):
    ticker: str
    next_earnings_date: str | None = None
    days_to_next_earnings: int | None = None
    latest_report_date: str | None = None
    avg_eps_surprise_pct: float | None = None
    avg_post_earnings_move_pct: float | None = None
    beat_rate: float | None = None
    caveats: list[str] = Field(default_factory=list)


class SignalEvidence(BaseModel):
    ticker: str
    benchmark: str
    horizon_days: int
    signal_score: float
    signal_band: str
    confidence: str
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    data_caveats: list[str] = Field(default_factory=list)
    disclaimer: str


class PortfolioChatEvidenceBundle(BaseModel):
    portfolio_context: PortfolioContext
    market_data: dict[str, MarketEvidence] = Field(default_factory=dict)
    calculations: dict[str, HoldingCalculation] = Field(default_factory=dict)
    news: dict[str, list[NewsEvidence]] = Field(default_factory=dict)
    earnings: dict[str, EarningsEvidence] = Field(default_factory=dict)
    signals: dict[str, SignalEvidence] = Field(default_factory=dict)
    tool_errors: list[str] = Field(default_factory=list)
    data_caveats: list[str] = Field(default_factory=list)
    generated_at: datetime


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
    generation_metadata: dict[str, str | bool | list[str] | None] | None = None
