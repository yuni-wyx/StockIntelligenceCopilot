from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HoldingInput(BaseModel):
    ticker: str
    name: str | None = None
    avg_cost: float | None = None
    current_price: float | None = None
    current_value: float | None = None
    shares: float | None = None
    asset_type: str | None = None
    category: str | None = None
    notes: str | None = None


class PortfolioRequest(BaseModel):
    holdings: list[HoldingInput]
    risk_profile: str | None = None
    goal: str | None = None
    base_currency: str = "TWD"


class HoldingMetrics(BaseModel):
    ticker: str
    name: str | None = None
    cost_basis: float | None = None
    current_value: float | None = None
    unrealized_gain_loss: float | None = None
    return_pct: float | None = None
    portfolio_weight_pct: float | None = None
    estimated_annual_dividend: float | None = None
    estimated_monthly_dividend: float | None = None
    current_price: float | None = None
    shares: float | None = None
    category: str | None = None
    asset_type: str | None = None
    sector: str | None = None
    theme: str | None = None
    market: str | None = None
    notes: str | None = None
    missing_data: list[str] = Field(default_factory=list)


class PortfolioAnalysisResponse(BaseModel):
    total_cost_basis: float | None
    total_current_value: float | None
    total_unrealized_gain_loss: float | None
    total_return_pct: float | None
    estimated_annual_dividend: float | None
    estimated_monthly_dividend: float | None
    overall_score: int = 0
    diversification_score: int = 0
    concentration_score: int = 0
    income_score: int = 0
    defensive_score: int = 0
    growth_score: int = 0
    holdings: list[HoldingMetrics]
    asset_type_exposure: dict[str, float] = Field(default_factory=dict)
    category_exposure: dict[str, float]
    sector_exposure: dict[str, float] = Field(default_factory=dict)
    theme_exposure: dict[str, float] = Field(default_factory=dict)
    market_exposure: dict[str, float] = Field(default_factory=dict)
    risk_flags: list[str]
    summary: str
    suggestions: list[str]
    news_to_monitor: dict[str, list[str]] = Field(default_factory=dict)
    missing_data: list[str] = Field(default_factory=list)


class ReallocationAction(BaseModel):
    action: Literal["sell", "buy", "hold_cash"]
    ticker: str
    shares: float | None = None
    percentage: float | None = None
    amount: float | None = None


class ScenarioRequest(BaseModel):
    portfolio: PortfolioRequest
    actions: list[ReallocationAction]
    target_ticker: str | None = None
    target_name: str | None = None
    user_question: str | None = None


class ScenarioResponse(BaseModel):
    before: PortfolioAnalysisResponse
    after: PortfolioAnalysisResponse
    dividend_change: float | None
    risk_change_summary: str
    recommendation: str
    caveats: list[str]


class NamedScenario(BaseModel):
    name: str
    actions: list[ReallocationAction]
    user_question: str | None = None


class ScenarioComparisonItem(BaseModel):
    name: str
    before_value: float | None
    after_value: float | None
    dividend_change: float | None
    technology_exposure_change: float | None
    defensive_allocation_change: float | None
    concentration_change: float | None
    risk_flags_added: list[str] = Field(default_factory=list)
    risk_flags_removed: list[str] = Field(default_factory=list)
    overall_score_change: int = 0
    recommendation_rank: int = 0
    recommendation: str


class ScenarioComparisonRequest(BaseModel):
    portfolio: PortfolioRequest
    scenarios: list[NamedScenario]


class ScenarioComparisonResponse(BaseModel):
    current: PortfolioAnalysisResponse
    scenarios: list[ScenarioComparisonItem]


class PortfolioSaveRequest(BaseModel):
    portfolio: PortfolioRequest
    name: str = "current"
    make_current: bool = True


class SavedPortfolioSummary(BaseModel):
    name: str
    updated_at: datetime
    holding_count: int
    base_currency: str
    risk_profile: str | None = None
    goal: str | None = None


class SavedPortfolioRecord(BaseModel):
    name: str
    updated_at: datetime
    portfolio: PortfolioRequest


class PortfolioAgentRequest(BaseModel):
    portfolio: PortfolioRequest | None = None
    user_question: str | None = None
    target_ticker_or_fund: str | None = None


class PortfolioAgentResponse(BaseModel):
    conclusion: str
    current_portfolio_diagnosis: str
    key_numbers: dict[str, Any]
    evidence_used: list[str]
    bull_case: str
    bear_case: str
    base_case: str
    suggested_next_actions: list[str]
    risks: list[str]
    missing_data: list[str]
