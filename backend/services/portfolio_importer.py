from __future__ import annotations

import csv
import io

try:
    from ..schemas.portfolio import HoldingInput
    from ..schemas.portfolio_import import (
        PortfolioImportIssue,
        PortfolioImportPreviewResponse,
    )
except ImportError:
    from schemas.portfolio import HoldingInput
    from schemas.portfolio_import import (
        PortfolioImportIssue,
        PortfolioImportPreviewResponse,
    )


HEADER_ALIASES = {
    "ticker": {"ticker", "symbol", "stock", "code"},
    "name": {"name", "company", "company name", "security", "security name"},
    "shares": {"shares", "quantity", "qty", "units"},
    "avg_cost": {"avg cost", "average cost", "cost", "cost basis", "avg_cost"},
    "current_price": {"current price", "price", "last price", "market price", "current_price"},
    "current_value": {"current value", "market value", "value", "position value", "current_value"},
    "asset_type": {"asset type", "type", "asset_type"},
    "category": {"category", "theme", "group"},
    "notes": {"notes", "note", "memo", "comment"},
}


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "").replace("$", "")
    if cleaned == "":
        return None
    return float(cleaned)


def _resolve_column_map(headers: list[str]) -> dict[str, str]:
    normalized_headers = {_normalize_header(header): header for header in headers}
    resolved: dict[str, str] = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            header = normalized_headers.get(alias)
            if header is not None:
                resolved[field] = header
                break
    return resolved


def preview_portfolio_csv(content: bytes) -> PortfolioImportPreviewResponse:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file is missing a header row.")

    column_map = _resolve_column_map(reader.fieldnames)
    if "ticker" not in column_map:
        raise ValueError("CSV must include a ticker or symbol column.")

    holdings: list[HoldingInput] = []
    errors: list[PortfolioImportIssue] = []
    warnings: list[PortfolioImportIssue] = []
    total_rows = 0

    for row_index, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        total_rows += 1

        ticker = (row.get(column_map["ticker"]) or "").strip()
        if not ticker:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Ticker is required.",
                )
            )
            continue

        try:
            shares = _to_float(row.get(column_map.get("shares")))
            avg_cost = _to_float(row.get(column_map.get("avg_cost")))
            current_price = _to_float(row.get(column_map.get("current_price")))
            current_value = _to_float(row.get(column_map.get("current_value")))
        except ValueError:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Numeric fields must contain valid numbers.",
                )
            )
            continue

        if shares is None or shares <= 0:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Positive shares are required for import preview.",
                )
            )
            continue

        if avg_cost is not None and avg_cost < 0:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Average cost must be 0 or higher.",
                )
            )
            continue
        if current_price is not None and current_price < 0:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Current price must be 0 or higher.",
                )
            )
            continue
        if current_value is not None and current_value < 0:
            errors.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message="Current value must be 0 or higher.",
                )
            )
            continue

        if current_price is None and current_value is None:
            warnings.append(
                PortfolioImportIssue(
                    row_number=row_index,
                    message=(
                        "Current price and current value are blank, so later "
                        "analysis may need manual updates."
                    ),
                )
            )

        holdings.append(
            HoldingInput(
                ticker=ticker,
                name=(row.get(column_map.get("name")) or "").strip() or None,
                shares=shares,
                avg_cost=avg_cost,
                current_price=current_price,
                current_value=current_value,
                asset_type=(row.get(column_map.get("asset_type")) or "").strip() or None,
                category=(row.get(column_map.get("category")) or "").strip() or None,
                notes=(row.get(column_map.get("notes")) or "").strip() or None,
            )
        )

    return PortfolioImportPreviewResponse(
        holdings=holdings,
        errors=errors,
        warnings=warnings,
        detected_columns=reader.fieldnames,
        imported_count=len(holdings),
        total_rows=total_rows,
    )
