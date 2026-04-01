from __future__ import annotations

import re
from dataclasses import dataclass

TW_ALIAS_MAP: dict[str, str] = {
    "2330": "2330.TW",
    "2330.tw": "2330.TW",
    "台積電": "2330.TW",
    "tsmc": "2330.TW",
    "taiwan semiconductor": "2330.TW",
    "taiwan semiconductor manufacturing": "2330.TW",
    "2317": "2317.TW",
    "2317.tw": "2317.TW",
    "鴻海": "2317.TW",
    "foxconn": "2317.TW",
    "hon hai": "2317.TW",
    "2454": "2454.TW",
    "2454.tw": "2454.TW",
    "聯發科": "2454.TW",
    "mediatek": "2454.TW",
}

TW_CANONICAL_TO_NAME: dict[str, str] = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
}


@dataclass(frozen=True)
class SymbolInfo:
    raw_input: str
    canonical: str
    market: str
    display_name: str


def normalize_symbol(value: str) -> str:
    if not value:
        return ""

    raw = value.strip()
    lower = raw.lower()

    if lower in TW_ALIAS_MAP:
        return TW_ALIAS_MAP[lower]
    if raw in TW_ALIAS_MAP:
        return TW_ALIAS_MAP[raw]

    if re.fullmatch(r"\d{4}\.tw", lower):
        return f"{raw[:4]}.TW"

    if re.fullmatch(r"\d{4}", raw):
        return f"{raw}.TW"

    return raw.upper()


def detect_market(value: str) -> str:
    canonical = normalize_symbol(value)
    if canonical.endswith(".TW"):
        return "TW"
    return "US"


def market_label(value: str) -> str:
    return "Taiwan" if detect_market(value) == "TW" else "US"


def symbol_info(value: str) -> SymbolInfo:
    canonical = normalize_symbol(value)
    market = detect_market(canonical)
    display_name = TW_CANONICAL_TO_NAME.get(canonical, canonical)
    return SymbolInfo(
        raw_input=value,
        canonical=canonical,
        market=market,
        display_name=display_name,
    )


def extract_symbols_from_text(text: str) -> list[str]:
    if not text:
        return []

    canonical_matches: list[str] = []
    normalized_text = text.strip()
    upper = normalized_text.upper()

    pattern = r"\b(?:\d{4}(?:\.TW)?|[A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b"
    raw_candidates = re.findall(pattern, upper)

    stopwords = {
        "A", "I", "IN", "ON", "FOR", "AND", "OR", "THE", "TO", "OF",
        "AT", "AN", "BY", "IS", "IT", "AS", "BE", "DO", "GO", "IF",
        "MY", "NO", "SO", "UP", "VS", "ME", "WE", "AM",
        "RESEARCH", "EXPLAIN", "WATCHLIST", "WATCH", "MONITOR",
        "TRADE", "DECISION", "SETUP", "ANALYZE", "WHY", "MOVE", "DEEP", "DIVE",
    }

    for candidate in raw_candidates:
        if candidate in stopwords:
            continue
        canonical = normalize_symbol(candidate)
        if canonical not in canonical_matches:
            canonical_matches.append(canonical)

    lowered_text = normalized_text.lower()
    for alias, canonical in TW_ALIAS_MAP.items():
        if any(ch.isalpha() for ch in alias) or any(ord(ch) > 127 for ch in alias):
            if alias in lowered_text and canonical not in canonical_matches:
                canonical_matches.append(canonical)

    return canonical_matches
