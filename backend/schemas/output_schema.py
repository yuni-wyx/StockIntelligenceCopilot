"""
Output Schema
--------------
Final structured outputs for each analysis mode.
These are the top-level objects returned to the caller / CLI.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

# ── Shared primitives ────────────────────────────────────────────────────────

class WatchPoint(BaseModel):
    """A single 'what to watch next' item."""

    item: str = Field(..., description="Short description of the thing to watch.")
    reason: str = Field(..., description="Why this matters.")
    timeframe: str = Field(..., description="Expected timeframe, e.g. '1–2 weeks'.")


class RankedCause(BaseModel):
    """A candidate cause for a price movement, scored and ranked."""

    rank: int = Field(..., ge=1, description="Rank order, 1 = highest confidence.")
    cause: str = Field(..., description="Short label for the cause.")
    explanation: str = Field(..., description="Detailed explanation.")
    supporting_evidence: List[str] = Field(
        ...,
        description="Bullet points of evidence supporting this cause.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence this cause explains the move (0–1).",
    )
    confidence_label: str = Field(
        ...,
        description="Human-readable label: HIGH / MEDIUM / LOW.",
    )


class TradingDecisionOutput(BaseModel):
    """Final output for Trading Decision Mode."""

    ticker: str = Field(..., description="Ticker symbol.")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the trading decision was generated.",
    )
    bias: str = Field(
        ...,
        description="Overall trading bias: Bullish / Neutral / Bearish.",
    )
    buy_zone: str = Field(
        ...,
        description="Suggested buy zone as a price or price range.",
    )
    stop_loss: str = Field(
        ...,
        description="Suggested stop loss as a price or price range.",
    )
    take_profit: str = Field(
        ...,
        description="Suggested take profit as a price or price range.",
    )
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score for the decision, from 0 to 100.",
    )
    reasoning: List[str] = Field(
        ...,
        description="Short bullet reasons supporting the decision.",
    )


# ── Mode 1: Stock Research ───────────────────────────────────────────────────

class StockResearchOutput(BaseModel):
    """Final output for Stock Research Mode."""

    ticker: str = Field(..., description="Ticker symbol.")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    fundamental_summary: str = Field(
        ...,
        description="Concise overview of the company's fundamentals.",
    )
    recent_news_summary: str = Field(
        ...,
        description="Summary of the most relevant recent headlines.",
    )
    bull_case: str = Field(
        ...,
        description="Bullish thesis with key supporting factors.",
    )
    bear_case: str = Field(
        ...,
        description="Bearish thesis with key risk factors.",
    )
    what_to_watch_next: List[WatchPoint] = Field(
        ...,
        description="Prioritised list of catalysts / events to monitor.",
    )
    overall_sentiment: str = Field(
        ...,
        description="One of: BULLISH / NEUTRAL / BEARISH.",
    )


# ── Mode 2: Price Movement Explanation ──────────────────────────────────────

class PriceMovementOutput(BaseModel):
    """Final output for Price Movement Explanation Mode."""

    ticker: str = Field(..., description="Ticker symbol.")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    price_move_summary: str = Field(
        ...,
        description="Plain-English summary of today's price action.",
    )
    price_change_pct: float = Field(
        ...,
        description="Percentage price change (positive = up).",
    )
    volume_context: str = Field(
        ...,
        description="Whether volume was above/below average and by how much.",
    )
    ranked_causes: List[RankedCause] = Field(
        ...,
        description="Candidate causes ranked by confidence, highest first.",
    )
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate explanation confidence (weighted average of top causes).",
    )
    what_to_watch_next: List[WatchPoint] = Field(
        ...,
        description="Follow-on items to monitor given today's move.",
    )


# ── Mode 3: Watchlist Monitoring ─────────────────────────────────────────────

class TickerWeeklySummary(BaseModel):
    """Per-ticker section within a watchlist report."""

    ticker: str = Field(..., description="Ticker symbol.")
    weekly_highlights: str = Field(..., description="Key developments this week.")
    major_news: List[str] = Field(..., description="Top news headlines.")
    earnings_events: str = Field(
        ...,
        description="Upcoming earnings date / recent results summary.",
    )
    risk_signals: List[str] = Field(
        ...,
        description="Identified risk signals to be aware of.",
    )
    next_week_watchpoints: List[WatchPoint] = Field(
        ...,
        description="Specific things to watch heading into next week.",
    )
    momentum: str = Field(
        ...,
        description="Short momentum label: STRONG_UP / UP / FLAT / DOWN / STRONG_DOWN.",
    )


class WatchlistMonitorOutput(BaseModel):
    """Final output for Watchlist Monitoring Mode."""

    tickers: List[str] = Field(..., description="List of ticker symbols in the watchlist.")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    portfolio_summary: str = Field(
        ...,
        description="Cross-ticker narrative for the week.",
    )
    ticker_summaries: List[TickerWeeklySummary] = Field(
        ...,
        description="Per-ticker breakdown.",
    )
    macro_risks: List[str] = Field(
        ...,
        description="Macro-level risks relevant across the watchlist.",
    )
    top_opportunities: List[str] = Field(
        ...,
        description="Highest-conviction opportunities across the watchlist.",
    )