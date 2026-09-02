from __future__ import annotations

from fastapi.responses import JSONResponse

try:
    from ..api.presentation import error_output, serialize_output
    from ..schemas.agent import AgentResult, AgentTask, AgentTaskType
    from ..services.evidence_provenance import build_claim_evidence, extract_source_metadata
except ImportError:
    from api.presentation import error_output, serialize_output
    from schemas.agent import AgentResult, AgentTask, AgentTaskType
    from services.evidence_provenance import build_claim_evidence, extract_source_metadata


def task_to_raw_query(task: AgentTask) -> str:
    if task.raw_query:
        return task.raw_query

    prefixes = {
        AgentTaskType.RESEARCH: "research",
        AgentTaskType.EXPLAIN: "explain",
        AgentTaskType.TRADE: "trade",
        AgentTaskType.WATCHLIST: "watchlist",
    }
    prefix = prefixes.get(task.task_type)
    if prefix and task.tickers:
        return f"{prefix} {' '.join(task.tickers)}"
    return task.task_type.value


def agent_result_to_api_response(result: AgentResult) -> dict:
    payload = serialize_output(result.output)
    source_metadata = extract_source_metadata(result.evidence)
    claim_evidence, unsupported_claims, confidence_score = build_claim_evidence(
        payload,
        source_metadata,
    )
    result.evidence.source_metadata = source_metadata
    result.evidence.claim_evidence = claim_evidence
    result.evidence.unsupported_claims = unsupported_claims
    result.evidence.confidence_score = confidence_score
    audit = {
        "evidence_provenance": [
            source.model_dump(mode="json") for source in source_metadata
        ],
        "claim_evidence": [claim.model_dump(mode="json") for claim in claim_evidence],
        "unsupported_claims": [
            claim.model_dump(mode="json") for claim in unsupported_claims
        ],
        "confidence_score": confidence_score,
    }
    research_payload = result.evidence.external_evidence.get("research_evidence") or {}
    audit["research_data_gaps"] = research_payload.get("data_gaps", [])
    audit["research_conflicts"] = research_payload.get("conflicts", [])
    audit["research_conflict_details"] = research_payload.get("conflict_details", [])
    response = {**payload, **audit}
    legacy = result.evidence.legacy_evidence
    if (
        legacy is not None
        and legacy.total_tool_calls > 0
        and legacy.successful_calls == 0
    ):
        return JSONResponse(
            status_code=502,
            content={
                **response,
                "error": "All evidence providers failed; no grounded result is available.",
            },
        )
    return response


def agent_exception_to_api_error(task: AgentTask, exc: Exception) -> dict:
    return error_output(task_to_raw_query(task), exc)


def agent_exception_status_code(exc: Exception) -> int:
    if isinstance(exc, ValueError):
        return 400
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return 502
    return 500


def agent_exception_to_api_response(
    task: AgentTask,
    exc: Exception,
    *,
    status_code: int | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or agent_exception_status_code(exc),
        content=agent_exception_to_api_error(task, exc),
    )
