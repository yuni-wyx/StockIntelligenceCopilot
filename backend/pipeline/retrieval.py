from __future__ import annotations

from langsmith import traceable

try:
    from ..services.evidence_aggregator import EvidenceAggregator
    from ..services.tool_router import ToolRouter
except ImportError:
    from services.evidence_aggregator import EvidenceAggregator
    from services.tool_router import ToolRouter


@traceable(name="tool_routing", run_type="tool", tags=["tools"])
def trace_tool_routing(plan):
    router = ToolRouter()
    return router.execute(plan)


@traceable(name="evidence_aggregation", run_type="chain", tags=["evidence"])
def trace_aggregate(tool_results, plan):
    aggregator = EvidenceAggregator()
    return aggregator.aggregate(tool_results, plan)


def retrieve_evidence(plan):
    tool_results = trace_tool_routing(plan)
    evidence = trace_aggregate(tool_results, plan)
    return tool_results, evidence
