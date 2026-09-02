from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
import zipfile

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
    "ticker": {"ticker", "symbol", "stock", "code", "股票代號", "股票代碼", "證券代號"},
    "name": {"name", "company", "company name", "security", "security name", "股票名稱", "證券名稱"},
    "shares": {"shares", "quantity", "qty", "units", "股數", "數量", "持有股數"},
    "avg_cost": {"avg cost", "average cost", "cost", "cost basis", "avg_cost", "成交均價", "平均成本", "買進均價"},
    "current_price": {"current price", "price", "last price", "market price", "current_price", "市價", "現價"},
    "current_value": {"current value", "market value", "value", "position value", "current_value", "現值", "市值"},
    "asset_type": {"asset type", "type", "asset_type"},
    "category": {"category", "theme", "group"},
    "notes": {"notes", "note", "memo", "comment"},
}

NAME_TO_TICKER = {
    "國泰20年美債": "00687B.TW",
    "國泰永續高股息": "00878.TW",
    "國泰台灣科技龍頭": "00881.TW",
    "國泰台灣領袖50": "00922.TW",
    "中華": "2204.TW",
    "鴻海": "2317.TW",
    "廣達": "2382.TW",
    "兆利": "3548.TW",
    "精材": "3374.TW",
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


def _read_xlsx_rows(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Read the first worksheet using the XLSX Open XML parts in stdlib."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in shared_root]
        else:
            shared = []
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ValueError("XLSX file could not be read. Please export it again.") from exc

    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(sheet_xml)
    matrix: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", ns):
        values: dict[int, str] = {}
        for cell in row.findall("x:c", ns):
            reference = cell.attrib.get("r", "A1")
            column = 0
            for char in reference:
                if char.isalpha():
                    column = column * 26 + ord(char.upper()) - 64
            column -= 1
            value = cell.find("x:v", ns)
            text = "" if value is None else value.text or ""
            if cell.attrib.get("t") == "s" and text:
                text = shared[int(text)]
            elif cell.attrib.get("t") == "inlineStr":
                inline = cell.find("x:is", ns)
                text = "" if inline is None else "".join(inline.itertext())
            values[column] = text
        if values:
            matrix.append([values.get(index, "") for index in range(max(values) + 1)])
    if not matrix:
        raise ValueError("XLSX file is missing a header row.")
    headers = matrix[0]
    return headers, [dict(zip(headers, row)) for row in matrix[1:]]


def _preview_rows(headers: list[str], rows: list[dict[str, str]]) -> PortfolioImportPreviewResponse:
    column_map = _resolve_column_map(headers)
    if "ticker" not in column_map and "name" not in column_map:
        raise ValueError("File must include a ticker, symbol, or stock name column.")

    holdings: list[HoldingInput] = []
    errors: list[PortfolioImportIssue] = []
    warnings: list[PortfolioImportIssue] = []
    total_rows = 0

    for row_index, row in enumerate(rows, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        total_rows += 1
        name = (row.get(column_map.get("name", "")) or "").strip()
        raw_ticker = (row.get(column_map.get("ticker", "")) or "").strip()
        if not raw_ticker and (name.startswith(("總", "合計")) or name.lower().startswith("total")):
            continue
        ticker = raw_ticker or NAME_TO_TICKER.get(name, name)
        if not ticker:
            errors.append(PortfolioImportIssue(row_number=row_index, message="Ticker or stock name is required."))
            continue
        try:
            shares = _to_float(row.get(column_map.get("shares")))
            avg_cost = _to_float(row.get(column_map.get("avg_cost")))
            current_price = _to_float(row.get(column_map.get("current_price")))
            current_value = _to_float(row.get(column_map.get("current_value")))
        except ValueError:
            errors.append(PortfolioImportIssue(row_number=row_index, message="Numeric fields must contain valid numbers."))
            continue
        if shares is None or shares <= 0:
            errors.append(PortfolioImportIssue(row_number=row_index, message="Positive shares are required for import preview."))
            continue
        if any(value is not None and value < 0 for value in (avg_cost, current_price, current_value)):
            errors.append(PortfolioImportIssue(row_number=row_index, message="Cost, price, and value must be 0 or higher."))
            continue
        if current_price is None and current_value is None:
            warnings.append(PortfolioImportIssue(row_number=row_index, message="Current price and current value are blank."))
        holdings.append(HoldingInput(
            ticker=ticker,
            name=name or None,
            shares=shares,
            avg_cost=avg_cost,
            buy_price=avg_cost,
            current_price=current_price,
            current_value=current_value,
        ))
    return PortfolioImportPreviewResponse(
        holdings=holdings, errors=errors, warnings=warnings,
        detected_columns=headers, imported_count=len(holdings), total_rows=total_rows,
    )


def preview_portfolio_csv(content: bytes) -> PortfolioImportPreviewResponse:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file is missing a header row.")
    return _preview_rows(reader.fieldnames, list(reader))


def preview_portfolio_file(content: bytes, filename: str) -> PortfolioImportPreviewResponse:
    if filename.lower().endswith(".csv"):
        return preview_portfolio_csv(content)
    if filename.lower().endswith(".xlsx"):
        headers, rows = _read_xlsx_rows(content)
        return _preview_rows(headers, rows)
    raise ValueError("Please upload a CSV or XLSX file.")
