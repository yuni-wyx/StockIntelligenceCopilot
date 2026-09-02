"""Deterministic security identity resolution for Research requests."""

from __future__ import annotations

from ..schemas.research import SecurityIdentity
from ..symbols import detect_market, normalize_symbol, symbol_info


def resolve_security(
    symbol: str,
    *,
    exchange: str | None = None,
    country: str | None = None,
) -> SecurityIdentity:
    """Resolve supported symbols without guessing an unverified company name."""
    canonical = normalize_symbol(symbol)
    if not canonical:
        raise ValueError("A ticker or security symbol is required.")

    market = detect_market(canonical)
    info = symbol_info(canonical)
    resolved_country = country or ("TW" if market == "TW" else "US")
    currency = "TWD" if market == "TW" else "USD"

    return SecurityIdentity(
        canonical_id=f"{resolved_country}:{canonical}",
        symbol=canonical,
        exchange=exchange,
        company_name=info.display_name if info.display_name != canonical else None,
        asset_type="equity",
        country=resolved_country,
        currency=currency,
        aliases=[symbol] if symbol.strip().upper() != canonical else [],
    )
