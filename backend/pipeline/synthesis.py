from __future__ import annotations

from langsmith import traceable

try:
    from ..chains.synthesis_chain import SynthesisInput, build_synthesis_chain
    from ..schemas.agent import AgentEvidenceBundle, AgentPlan, AgentTaskType
except ImportError:
    from chains.synthesis_chain import SynthesisInput, build_synthesis_chain
    from schemas.agent import AgentEvidenceBundle, AgentPlan, AgentTaskType


@traceable(name="synthesis", run_type="chain", tags=["synthesis"])
def trace_synthesis(evidence, plan, runtime_signals=None):
    chain = build_synthesis_chain()
    return chain.invoke(
        SynthesisInput(
            evidence=evidence,
            plan=plan,
            runtime_signals=runtime_signals or {},
        )
    )


def synthesise_output(evidence, plan):
    return trace_synthesis(evidence, plan)


def synthesise_agent_output(bundle: AgentEvidenceBundle, plan: AgentPlan):
    if plan.task_type in {
        AgentTaskType.RESEARCH,
        AgentTaskType.EXPLAIN,
        AgentTaskType.TRADE,
        AgentTaskType.WATCHLIST,
    }:
        if bundle.legacy_evidence is None:
            raise ValueError("Legacy security synthesis requires aggregated evidence.")
        legacy_plan = plan.metadata.get("legacy_execution_plan")
        if not legacy_plan:
            raise ValueError("Legacy security synthesis requires execution plan metadata.")
        try:
            from ..schemas.planner_schema import ExecutionPlan
        except ImportError:
            from schemas.planner_schema import ExecutionPlan
        return trace_synthesis(
            bundle.legacy_evidence,
            ExecutionPlan(**legacy_plan),
            runtime_signals={
                **bundle.external_evidence.get("signals", {}),
                "__research_evidence": bundle.external_evidence.get("research_evidence"),
            },
        )

    if plan.task_type == AgentTaskType.PORTFOLIO_ANALYSIS:
        try:
            from ..schemas.portfolio import PortfolioAnalysisResponse
        except ImportError:
            from schemas.portfolio import PortfolioAnalysisResponse
        payload = bundle.derived_metrics.get("portfolio_analysis")
        if payload is None:
            raise ValueError("Portfolio analysis bundle is missing derived metrics.")
        return PortfolioAnalysisResponse(**payload)

    if plan.task_type == AgentTaskType.PORTFOLIO_SCENARIO:
        try:
            from ..schemas.portfolio import ScenarioResponse
        except ImportError:
            from schemas.portfolio import ScenarioResponse
        payload = bundle.derived_metrics.get("portfolio_scenario")
        if payload is None:
            raise ValueError("Portfolio scenario bundle is missing derived metrics.")
        return ScenarioResponse(**payload)

    if plan.task_type == AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE:
        try:
            from ..schemas.portfolio import ScenarioComparisonResponse
        except ImportError:
            from schemas.portfolio import ScenarioComparisonResponse
        payload = bundle.derived_metrics.get("portfolio_scenarios_compare")
        if payload is None:
            raise ValueError("Scenario comparison bundle is missing derived metrics.")
        return ScenarioComparisonResponse(**payload)

    if plan.task_type == AgentTaskType.PORTFOLIO_AGENT:
        try:
            from ..pipeline.portfolio_agent import synthesise_portfolio_agent_output
        except ImportError:
            from pipeline.portfolio_agent import synthesise_portfolio_agent_output
        return synthesise_portfolio_agent_output(bundle, plan)

    raise ValueError(f"Unsupported agent task type: {plan.task_type}")
