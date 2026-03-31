"""
Evidence Schema
----------------
Represents the aggregated outputs of all tool executions,
ready to be consumed by the Synthesis Chain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Individual tool result wrappers ─────────────────────────────────────────

class ToolResult(BaseModel):
    """Raw result from a single tool execution."""

    tool: str = Field(..., description="Tool name that produced this result.")
    ticker: str = Field(..., description="Ticker this result relates to.")
    success: bool = Field(..., description="Whether the tool executed without error.")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool payload (structure varies by tool).",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if success=False.",
    )


# ── Per-ticker evidence bundle ───────────────────────────────────────────────

class TickerEvidence(BaseModel):
    """All evidence collected for a single ticker."""

    ticker: str
    market_data: Optional[Dict[str, Any]] = None
    fundamentals: Optional[Dict[str, Any]] = None
    news: Optional[List[Dict[str, Any]]] = None
    earnings: Optional[Dict[str, Any]] = None
    tool_errors: List[str] = Field(
        default_factory=list,
        description="Any tool errors encountered during evidence collection.",
    )

    @property
    def has_market_data(self) -> bool:
        return self.market_data is not None

    @property
    def has_news(self) -> bool:
        return bool(self.news)

    @property
    def completeness_score(self) -> float:
        """Fraction of expected evidence slots that were filled (0–1)."""
        slots = [self.market_data, self.fundamentals, self.news, self.earnings]
        filled = sum(1 for s in slots if s is not None)
        return filled / len(slots)


# ── Aggregated evidence across all tickers ───────────────────────────────────

class AggregatedEvidence(BaseModel):
    """Full evidence bundle passed to the Synthesis Chain."""

    mode: str = Field(..., description="Analysis mode that generated this evidence.")
    tickers_evidence: Dict[str, TickerEvidence] = Field(
        ...,
        description="Map of ticker → TickerEvidence.",
    )
    total_tool_calls: int = Field(..., description="Total number of tool calls made.")
    successful_calls: int = Field(..., description="Number of successful tool calls.")

    @property
    def success_rate(self) -> float:
        if self.total_tool_calls == 0:
            return 0.0
        return self.successful_calls / self.total_tool_calls

    def get_ticker(self, ticker: str) -> Optional[TickerEvidence]:
        return self.tickers_evidence.get(ticker)
