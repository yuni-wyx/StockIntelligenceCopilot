from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SignalRequest(BaseModel):
    ticker: str
    benchmark: str = "SPY"
    horizon_days: int = 30


class SignalFeatureSnapshot(BaseModel):
    ticker_return_5d: float | None = None
    ticker_return_20d: float | None = None
    benchmark_return_20d: float | None = None
    relative_return_20d: float | None = None
    price_vs_sma20_pct: float | None = None
    sma20_vs_sma50_pct: float | None = None
    realized_volatility_20d: float | None = None
    drawdown_from_60d_high_pct: float | None = None
    volume_ratio_5d_20d: float | None = None


class SignalComponent(BaseModel):
    name: str
    contribution: float
    direction: Literal["positive", "negative", "neutral"]
    summary: str


class SignalResponse(BaseModel):
    ticker: str
    benchmark: str
    horizon_days: int
    signal_score: float = Field(ge=0, le=100)
    signal_band: Literal["Weak", "Neutral", "Strong"]
    confidence: Literal["Low", "Medium", "High"]
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    data_caveats: list[str] = Field(default_factory=list)
    disclaimer: str
    feature_snapshot: SignalFeatureSnapshot
    components: list[SignalComponent] = Field(default_factory=list)
