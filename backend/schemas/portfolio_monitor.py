from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .portfolio import PortfolioRequest


class PortfolioMonitorRequest(BaseModel):
    portfolio: PortfolioRequest | None = None
    workspace_id: str | None = None
    benchmark: str = "SPY"
    signal_horizon_days: int = 30
    max_news_articles: int = 3
    include_earnings: bool = True


class PortfolioHoldingMonitor(BaseModel):
    ticker: str
    name: str | None = None
    weight_pct: float | None = None
    return_pct: float | None = None
    signal_score: float | None = None
    signal_band: str | None = None
    signal_confidence: str | None = None
    news_sentiment: str | None = None
    next_earnings_date: str | None = None
    days_to_next_earnings: int | None = None
    watch_items: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class PortfolioMonitorResponse(BaseModel):
    generated_at: datetime
    workspace_id: str | None = None
    portfolio_summary: str
    risk_flags: list[str] = Field(default_factory=list)
    top_portfolio_alerts: list[str] = Field(default_factory=list)
    holdings: list[PortfolioHoldingMonitor] = Field(default_factory=list)
    safety_disclaimer: str
