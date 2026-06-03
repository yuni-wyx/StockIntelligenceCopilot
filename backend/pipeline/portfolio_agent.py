from __future__ import annotations

import json
import logging

try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    JsonOutputParser = None
    ChatPromptTemplate = None
    ChatOpenAI = None

try:
    from ..schemas.agent import AgentEvidenceBundle, AgentPlan
    from ..schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioAgentResponse,
        PortfolioAnalysisResponse,
    )
    from ..services.portfolio_store import PortfolioStore
    from .portfolio_orchestrator import analyze_portfolio_with_evidence
except ImportError:
    from pipeline.portfolio_orchestrator import analyze_portfolio_with_evidence
    from schemas.agent import AgentEvidenceBundle, AgentPlan
    from schemas.portfolio import (
        PortfolioAgentRequest,
        PortfolioAgentResponse,
        PortfolioAnalysisResponse,
    )
    from services.portfolio_store import PortfolioStore

logger = logging.getLogger(__name__)


def _fallback_agent_response(
    analysis: PortfolioAnalysisResponse,
    evidence: dict,
    question: str | None,
) -> PortfolioAgentResponse:
    largest = max(
        analysis.holdings,
        key=lambda item: item.portfolio_weight_pct or 0,
        default=None,
    )
    conclusion = (
        "Conclusion: the portfolio is analyzable, but any reallocation should balance "
        "concentration, income stability, and missing data."
    )
    if question:
        conclusion = f"{conclusion} User question: {question}"

    key_numbers = {
        "total_current_value": analysis.total_current_value,
        "total_unrealized_gain_loss": analysis.total_unrealized_gain_loss,
        "total_return_pct": analysis.total_return_pct,
        "estimated_annual_dividend": analysis.estimated_annual_dividend,
        "overall_score": analysis.overall_score,
    }
    evidence_used = [
        f"Top holdings reviewed: {', '.join(evidence['targets']['top_holdings']) or 'none'}",
        f"Theme exposure: {json.dumps(analysis.theme_exposure, ensure_ascii=False)}",
    ]
    if largest:
        evidence_used.append(
            f"Largest holding: {largest.ticker} at {largest.portfolio_weight_pct or 0:.2f}%."
        )
    return PortfolioAgentResponse(
        conclusion=conclusion,
        current_portfolio_diagnosis=analysis.summary,
        key_numbers=key_numbers,
        evidence_used=evidence_used,
        bull_case=(
            "Bull case: the portfolio may already have meaningful winners "
            "and a visible income base."
        ),
        bear_case=(
            "Bear case: concentration, theme overlap, or weak defensive ballast "
            "could raise drawdown risk."
        ),
        base_case=(
            "Base case: trim only the most concentrated exposures gradually, "
            "and compare income loss before reallocating."
        ),
        suggested_next_actions=analysis.suggestions,
        risks=analysis.risk_flags,
        missing_data=analysis.missing_data,
    )


def _build_llm_chain():
    if not (ChatPromptTemplate and ChatOpenAI and JsonOutputParser):
        return None
    prompt = ChatPromptTemplate.from_template(
        """
You are a careful portfolio intelligence assistant.

Use only the provided evidence.
Do not invent any numbers.
If data is missing, say it is missing.
Do not promise returns or guaranteed outcomes.

User question:
{question}

Structured evidence:
{evidence}

Return valid JSON only:
{{
  "conclusion": "short conclusion",
  "current_portfolio_diagnosis": "diagnosis",
  "key_numbers": {{"label": "value"}},
  "evidence_used": ["..."],
  "bull_case": "bull case",
  "bear_case": "bear case",
  "base_case": "base case",
  "suggested_next_actions": ["..."],
  "risks": ["..."],
  "missing_data": ["..."]
}}
"""
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return prompt | llm | JsonOutputParser()


def synthesise_portfolio_agent_output(
    bundle: AgentEvidenceBundle,
    plan: AgentPlan,
) -> PortfolioAgentResponse:
    analysis_payload = bundle.derived_metrics.get("portfolio_analysis")
    if analysis_payload is None:
        raise ValueError("Portfolio agent bundle is missing portfolio analysis.")

    analysis = PortfolioAnalysisResponse(**analysis_payload)
    evidence = {
        "analysis": analysis.model_dump(mode="json"),
        "targets": bundle.derived_metrics.get("portfolio_targets", {}),
        "tool_evidence": bundle.external_evidence.get("holdings", {}),
    }
    question = bundle.context.get("user_question")
    chain = _build_llm_chain()
    if chain is None:
        return _fallback_agent_response(analysis, evidence, question)

    try:
        payload = chain.invoke(
            {
                "question": question or "Provide a grounded portfolio recommendation.",
                "evidence": json.dumps(evidence, ensure_ascii=False, default=str),
            }
        )
        return PortfolioAgentResponse(**payload)
    except Exception:
        logger.exception("Portfolio agent LLM synthesis failed")
        return _fallback_agent_response(analysis, evidence, question)


def _run_portfolio_agent_impl(
    request: PortfolioAgentRequest,
    *,
    store: PortfolioStore | None = None,
) -> PortfolioAgentResponse:
    store = store or PortfolioStore()
    portfolio = request.portfolio
    if portfolio is None:
        record = store.load_portfolio("current")
        if record is None:
            raise ValueError("No current portfolio is saved.")
        portfolio = record.portfolio

    analysis, enrichment = analyze_portfolio_with_evidence(portfolio)
    evidence = {
        "analysis": analysis.model_dump(mode="json"),
        "targets": {},
        "tool_evidence": enrichment,
    }
    return _fallback_agent_response(analysis, evidence, request.user_question)


def run_portfolio_agent(
    request: PortfolioAgentRequest,
    *,
    store: PortfolioStore | None = None,
) -> PortfolioAgentResponse:
    try:
        from .agent_runtime import execute_portfolio_agent_request
    except ImportError:
        from pipeline.agent_runtime import execute_portfolio_agent_request

    return execute_portfolio_agent_request(request, store=store)
