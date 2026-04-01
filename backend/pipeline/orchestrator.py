from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Generator

try:
    from ..api.presentation import partial_output_snapshot, serialize_output
    from .planning import classify_and_plan, plan_from_intent, trace_intent
    from .retrieval import retrieve_evidence, trace_aggregate, trace_tool_routing
    from .synthesis import synthesise_output, trace_synthesis
except ImportError:
    from api.presentation import partial_output_snapshot, serialize_output
    from pipeline.planning import classify_and_plan, plan_from_intent, trace_intent
    from pipeline.retrieval import retrieve_evidence, trace_aggregate, trace_tool_routing
    from pipeline.synthesis import synthesise_output, trace_synthesis

logger = logging.getLogger(__name__)


def execute_pipeline(raw_query: str) -> Any:
    _, plan = classify_and_plan(raw_query)
    _, evidence = retrieve_evidence(plan)
    return synthesise_output(evidence, plan)


def _event_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timeline_event(
    step: str,
    title: str,
    status: str,
    summary: str,
    started_at: float,
    metadata: dict | None = None,
) -> dict:
    return {
        "type": "timeline_step",
        "step": step,
        "title": title,
        "status": status,
        "summary": summary,
        "timestamp": _event_time(),
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 1),
        "metadata": metadata or {},
    }


def stream_pipeline_events(raw_query: str) -> Generator[dict, None, None]:
    t0 = time.perf_counter()
    yield {"type": "status", "message": "Starting pipeline", "raw_query": raw_query}

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
            "confidence": intent_data.get("confidence", getattr(intent, "confidence", None)),
        },
    )
    yield {
        "type": "stage_done",
        "stage": "intent",
        "message": "Intent classified",
        "data": intent_data if intent_data else str(intent),
    }

    step_started = time.perf_counter()
    yield _timeline_event(
        step="planning",
        title="Planning",
        status="in_progress",
        summary="Selecting the evidence sources needed for this request.",
        started_at=step_started,
    )
    plan = plan_from_intent(intent)
    plan_data = plan.model_dump(mode="json") if hasattr(plan, "model_dump") else {}
    yield _timeline_event(
        step="planning",
        title="Planning",
        status="completed",
        summary=f"Prepared {len(plan.tool_calls)} tool calls across {len(plan.tickers)} ticker(s).",
        started_at=step_started,
        metadata={
            "analysis_focus": plan_data.get("analysis_focus", getattr(plan, "analysis_focus", "")),
            "tool_count": len(plan.tool_calls),
            "tools": [str(call.tool) for call in plan.tool_calls],
        },
    )
    yield {
        "type": "stage_done",
        "stage": "planning",
        "message": "Plan created",
        "data": plan_data if plan_data else str(plan),
    }
    partial = partial_output_snapshot(raw_query, "planning", plan=plan)
    if partial is not None:
        yield {
            "type": "partial_output",
            "stage": "planning",
            "message": "Initial analysis plan is ready",
            "data": partial,
        }

    step_started = time.perf_counter()
    yield _timeline_event(
        step="evidence_retrieval",
        title="Evidence Retrieval",
        status="in_progress",
        summary="Collecting market data, company context, and recent catalysts.",
        started_at=step_started,
    )
    tool_results = trace_tool_routing(plan)

    for result in tool_results:
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else str(result)
        yield {
            "type": "tool_result",
            "stage": "tools",
            "tool": getattr(result, "tool", "unknown"),
            "ticker": getattr(result, "ticker", "unknown"),
            "success": getattr(result, "success", False),
            "data": payload,
        }

    yield {
        "type": "stage_done",
        "stage": "tools",
        "message": "Tool execution complete",
        "data": [
            r.model_dump(mode="json") if hasattr(r, "model_dump") else str(r)
            for r in tool_results
        ],
    }
    partial = partial_output_snapshot(raw_query, "tools", tool_results=tool_results)
    if partial is not None:
        yield {
            "type": "partial_output",
            "stage": "tools",
            "message": "Evidence collection is underway",
            "data": partial,
        }

    evidence = trace_aggregate(tool_results, plan)
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
            "tickers": getattr(plan, "tickers", []),
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
    yield {
        "type": "stage_done",
        "stage": "aggregation",
        "message": "Evidence aggregated",
        "data": (
            evidence.model_dump(mode="json")
            if hasattr(evidence, "model_dump")
            else str(evidence)
        ),
    }
    partial = partial_output_snapshot(raw_query, "aggregation", evidence=evidence)
    if partial is not None:
        yield {
            "type": "partial_output",
            "stage": "aggregation",
            "message": "Draft analysis is available",
            "data": partial,
        }
    try:
        output = trace_synthesis(evidence, plan)
    except Exception:
        logger.exception(
            "Synthesis failed after aggregation",
            extra={
                "mode": getattr(plan, "mode", None),
                "tickers": getattr(plan, "tickers", []),
            },
        )
        raise
    serialized_output = serialize_output(output)
    yield _timeline_event(
        step="synthesis",
        title="Synthesis",
        status="completed",
        summary="Generated the structured analysis from the evidence bundle.",
        started_at=step_started,
        metadata={
            "output_fields": sorted(serialized_output.keys()),
        },
    )
    yield {
        "type": "stage_done",
        "stage": "synthesis",
        "message": "Report generated",
        "data": serialized_output,
    }

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
    yield {"type": "final_output", "elapsed": round(elapsed, 2), "data": output}
