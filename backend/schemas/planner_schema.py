"""
Planning Chain Schema
----------------------
Input  : IntentOutput
Output : ExecutionPlan — an ordered list of tool calls per ticker
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

try:
    from .intent_schema import AnalysisMode
except ImportError:
    from schemas.intent_schema import AnalysisMode


class ToolName(str, Enum):
    """All available tools in the system."""

    MARKET_DATA = "market_data"
    FUNDAMENTALS = "fundamentals"
    NEWS = "news"
    EARNINGS = "earnings"


class ToolCallSpec(BaseModel):
    """A single planned tool invocation."""

    tool: ToolName = Field(..., description="Which tool to invoke.")
    ticker: str = Field(..., description="Target ticker symbol.")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters forwarded to the tool.",
    )
    priority: int = Field(
        ...,
        ge=1,
        description="Execution priority (1 = highest). Lower values run first.",
    )
    rationale: str = Field(
        ...,
        description="Why this tool call is needed for the plan.",
    )

    model_config = {"use_enum_values": True}


class ExecutionPlan(BaseModel):
    """Full execution plan produced by the Planning Chain."""

    mode: AnalysisMode = Field(..., description="The analysis mode being executed.")
    tickers: List[str] = Field(..., description="All tickers in scope.")
    tool_calls: List[ToolCallSpec] = Field(
        ...,
        description="Ordered list of tool calls to execute.",
    )
    analysis_focus: str = Field(
        ...,
        description="High-level description of what this plan aims to produce.",
    )
    expected_outputs: List[str] = Field(
        ...,
        description="List of output sections the synthesis chain should produce.",
    )

    model_config = {"use_enum_values": True}

    def calls_for_ticker(self, ticker: str) -> List[ToolCallSpec]:
        """Return all tool calls scoped to a specific ticker, sorted by priority."""
        return sorted(
            [c for c in self.tool_calls if c.ticker == ticker],
            key=lambda c: c.priority,
        )

    def calls_for_tool(self, tool: ToolName) -> List[ToolCallSpec]:
        """Return all calls targeting a specific tool."""
        return [c for c in self.tool_calls if c.tool == tool]
