"""Offline Research evidence enrichment for the unified agent runtime."""

from __future__ import annotations

from ..providers.registry import get_research_provider
from ..schemas.research import ResearchClaim, ResearchEvidence, SecurityIdentity


def _detect_fundamental_conflicts(
    facts,
    fundamentals: dict | None,
) -> list[str]:
    income_statement = (fundamentals or {}).get("income_statement") or {}
    field_by_metric = {
        "Revenue": "revenue_billions",
        "NetIncome": "net_income_billions",
    }
    conflicts: list[str] = []
    for fact in facts:
        # Current fundamentals have no period contract yet; only compare the
        # annual filing so quarterly values are not mistaken for conflicts.
        if fact.form_type != "10-K":
            continue
        field = field_by_metric.get(fact.metric)
        current_value = income_statement.get(field) if field else None
        if not isinstance(fact.value, (int, float)) or not isinstance(current_value, (int, float)):
            continue
        tolerance = max(abs(float(fact.value)) * 0.05, 0.01)
        if abs(float(fact.value) - float(current_value)) > tolerance:
            conflicts.append(
                f"{fact.metric} differs between the {fact.form_type or 'filing'} "
                f"({fact.value}) and current fundamentals ({current_value})."
            )
    return conflicts


def load_fixture_research_evidence(
    identity: SecurityIdentity | None,
    fundamentals: dict | None = None,
) -> ResearchEvidence | None:
    """Load only the checked-in filing fixture for a matching security.

    Missing fixtures are an expected data gap, not a runtime failure. This keeps
    the vertical slice deterministic and avoids making an external SEC request.
    """
    if identity is None:
        return None

    provider = get_research_provider(identity.symbol)
    try:
        provider_identity = provider.resolve_security(identity.symbol)
        filings = provider.get_filings(provider_identity)
    except (OSError, ValueError, KeyError):
        return ResearchEvidence(
            identity=identity,
            data_gaps=[f"SEC filing fixture could not be loaded for {identity.symbol}."],
        )

    facts = [fact for filing in filings for fact in filing.facts]
    claims = [
        ResearchClaim(
            claim_text=(
                f"{fact.metric} was reported as {fact.value} {fact.unit or ''}"
                f" for {fact.fiscal_period or 'the reported period'}."
            ).replace("  ", " "),
            claim_type="fact",
            supporting_source_ids=[fact.source.source_id],
            confidence=1.0,
            data_as_of=fact.period_end,
            limitations=["Historical filing fact; it is not a current market quote."],
        )
        for fact in facts
    ]
    return ResearchEvidence(
        identity=provider_identity,
        filings=filings,
        facts=facts,
        sources=[filing.source for filing in filings],
        claims=claims,
        data_gaps=[] if filings else [f"No 10-K filing was found for {identity.symbol}."],
        conflicts=_detect_fundamental_conflicts(facts, fundamentals),
    )
