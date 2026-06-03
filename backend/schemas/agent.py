from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

try:
    from .evidence_schema import (
        AggregatedEvidence,
        ClaimEvidence,
        SourceMetadata,
        ToolResult,
        UnsupportedClaim,
    )
    from .portfolio import (
        NamedScenario,
        PortfolioRequest,
        ReallocationAction,
    )
except ImportError:
    from schemas.evidence_schema import (
        AggregatedEvidence,
        ClaimEvidence,
        SourceMetadata,
        ToolResult,
        UnsupportedClaim,
    )
    from schemas.portfolio import NamedScenario, PortfolioRequest, ReallocationAction


class AgentTaskType(str, Enum):
    RESEARCH = "research"
    EXPLAIN = "explain"
    TRADE = "trade"
    WATCHLIST = "watchlist"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    PORTFOLIO_SCENARIO = "portfolio_scenario"
    PORTFOLIO_SCENARIOS_COMPARE = "portfolio_scenarios_compare"
    PORTFOLIO_AGENT = "portfolio_agent"


class AgentTask(BaseModel):
    task_type: AgentTaskType
    raw_query: str | None = None
    tickers: list[str] = Field(default_factory=list)
    portfolio: PortfolioRequest | None = None
    actions: list[ReallocationAction] = Field(default_factory=list)
    scenarios: list[NamedScenario] = Field(default_factory=list)
    portfolio_name: str | None = None
    user_question: str | None = None
    target_ticker_or_fund: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentToolCall(BaseModel):
    name: str
    target: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1)
    rationale: str
    output_key: str | None = None


class AgentStep(BaseModel):
    name: str
    summary: str
    tool_calls: list[AgentToolCall] = Field(default_factory=list)


class AgentPlan(BaseModel):
    task_type: AgentTaskType
    summary: str
    steps: list[AgentStep] = Field(default_factory=list)
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentEvidenceBundle(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    derived_metrics: dict[str, Any] = Field(default_factory=dict)
    external_evidence: dict[str, Any] = Field(default_factory=dict)
    tool_results: list[ToolResult] = Field(default_factory=list)
    legacy_evidence: AggregatedEvidence | None = None
    source_metadata: list[SourceMetadata] = Field(default_factory=list)
    claim_evidence: list[ClaimEvidence] = Field(default_factory=list)
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task: AgentTask
    plan: AgentPlan
    evidence: AgentEvidenceBundle
    output: Any
    output_type: str


class AgentStreamEvent(BaseModel):
    type: str
    message: str | None = None
    stage: str | None = None
    data: Any | None = None
    elapsed: float | None = None
    step: str | None = None
    title: str | None = None
    status: str | None = None
    summary: str | None = None
    timestamp: str | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
