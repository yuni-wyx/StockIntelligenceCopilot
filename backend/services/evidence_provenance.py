from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from ..schemas.agent import AgentEvidenceBundle
    from ..schemas.evidence_schema import ClaimEvidence, SourceMetadata, UnsupportedClaim
except ImportError:
    from schemas.agent import AgentEvidenceBundle
    from schemas.evidence_schema import ClaimEvidence, SourceMetadata, UnsupportedClaim


UNSAFE_CERTAINTY_TERMS = (
    "guarantee",
    "guaranteed",
    "definitely",
    "certainly",
    "risk-free",
    "no risk",
    "sure thing",
    "cannot lose",
)

FIELD_SOURCE_HINTS = {
    "fundamental_summary": ("filing", "fundamentals", "analyst_signal", "signal"),
    "bull_case": ("fundamentals", "analyst_signal", "news"),
    "bear_case": ("fundamentals", "news", "analyst_signal"),
    "recent_news_summary": ("news",),
    "overall_sentiment": ("news", "fundamentals"),
    "what_to_watch_next": ("news", "earnings", "fundamentals", "signal"),
    "price_move_summary": ("market_data", "news", "earnings", "signal"),
    "price_change_pct": ("market_data",),
    "volume_context": ("market_data", "signal"),
    "ranked_causes": ("market_data", "news", "earnings", "fundamentals"),
    "overall_confidence": ("market_data", "news", "earnings", "fundamentals"),
    "bias": ("market_data", "fundamentals", "news", "analyst_signal"),
    "buy_zone": ("market_data",),
    "stop_loss": ("market_data",),
    "take_profit": ("market_data", "analyst_signal"),
    "reasoning": ("market_data", "fundamentals", "news", "analyst_signal"),
    "portfolio_summary": ("portfolio_metric", "news", "fundamentals"),
    "ticker_summaries": ("news", "earnings", "fundamentals", "market_data"),
    "macro_risks": ("news", "fundamentals"),
    "top_opportunities": ("fundamentals", "news", "analyst_signal"),
    "summary": ("portfolio_metric", "portfolio_input"),
    "suggestions": ("portfolio_metric", "portfolio_input", "news", "fundamentals"),
    "risk_flags": ("portfolio_metric", "portfolio_input", "fundamentals"),
    "total_cost_basis": ("portfolio_metric", "portfolio_input"),
    "total_current_value": ("portfolio_metric", "portfolio_input", "market_data"),
    "total_unrealized_gain_loss": ("portfolio_metric", "portfolio_input", "market_data"),
    "total_return_pct": ("portfolio_metric", "portfolio_input", "market_data"),
    "estimated_annual_dividend": ("portfolio_metric", "fundamentals"),
    "estimated_monthly_dividend": ("portfolio_metric", "fundamentals"),
    "asset_type_exposure": ("portfolio_metric", "portfolio_input"),
    "category_exposure": ("portfolio_metric", "portfolio_input", "fundamentals"),
    "sector_exposure": ("portfolio_metric", "fundamentals"),
    "theme_exposure": ("portfolio_metric", "fundamentals", "portfolio_input"),
    "market_exposure": ("portfolio_metric", "portfolio_input"),
    "news_to_monitor": ("news",),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


def _source_id(source_type: str, ticker: str | None, suffix: str = "primary") -> str:
    target = ticker or "portfolio"
    return f"{source_type}:{target}:{suffix}"


def _has_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return True


def _short_claim(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(item) for item in value[:3]]
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = ", ".join(f"{key}: {val}" for key, val in list(value.items())[:5])
    else:
        text = str(value)
    return text[:280]


def _source_confidence(source: SourceMetadata) -> float:
    return source.confidence


def _dedupe_sources(sources: list[SourceMetadata]) -> list[SourceMetadata]:
    seen: set[str] = set()
    deduped: list[SourceMetadata] = []
    for source in sources:
        if source.source_id in seen:
            continue
        seen.add(source.source_id)
        deduped.append(source)
    return deduped


def _extract_legacy_sources(bundle: AgentEvidenceBundle) -> list[SourceMetadata]:
    evidence = bundle.legacy_evidence
    if evidence is None:
        return []

    sources: list[SourceMetadata] = []
    retrieved_at = _now_iso()
    for ticker, ticker_evidence in evidence.tickers_evidence.items():
        if _has_payload(ticker_evidence.market_data):
            sources.append(
                SourceMetadata(
                    source_id=_source_id("market_data", ticker),
                    source_type="market_data",
                    ticker=ticker,
                    provider="market data tool",
                    tool="market_data",
                    confidence=0.85,
                    retrieved_at=retrieved_at,
                    fields=sorted(ticker_evidence.market_data.keys()),
                )
            )
        if _has_payload(ticker_evidence.fundamentals):
            sources.append(
                SourceMetadata(
                    source_id=_source_id("fundamentals", ticker),
                    source_type="fundamentals",
                    ticker=ticker,
                    provider="yfinance",
                    tool="fundamentals",
                    confidence=0.75,
                    retrieved_at=retrieved_at,
                    fields=sorted(ticker_evidence.fundamentals.keys()),
                )
            )
            estimates = ticker_evidence.fundamentals.get("estimates")
            if _has_payload(estimates):
                sources.append(
                    SourceMetadata(
                        source_id=_source_id("analyst_signal", ticker),
                        source_type="analyst_signal",
                        ticker=ticker,
                        provider="yfinance analyst estimates",
                        tool="fundamentals",
                        confidence=0.65,
                        retrieved_at=retrieved_at,
                        fields=sorted(estimates.keys()) if isinstance(estimates, dict) else [],
                    )
                )
        for index, article in enumerate(ticker_evidence.news or [], start=1):
            relevance = article.get("relevance_score", 0.6) if isinstance(article, dict) else 0.6
            sources.append(
                SourceMetadata(
                    source_id=_source_id("news", ticker, str(index)),
                    source_type="news",
                    ticker=ticker,
                    provider=article.get("source") if isinstance(article, dict) else None,
                    title=article.get("title") if isinstance(article, dict) else None,
                    url=article.get("url") if isinstance(article, dict) else None,
                    published_at=article.get("published_at") if isinstance(article, dict) else None,
                    tool="news",
                    confidence=max(0.35, min(float(relevance or 0.6), 0.9)),
                    retrieved_at=retrieved_at,
                    fields=["title", "source", "url", "published_at", "sentiment"],
                )
            )
        if _has_payload(ticker_evidence.earnings):
            sources.append(
                SourceMetadata(
                    source_id=_source_id("earnings", ticker),
                    source_type="earnings",
                    ticker=ticker,
                    provider="earnings tool",
                    tool="earnings",
                    confidence=0.7,
                    retrieved_at=retrieved_at,
                    fields=sorted(ticker_evidence.earnings.keys()),
                )
            )
        if _has_payload(getattr(ticker_evidence, "signal", None)):
            signal_fields = (
                sorted(ticker_evidence.signal.keys())
                if isinstance(ticker_evidence.signal, dict)
                else []
            )
            sources.append(
                SourceMetadata(
                    source_id=_source_id("signal", ticker),
                    source_type="signal",
                    ticker=ticker,
                    provider="signal engine",
                    tool="signal",
                    confidence=0.7,
                    retrieved_at=retrieved_at,
                    fields=signal_fields,
                )
            )
    return sources


def _extract_portfolio_sources(bundle: AgentEvidenceBundle) -> list[SourceMetadata]:
    if "portfolio_analysis" not in bundle.derived_metrics:
        return []

    retrieved_at = _now_iso()
    sources = [
        SourceMetadata(
            source_id="portfolio_input:portfolio:primary",
            source_type="portfolio_input",
            provider="user input",
            confidence=0.95,
            retrieved_at=retrieved_at,
            fields=["holdings", "risk_profile", "goal", "base_currency"],
        ),
        SourceMetadata(
            source_id="portfolio_metric:portfolio:primary",
            source_type="portfolio_metric",
            provider="deterministic portfolio calculator",
            confidence=0.9,
            retrieved_at=retrieved_at,
            fields=[
                "cost_basis",
                "current_value",
                "unrealized_gain_loss",
                "return_pct",
                "exposure",
                "risk_flags",
            ],
        ),
    ]
    holdings = bundle.external_evidence.get("holdings", {})
    if isinstance(holdings, dict):
        for ticker, payload in holdings.items():
            if not isinstance(payload, dict):
                continue
            if _has_payload(payload.get("market_data")) or payload.get("current_price") is not None:
                sources.append(
                    SourceMetadata(
                        source_id=_source_id("market_data", ticker),
                        source_type="market_data",
                        ticker=ticker,
                        provider="market data tool",
                        tool="market_data",
                        confidence=0.85,
                        retrieved_at=retrieved_at,
                        fields=["current_price", "market_data"],
                    )
                )
            if _has_payload(payload.get("fundamentals")):
                fundamentals = payload.get("fundamentals") or {}
                sources.append(
                    SourceMetadata(
                        source_id=_source_id("fundamentals", ticker),
                        source_type="fundamentals",
                        ticker=ticker,
                        provider="yfinance",
                        tool="fundamentals",
                        confidence=0.75,
                        retrieved_at=retrieved_at,
                        fields=(
                            sorted(fundamentals.keys())
                            if isinstance(fundamentals, dict)
                            else []
                        ),
                    )
                )
            for index, article in enumerate(payload.get("news_articles") or [], start=1):
                sources.append(
                    SourceMetadata(
                        source_id=_source_id("news", ticker, str(index)),
                        source_type="news",
                        ticker=ticker,
                        provider=article.get("source"),
                        title=article.get("title"),
                        url=article.get("url"),
                        published_at=article.get("published_at"),
                        tool="news",
                        confidence=max(
                            0.35,
                            min(float(article.get("relevance_score") or 0.6), 0.9),
                        ),
                        retrieved_at=retrieved_at,
                        fields=["title", "source", "url", "published_at", "sentiment"],
                    )
                )
    return sources


def _extract_research_sources(bundle: AgentEvidenceBundle) -> list[SourceMetadata]:
    payload = bundle.external_evidence.get("research_evidence")
    if not isinstance(payload, dict):
        return []
    sources: list[SourceMetadata] = []
    for raw_source in payload.get("sources", []):
        if not isinstance(raw_source, dict) or not raw_source.get("source_id"):
            continue
        source = SourceMetadata(
            source_id=raw_source["source_id"],
            source_type="filing",
            ticker=(payload.get("identity") or {}).get("symbol"),
            provider=raw_source.get("provider"),
            url=raw_source.get("source_url"),
            published_at=raw_source.get("published_at"),
            retrieved_at=raw_source.get("retrieved_at"),
            data_as_of=raw_source.get("data_as_of"),
            freshness=raw_source.get("freshness"),
            source_tier=raw_source.get("source_tier"),
            tool="sec_edgar",
            confidence=1.0 if raw_source.get("source_tier") == "tier_1" else 0.8,
            fields=["filing", "facts", "source_tier"],
        )
        sources.append(source)
    return sources


def extract_source_metadata(bundle: AgentEvidenceBundle) -> list[SourceMetadata]:
    return _dedupe_sources(
        [
            *_extract_legacy_sources(bundle),
            *_extract_portfolio_sources(bundle),
            *_extract_research_sources(bundle),
        ]
    )


def _evidence_ids_for_field(field: str, sources: list[SourceMetadata]) -> list[str]:
    desired = FIELD_SOURCE_HINTS.get(field)
    if desired is None:
        desired = tuple({source.source_type for source in sources})
    return [source.source_id for source in sources if source.source_type in desired]


def _iter_claim_fields(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    claims: list[tuple[str, Any]] = []
    for field, value in payload.items():
        if field in {
            "generated_at",
            "ticker",
            "tickers",
            "holdings",
            "evidence_provenance",
            "claim_evidence",
            "unsupported_claims",
            "confidence_score",
        }:
            continue
        if _has_payload(value):
            claims.append((field, value))
    return claims


def _unsafe_claim_reason(text: str) -> str | None:
    lowered = text.lower()
    for term in UNSAFE_CERTAINTY_TERMS:
        if term in lowered:
            return f"Uses over-certain wording: {term}"
    return None


def build_claim_evidence(
    output_payload: dict[str, Any],
    sources: list[SourceMetadata],
) -> tuple[list[ClaimEvidence], list[UnsupportedClaim], float]:
    claims: list[ClaimEvidence] = []
    unsupported: list[UnsupportedClaim] = []
    source_by_id = {source.source_id: source for source in sources}

    for index, (field, value) in enumerate(_iter_claim_fields(output_payload), start=1):
        claim = _short_claim(value)
        evidence_ids = _evidence_ids_for_field(field, sources)
        if evidence_ids:
            score = sum(_source_confidence(source_by_id[source_id]) for source_id in evidence_ids)
            score = round(score / len(evidence_ids), 2)
        else:
            score = 0.0

        notes: list[str] = []
        unsafe_reason = _unsafe_claim_reason(claim)
        is_unsupported = not evidence_ids or unsafe_reason is not None
        if not evidence_ids:
            notes.append("No matching evidence source was available for this field.")
            unsupported.append(
                UnsupportedClaim(
                    output_field=field,
                    claim=claim,
                    reason="No matching evidence source was available.",
                    severity="medium",
                )
            )
        if unsafe_reason is not None:
            notes.append(unsafe_reason)
            unsupported.append(
                UnsupportedClaim(
                    output_field=field,
                    claim=claim,
                    reason=unsafe_reason,
                    severity="high",
                )
            )

        claims.append(
            ClaimEvidence(
                claim_id=f"claim:{index}",
                output_field=field,
                claim=claim,
                evidence_ids=evidence_ids,
                confidence_score=score,
                confidence_label=_label(score),
                unsupported=is_unsupported,
                notes=notes,
            )
        )

    supported_scores = [
        claim.confidence_score for claim in claims if not claim.unsupported and claim.evidence_ids
    ]
    confidence = (
        round(sum(supported_scores) / len(supported_scores), 2)
        if supported_scores
        else 0.0
    )
    return claims, unsupported, confidence


def build_evidence_audit(
    bundle: AgentEvidenceBundle,
    output_payload: dict[str, Any],
) -> dict[str, Any]:
    sources = extract_source_metadata(bundle)
    claim_evidence, unsupported_claims, confidence = build_claim_evidence(output_payload, sources)
    return {
        "evidence_provenance": [source.model_dump(mode="json") for source in sources],
        "claim_evidence": [claim.model_dump(mode="json") for claim in claim_evidence],
        "unsupported_claims": [claim.model_dump(mode="json") for claim in unsupported_claims],
        "confidence_score": confidence,
    }
