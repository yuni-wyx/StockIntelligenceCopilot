"""
Intent Classification Schema
-----------------------------
Input  : raw user query string
Output : structured intent with mode + extracted tickers
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class AnalysisMode(str, Enum):
    """All supported workflow modes."""

    STOCK_RESEARCH = "stock_research"
    PRICE_MOVEMENT = "price_movement"
    WATCHLIST_MONITOR = "watchlist_monitor"
    TRADE = "trade"


class IntentInput(BaseModel):
    """Raw input before classification."""

    raw_query: str = Field(
        ...,
        description="Original user query, e.g. 'research NVDA' or 'trade TSLA'.",
    )


class IntentOutput(BaseModel):
    """Structured intent emitted by the Intent Classification Chain."""

    mode: AnalysisMode = Field(
        ...,
        description="Detected analysis mode.",
    )
    tickers: List[str] = Field(
        ...,
        min_length=1,
        description="Uppercase ticker symbols extracted from the query.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier confidence in the detected mode (0–1).",
    )
    reasoning: str = Field(
        ...,
        description="Short rationale for the classification result.",
    )

    model_config = {"use_enum_values": True}