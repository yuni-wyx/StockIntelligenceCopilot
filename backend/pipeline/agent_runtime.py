from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Generator

try:
    from ..pipeline.planning import classify_and_plan
    from ..pipeline.retrieval import retrieve_evidence
    from ..pipeline.synthesis import synthesise_agent_output
    from ..schemas.agent import (
        AgentEvidenceBundle,
        AgentPlan,
        AgentResult,
        AgentStep,
        AgentStreamEvent,
        AgentTask,
        AgentTaskType,
        AgentToolCall,
    )
    from ..schemas.planner_schema import ExecutionPlan, ToolCallSpec
    from ..schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioRequest,
        ScenarioComparisonRequest,
        ScenarioRequest,
    )
    from ..services.evidence_provenance import build_claim_evidence, extract_source_metadata
    from ..services.portfolio_store import PortfolioStore
    from .portfolio_orchestrator import (
        _compare_portfolio_scenarios_impl,
        _run_portfolio_scenario_impl,
        analyze_portfolio_with_evidence,
    )
except ImportError:
    from pipeline.planning import classify_and_plan
    from pipeline.portfolio_orchestrator import (
        _compare_portfolio_scenarios_impl,
        _run_portfolio_scenario_impl,
        analyze_portfolio_with_evidence,
    )
    from pipeline.retrieval import retrieve_evidence
    from pipeline.synthesis import synthesise_agent_output
    from schemas.agent import (
        AgentEvidenceBundle,
        AgentPlan,
        AgentResult,
        AgentStep,
        AgentStreamEvent,
        AgentTask,
        AgentTaskType,
        AgentToolCall,
    )
    from schemas.planner_schema import ExecutionPlan, ToolCallSpec
    from schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioRequest,
        ScenarioComparisonRequest,
        ScenarioRequest,
    )
    from services.evidence_provenance import build_claim_evidence, extract_source_metadata
    from services.portfolio_store import PortfolioStore


def _output_type_name(output: Any) -> str:
    return getattr(type(output), "__name__", "object")


def _event_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attach_evidence_audit(
    bundle: AgentEvidenceBundle,
    payload: dict[str, Any],
) -> dict[str, Any]:
    source_metadata = extract_source_metadata(bundle)
    claim_evidence, unsupported_claims, confidence_score = build_claim_evidence(
        payload,
        source_metadata,
    )
    bundle.source_metadata = source_metadata
    bundle.claim_evidence = claim_evidence
    bundle.unsupported_claims = unsupported_claims
    bundle.confidence_score = confidence_score
    return {
        **payload,
        "evidence_provenance": [
            source.model_dump(mode="json") for source in source_metadata
        ],
        "claim_evidence": [claim.model_dump(mode="json") for claim in claim_evidence],
        "unsupported_claims": [
            claim.model_dump(mode="json") for claim in unsupported_claims
        ],
        "confidence_score": confidence_score,
    }


def _timeline_event(
    step: str,
    title: str,
    status: str,
    summary: str,
    started_at: float,
    metadata: dict[str, Any] | None = None,
) -> AgentStreamEvent:
    return AgentStreamEvent(
        type="timeline_step",
        step=step,
        title=title,
        status=status,
        summary=summary,
        timestamp=_event_time(),
        latency_ms=round((time.perf_counter() - started_at) * 1000, 1),
        metadata=metadata or {},
    )


def _build_raw_query(task: AgentTask) -> str:
    if task.raw_query:
        return task.raw_query

    prefixes = {
        AgentTaskType.RESEARCH: "research",
        AgentTaskType.EXPLAIN: "explain",
        AgentTaskType.TRADE: "trade",
        AgentTaskType.WATCHLIST: "watchlist",
    }
    prefix = prefixes.get(task.task_type)
    if prefix is None:
        raise ValueError(f"Task type {task.task_type} does not map to a raw query.")
    if not task.tickers:
        raise ValueError(f"Task type {task.task_type} requires at least one ticker.")
    return f"{prefix} {' '.join(task.tickers)}"


def _adapt_tool_call(call: ToolCallSpec) -> AgentToolCall:
    return AgentToolCall(
        name=str(call.tool),
        target=call.ticker,
        params=call.params,
        priority=call.priority,
        rationale=call.rationale,
        output_key=f"{call.tool}:{call.ticker}",
    )


def build_agent_plan_from_execution_plan(
    task: AgentTask,
    plan: ExecutionPlan,
) -> AgentPlan:
    tool_calls = [_adapt_tool_call(call) for call in plan.tool_calls]
    steps = [
        AgentStep(
            name="planner",
            summary=plan.analysis_focus,
            tool_calls=tool_calls,
        )
    ]
    return AgentPlan(
        task_type=task.task_type,
        summary=plan.analysis_focus,
        steps=steps,
        tool_calls=tool_calls,
        expected_outputs=plan.expected_outputs,
        metadata={
            "tickers": plan.tickers,
            "mode": plan.mode,
            "legacy_execution_plan": (
                plan.model_dump(mode="json")
                if hasattr(plan, "model_dump")
                else {}
            ),
        },
    )


def build_agent_evidence_from_aggregated_evidence(
    task: AgentTask,
    plan: AgentPlan,
    *,
    raw_query: str,
    tool_results: list[Any],
    aggregated_evidence: Any,
) -> AgentEvidenceBundle:
    serialized_results = [
        result.model_copy() if hasattr(result, "model_copy") else result
        for result in tool_results
    ]
    return AgentEvidenceBundle(
        context={
            "raw_query": raw_query,
            "tickers": task.tickers or plan.metadata.get("tickers", []),
            "task_type": task.task_type,
        },
        derived_metrics={
            "analysis_focus": plan.summary,
            "expected_outputs": plan.expected_outputs,
        },
        external_evidence={
            "tickers_evidence": (
                aggregated_evidence.model_dump(mode="json")
                if hasattr(aggregated_evidence, "model_dump")
                else {}
            ),
        },
        tool_results=serialized_results,
        legacy_evidence=aggregated_evidence,
        metadata={
            "success_rate": getattr(aggregated_evidence, "success_rate", None),
        },
    )


def derive_portfolio_targets(analysis: Any, target: str | None = None) -> dict[str, Any]:
    top_holdings = sorted(
        getattr(analysis, "holdings", []),
        key=lambda item: item.portfolio_weight_pct or 0,
        reverse=True,
    )[:3]
    largest_losers = sorted(
        [holding for holding in getattr(analysis, "holdings", []) if (holding.return_pct or 0) < 0],
        key=lambda item: item.return_pct or 0,
    )[:3]
    concentrated_themes = {
        theme: pct
        for theme, pct in getattr(analysis, "theme_exposure", {}).items()
        if pct >= 25
    }
    return {
        "top_holdings": [holding.ticker for holding in top_holdings],
        "largest_losers": [holding.ticker for holding in largest_losers],
        "concentrated_themes": concentrated_themes,
        "target_ticker_or_fund": target,
    }


def build_portfolio_agent_plan(task: AgentTask) -> AgentPlan:
    portfolio_name = task.portfolio_name or "current"
    has_inline_portfolio = task.portfolio is not None
    base_tool_calls = []
    if not has_inline_portfolio:
        base_tool_calls.append(
            AgentToolCall(
                name="load_portfolio",
                target=portfolio_name,
                rationale="Load the saved portfolio before analysis.",
                output_key="portfolio",
            )
        )

    per_holding_calls: list[AgentToolCall] = []
    holdings = task.portfolio.holdings if task.portfolio else []
    for index, holding in enumerate(holdings, start=1):
        per_holding_calls.extend(
            [
                AgentToolCall(
                    name="market_data",
                    target=holding.ticker,
                    priority=index,
                    rationale="Refresh market pricing for the holding.",
                    output_key=f"market_data:{holding.ticker}",
                ),
                AgentToolCall(
                    name="fundamentals",
                    target=holding.ticker,
                    priority=index,
                    rationale="Collect company or fund context for the holding.",
                    output_key=f"fundamentals:{holding.ticker}",
                ),
                AgentToolCall(
                    name="news",
                    target=holding.ticker,
                    priority=index,
                    rationale="Collect recent headlines for the holding.",
                    output_key=f"news:{holding.ticker}",
                ),
            ]
        )

    if task.target_ticker_or_fund:
        per_holding_calls.extend(
            [
                AgentToolCall(
                    name="market_data",
                    target=task.target_ticker_or_fund,
                    rationale="Collect target security price context for the scenario question.",
                    output_key=f"market_data:{task.target_ticker_or_fund}",
                ),
                AgentToolCall(
                    name="fundamentals",
                    target=task.target_ticker_or_fund,
                    rationale="Collect target security profile for the scenario question.",
                    output_key=f"fundamentals:{task.target_ticker_or_fund}",
                ),
                AgentToolCall(
                    name="news",
                    target=task.target_ticker_or_fund,
                    rationale="Collect target security headlines for the scenario question.",
                    output_key=f"news:{task.target_ticker_or_fund}",
                ),
            ]
        )

    derived_calls = [
        AgentToolCall(
            name="calculate_portfolio_metrics",
            rationale="Compute deterministic portfolio health, returns, and exposures.",
            output_key="portfolio_analysis",
        ),
        AgentToolCall(
            name="derive_portfolio_targets",
            rationale="Identify the holdings and themes that deserve extra attention.",
            output_key="portfolio_targets",
        ),
    ]

    task_specific_calls: list[AgentToolCall] = []
    if task.task_type == AgentTaskType.PORTFOLIO_SCENARIO:
        task_specific_calls.append(
            AgentToolCall(
                name="compare_portfolio_scenarios",
                rationale="Calculate before-vs-after scenario effects.",
                output_key="portfolio_scenario",
            )
        )
    elif task.task_type == AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE:
        task_specific_calls.append(
            AgentToolCall(
                name="compare_portfolio_scenarios",
                rationale="Rank multiple reallocation scenarios with deterministic metrics.",
                output_key="portfolio_scenarios_compare",
            )
        )

    tool_calls = [*base_tool_calls, *per_holding_calls, *derived_calls, *task_specific_calls]
    steps = [
        AgentStep(
            name="portfolio_context",
            summary="Load or accept the portfolio context for the task.",
            tool_calls=base_tool_calls,
        ),
        AgentStep(
            name="portfolio_research",
            summary="Refresh portfolio evidence from market, fundamentals, and news tools.",
            tool_calls=per_holding_calls,
        ),
        AgentStep(
            name="portfolio_metrics",
            summary="Compute deterministic portfolio metrics and scenario deltas.",
            tool_calls=[*derived_calls, *task_specific_calls],
        ),
    ]
    expected_outputs = {
        AgentTaskType.PORTFOLIO_ANALYSIS: ["portfolio_analysis"],
        AgentTaskType.PORTFOLIO_SCENARIO: ["portfolio_scenario"],
        AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE: ["portfolio_scenarios_compare"],
        AgentTaskType.PORTFOLIO_AGENT: ["portfolio_agent_recommendation"],
    }[task.task_type]
    return AgentPlan(
        task_type=task.task_type,
        summary="Unified portfolio agent plan",
        steps=steps,
        tool_calls=tool_calls,
        expected_outputs=expected_outputs,
        metadata={
            "portfolio_name": portfolio_name,
            "user_question": task.user_question,
            "target_ticker_or_fund": task.target_ticker_or_fund,
        },
    )


def build_portfolio_evidence_bundle(
    task: AgentTask,
    plan: AgentPlan,
    *,
    portfolio: PortfolioRequest,
    analysis: Any,
    enrichment: dict[str, dict[str, Any]],
    scenario_output: Any | None = None,
    comparison_output: Any | None = None,
) -> AgentEvidenceBundle:
    targets = derive_portfolio_targets(analysis, task.target_ticker_or_fund)
    return AgentEvidenceBundle(
        context={
            "portfolio": portfolio.model_dump(mode="json"),
            "user_question": task.user_question,
            "target_ticker_or_fund": task.target_ticker_or_fund,
            "task_type": task.task_type,
        },
        derived_metrics={
            "portfolio_analysis": analysis.model_dump(mode="json"),
            "portfolio_targets": targets,
            "portfolio_scenario": (
                scenario_output.model_dump(mode="json")
                if scenario_output is not None and hasattr(scenario_output, "model_dump")
                else None
            ),
            "portfolio_scenarios_compare": (
                comparison_output.model_dump(mode="json")
                if comparison_output is not None and hasattr(comparison_output, "model_dump")
                else None
            ),
        },
        external_evidence={
            "holdings": enrichment,
            "market_data": {
                ticker: payload.get("market_data", {})
                for ticker, payload in enrichment.items()
                if payload.get("market_data") is not None
            },
            "fundamentals": {
                ticker: payload.get("fundamentals", {})
                for ticker, payload in enrichment.items()
                if payload.get("fundamentals") is not None
            },
            "news": {
                ticker: payload.get("news_articles", [])
                for ticker, payload in enrichment.items()
                if payload.get("news_articles")
            },
        },
        metadata={
            "expected_outputs": plan.expected_outputs,
        },
    )


def execute_agent_task(
    task: AgentTask,
    *,
    store: PortfolioStore | None = None,
) -> AgentResult:
    if task.task_type in {
        AgentTaskType.RESEARCH,
        AgentTaskType.EXPLAIN,
        AgentTaskType.TRADE,
        AgentTaskType.WATCHLIST,
    }:
        raw_query = _build_raw_query(task)
        _, legacy_plan = classify_and_plan(raw_query)
        tool_results, aggregated_evidence = retrieve_evidence(legacy_plan)
        plan = build_agent_plan_from_execution_plan(task, legacy_plan)
        bundle = build_agent_evidence_from_aggregated_evidence(
            task,
            plan,
            raw_query=raw_query,
            tool_results=tool_results,
            aggregated_evidence=aggregated_evidence,
        )
        output = synthesise_agent_output(bundle, plan)
        return AgentResult(
            task=task,
            plan=plan,
            evidence=bundle,
            output=output,
            output_type=_output_type_name(output),
        )

    store = store or PortfolioStore()
    plan = build_portfolio_agent_plan(task)

    portfolio = task.portfolio
    if portfolio is None:
        record = store.load_portfolio(task.portfolio_name or "current")
        if record is None:
            raise ValueError("No current portfolio is saved.")
        portfolio = record.portfolio

    analysis, enrichment = analyze_portfolio_with_evidence(portfolio)
    scenario_output = None
    comparison_output = None

    if task.task_type == AgentTaskType.PORTFOLIO_SCENARIO:
        scenario_output = _run_portfolio_scenario_impl(
            ScenarioRequest(
                portfolio=portfolio,
                actions=task.actions,
                target_name=task.metadata.get("target_name"),
                target_ticker=task.metadata.get("target_ticker"),
                user_question=task.user_question,
            )
        )
    elif task.task_type == AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE:
        comparison_output = _compare_portfolio_scenarios_impl(
            ScenarioComparisonRequest(
                portfolio=portfolio,
                scenarios=task.scenarios,
            )
        )

    bundle = build_portfolio_evidence_bundle(
        task,
        plan,
        portfolio=portfolio,
        analysis=analysis,
        enrichment=enrichment,
        scenario_output=scenario_output,
        comparison_output=comparison_output,
    )
    output = synthesise_agent_output(bundle, plan)
    return AgentResult(
        task=task,
        plan=plan,
        evidence=bundle,
        output=output,
        output_type=_output_type_name(output),
    )


def stream_agent_task(
    task: AgentTask,
    *,
    store: PortfolioStore | None = None,
) -> Generator[AgentStreamEvent, None, None]:
    if task.task_type not in {
        AgentTaskType.RESEARCH,
        AgentTaskType.EXPLAIN,
        AgentTaskType.TRADE,
    }:
        raise ValueError(
            "Runtime streaming adapter currently supports research, explain, and trade only."
        )

    try:
        from ..api.presentation import partial_output_snapshot, serialize_output
        from .planning import plan_from_intent, trace_intent
        from .retrieval import trace_aggregate, trace_tool_routing
    except ImportError:
        from api.presentation import partial_output_snapshot, serialize_output
        from pipeline.planning import plan_from_intent, trace_intent
        from pipeline.retrieval import trace_aggregate, trace_tool_routing

    t0 = time.perf_counter()
    raw_query = _build_raw_query(task)
    yield AgentStreamEvent(
        type="status",
        message="Starting pipeline",
        data={"raw_query": raw_query},
    )

    step_started = time.perf_counter()
    yield _timeline_event(
        step="query_interpretation",
        title="Query Interpretation",
        status="in_progress",
        summary="Interpreting the user query and detecting symbols.",
        started_at=step_started,
    )
    intent = trace_intent(raw_query)
    intent_data = intent.model_dump(mode="json") if hasattr(intent, "model_dump") else {}
    yield _timeline_event(
        step="query_interpretation",
        title="Query Interpretation",
        status="completed",
        summary=f"Detected {intent.mode} for {', '.join(intent.tickers)}.",
        started_at=step_started,
        metadata={
            "mode": intent_data.get("mode", getattr(intent, "mode", "")),
            "tickers": intent_data.get("tickers", getattr(intent, "tickers", [])),
            "confidence": intent_data.get(
                "confidence",
                getattr(intent, "confidence", None),
            ),
        },
    )
    yield AgentStreamEvent(
        type="stage_done",
        stage="intent",
        message="Intent classified",
        data=intent_data if intent_data else str(intent),
    )

    step_started = time.perf_counter()
    yield _timeline_event(
        step="planning",
        title="Planning",
        status="in_progress",
        summary="Selecting the evidence sources needed for this request.",
        started_at=step_started,
    )
    legacy_plan = plan_from_intent(intent)
    plan = build_agent_plan_from_execution_plan(task, legacy_plan)
    plan_data = legacy_plan.model_dump(mode="json") if hasattr(legacy_plan, "model_dump") else {}
    yield _timeline_event(
        step="planning",
        title="Planning",
        status="completed",
        summary=(
            f"Prepared {len(legacy_plan.tool_calls)} tool calls across "
            f"{len(legacy_plan.tickers)} ticker(s)."
        ),
        started_at=step_started,
        metadata={
            "analysis_focus": plan_data.get(
                "analysis_focus",
                getattr(legacy_plan, "analysis_focus", ""),
            ),
            "tool_count": len(legacy_plan.tool_calls),
            "tools": [str(call.tool) for call in legacy_plan.tool_calls],
        },
    )
    yield AgentStreamEvent(
        type="stage_done",
        stage="planning",
        message="Plan created",
        data=plan_data if plan_data else str(legacy_plan),
    )
    partial = partial_output_snapshot(raw_query, "planning", plan=legacy_plan)
    if partial is not None:
        yield AgentStreamEvent(
            type="partial_output",
            stage="planning",
            message="Initial analysis plan is ready",
            data=partial,
        )

    step_started = time.perf_counter()
    yield _timeline_event(
        step="evidence_retrieval",
        title="Evidence Retrieval",
        status="in_progress",
        summary="Collecting market data, company context, and recent catalysts.",
        started_at=step_started,
    )
    tool_results = trace_tool_routing(legacy_plan)
    for result in tool_results:
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else str(result)
        yield AgentStreamEvent(
            type="tool_result",
            stage="tools",
            message=f"{getattr(result, 'tool', 'unknown')} completed",
            data=payload,
            metadata={
                "tool": getattr(result, "tool", "unknown"),
                "ticker": getattr(result, "ticker", "unknown"),
                "success": getattr(result, "success", False),
            },
        )
    yield AgentStreamEvent(
        type="stage_done",
        stage="tools",
        message="Tool execution complete",
        data=[
            result.model_dump(mode="json") if hasattr(result, "model_dump") else str(result)
            for result in tool_results
        ],
    )
    partial = partial_output_snapshot(raw_query, "tools", tool_results=tool_results)
    if partial is not None:
        yield AgentStreamEvent(
            type="partial_output",
            stage="tools",
            message="Evidence collection is underway",
            data=partial,
        )

    aggregated_evidence = trace_aggregate(tool_results, legacy_plan)
    successful = sum(1 for result in tool_results if getattr(result, "success", False))
    failed = len(tool_results) - successful
    yield _timeline_event(
        step="evidence_retrieval",
        title="Evidence Retrieval",
        status="completed",
        summary=(
            f"Retrieved {successful} successful evidence set(s)"
            f"{f' with {failed} issue(s)' if failed else ''}."
        ),
        started_at=step_started,
        metadata={
            "successful_calls": successful,
            "failed_calls": failed,
            "tickers": getattr(legacy_plan, "tickers", []),
        },
    )

    step_started = time.perf_counter()
    yield _timeline_event(
        step="synthesis",
        title="Synthesis",
        status="in_progress",
        summary="Combining the retrieved evidence into a concise answer.",
        started_at=step_started,
    )
    yield AgentStreamEvent(
        type="stage_done",
        stage="aggregation",
        message="Evidence aggregated",
        data=(
            aggregated_evidence.model_dump(mode="json")
            if hasattr(aggregated_evidence, "model_dump")
            else str(aggregated_evidence)
        ),
    )
    partial = partial_output_snapshot(
        raw_query,
        "aggregation",
        evidence=aggregated_evidence,
    )
    if partial is not None:
        yield AgentStreamEvent(
            type="partial_output",
            stage="aggregation",
            message="Draft analysis is available",
            data=partial,
        )

    bundle = build_agent_evidence_from_aggregated_evidence(
        task,
        plan,
        raw_query=raw_query,
        tool_results=tool_results,
        aggregated_evidence=aggregated_evidence,
    )
    output = synthesise_agent_output(bundle, plan)
    serialized_output = _attach_evidence_audit(bundle, serialize_output(output))
    yield _timeline_event(
        step="synthesis",
        title="Synthesis",
        status="completed",
        summary="Generated the structured analysis from the evidence bundle.",
        started_at=step_started,
        metadata={"output_fields": sorted(serialized_output.keys())},
    )
    yield AgentStreamEvent(
        type="stage_done",
        stage="synthesis",
        message="Report generated",
        data=serialized_output,
    )

    elapsed = time.perf_counter() - t0
    final_step_started = time.perf_counter()
    yield _timeline_event(
        step="final_answer",
        title="Final Answer",
        status="completed",
        summary="Delivered the final answer to the client.",
        started_at=final_step_started,
        metadata={
            "ticker": serialized_output.get("ticker"),
            "tickers": serialized_output.get("tickers"),
            "elapsed_seconds": round(elapsed, 2),
        },
    )
    yield AgentStreamEvent(
        type="final_output",
        elapsed=round(elapsed, 2),
        data=serialized_output,
    )


def execute_portfolio_analysis(
    portfolio: PortfolioRequest,
    *,
    user_question: str | None = None,
) -> Any:
    result = execute_agent_task(
        AgentTask(
            task_type=AgentTaskType.PORTFOLIO_ANALYSIS,
            portfolio=portfolio,
            user_question=user_question,
        )
    )
    return result.output


def execute_portfolio_scenario(request: ScenarioRequest) -> Any:
    result = execute_agent_task(
        AgentTask(
            task_type=AgentTaskType.PORTFOLIO_SCENARIO,
            portfolio=request.portfolio,
            actions=request.actions,
            user_question=request.user_question,
            metadata={
                "target_name": request.target_name,
                "target_ticker": request.target_ticker,
            },
        )
    )
    return result.output


def execute_portfolio_scenarios_compare(request: ScenarioComparisonRequest) -> Any:
    result = execute_agent_task(
        AgentTask(
            task_type=AgentTaskType.PORTFOLIO_SCENARIOS_COMPARE,
            portfolio=request.portfolio,
            scenarios=request.scenarios,
        )
    )
    return result.output


def execute_portfolio_agent_request(
    request: PortfolioAgentRequest,
    *,
    store: PortfolioStore | None = None,
) -> Any:
    result = execute_agent_task(
        AgentTask(
            task_type=AgentTaskType.PORTFOLIO_AGENT,
            portfolio=request.portfolio,
            user_question=request.user_question,
            target_ticker_or_fund=request.target_ticker_or_fund,
        ),
        store=store,
    )
    return result.output
