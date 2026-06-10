from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HoldingContribution(BaseModel):
    ticker: str
    name: str | None = None
    weight_pct: float | None = None
    current_value: float | None = None
    unrealized_gain_loss: float | None = None
    return_pct: float | None = None
    contribution_value: float | None = None
    contribution_pct: float | None = None
    explanation: str | None = None


class ConcentrationSnapshot(BaseModel):
    top_holding_weight_pct: float | None = None
    top_3_weight_pct: float | None = None
    top_5_weight_pct: float | None = None
    top_tickers: list[HoldingContribution] = Field(default_factory=list)
    theme_exposure_pct: dict[str, float] = Field(default_factory=dict)
    sector_exposure_pct: dict[str, float] = Field(default_factory=dict)
    market_exposure_pct: dict[str, float] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)


class IncomeQualitySnapshot(BaseModel):
    estimated_annual_dividend: float | None = None
    estimated_monthly_dividend: float | None = None
    top_dividend_contributors: list[HoldingContribution] = Field(default_factory=list)
    dividend_concentration_pct: float | None = None
    holdings_missing_dividend_data: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class RiskAttributionSnapshot(BaseModel):
    top_downside_weighted_holdings: list[HoldingContribution] = Field(default_factory=list)
    top_unrealized_losers: list[HoldingContribution] = Field(default_factory=list)
    top_unrealized_winners: list[HoldingContribution] = Field(default_factory=list)
    top_stress_test_contributors: list[HoldingContribution] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    title: str
    reason: str
    evidence_keys: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"] = "medium"


class PortfolioIntelligenceSnapshot(BaseModel):
    risk_attribution: RiskAttributionSnapshot = Field(
        default_factory=RiskAttributionSnapshot
    )
    concentration: ConcentrationSnapshot = Field(default_factory=ConcentrationSnapshot)
    income_quality: IncomeQualitySnapshot = Field(default_factory=IncomeQualitySnapshot)
    suggested_review_items: list[ReviewItem] = Field(default_factory=list)
