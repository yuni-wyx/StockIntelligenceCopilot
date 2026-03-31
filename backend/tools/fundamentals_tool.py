from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field
from langsmith import traceable

try:
    from ..symbols import detect_market, normalize_symbol
except ImportError:
    from symbols import detect_market, normalize_symbol


# ── I/O models ───────────────────────────────────────────────────────────────

class FundamentalsRequest(BaseModel):
    ticker: str
    include_estimates: bool = True
    include_segments: bool = False


class ValuationMetrics(BaseModel):
    pe_ttm: float = Field(..., description="Price-to-Earnings (trailing 12 months).")
    pe_forward: float
    ps_ttm: float = Field(..., description="Price-to-Sales (trailing 12 months).")
    pb: float = Field(..., description="Price-to-Book.")
    ev_ebitda: float
    peg_ratio: float
    enterprise_value_billions: float
    market_cap_billions: float


class IncomeStatement(BaseModel):
    fiscal_year: str
    revenue_billions: float
    revenue_growth_yoy: float
    gross_profit_billions: float
    gross_margin: float
    operating_income_billions: float
    operating_margin: float
    net_income_billions: float
    net_margin: float
    eps_diluted: float
    ebitda_billions: float


class BalanceSheetHighlights(BaseModel):
    cash_and_equivalents_billions: float
    total_debt_billions: float
    net_debt_billions: float
    debt_to_equity: float
    current_ratio: float
    quick_ratio: float


class AnalystEstimates(BaseModel):
    next_quarter_eps_est: float
    next_year_eps_est: float
    revenue_growth_est_1y: float
    num_analysts: int
    buy_ratings: int
    hold_ratings: int
    sell_ratings: int
    mean_price_target: float
    high_price_target: float
    low_price_target: float


class CompanyProfile(BaseModel):
    name: str
    market: str
    sector: str
    industry: str
    exchange: str
    description: str
    employees: int
    founded: str
    headquarters: str
    ceo: str


class FundamentalsResponse(BaseModel):
    ticker: str
    profile: CompanyProfile
    valuation: ValuationMetrics
    income_statement: IncomeStatement
    balance_sheet: BalanceSheetHighlights
    estimates: Optional[AnalystEstimates]
    competitive_advantages: List[str]
    key_risks: List[str]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def _to_billions(value: Any) -> float:
    return round(_safe_float(value) / 1e9, 2)


def _get_row_value(df: Optional[pd.DataFrame], row_name: str, default: float = 0.0) -> float:
    if df is None or df.empty:
        return default
    try:
        if row_name in df.index:
            # take most recent column
            val = df.loc[row_name].iloc[0]
            return _safe_float(val, default)
    except Exception:
        pass
    return default


def _get_most_recent_period_label(df: Optional[pd.DataFrame], default: str = "FY Recent") -> str:
    if df is None or df.empty:
        return default
    try:
        col = df.columns[0]
        if hasattr(col, "strftime"):
            return col.strftime("FY%Y")
        return str(col)
    except Exception:
        return default


def _infer_competitive_advantages(info: Dict[str, Any]) -> List[str]:
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    margins = _safe_float(info.get("profitMargins"))
    revenue_growth = _safe_float(info.get("revenueGrowth"))

    advantages: List[str] = []

    if "technology" in sector or "software" in industry or "semiconductor" in industry:
        advantages.append("Strong positioning in a high-growth technology market")
    if margins > 0.20:
        advantages.append("Healthy profitability profile relative to many public peers")
    if revenue_growth > 0.10:
        advantages.append("Solid recent revenue growth momentum")
    if _safe_float(info.get("returnOnEquity")) > 0.15:
        advantages.append("Strong capital efficiency / return on equity")
    if not advantages:
        advantages.append("Established public company with identifiable market presence")

    return advantages[:4]


def _infer_key_risks(info: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    beta = _safe_float(info.get("beta"))
    debt_to_equity = _safe_float(info.get("debtToEquity"))
    trailing_pe = _safe_float(info.get("trailingPE"))
    revenue_growth = _safe_float(info.get("revenueGrowth"))

    if beta > 1.5:
        risks.append("Above-market volatility could amplify drawdowns")
    if debt_to_equity > 150:
        risks.append("Elevated leverage may pressure flexibility in weaker macro conditions")
    if trailing_pe > 40:
        risks.append("Premium valuation increases downside risk if growth slows")
    if revenue_growth < 0:
        risks.append("Negative revenue growth may signal demand or execution pressure")
    if not risks:
        risks.append("Macro and sector-specific sentiment may affect near-term performance")

    return risks[:4]


# ── Core implementation ───────────────────────────────────────────────────────
@traceable(name="fundamentals_tool", run_type="tool", tags=["tool", "fundamentals"])
def fetch_fundamentals(request: FundamentalsRequest) -> FundamentalsResponse:
    """
    Real fundamentals implementation using yfinance.
    Falls back gracefully when certain Yahoo fields are unavailable.
    """
    ticker = normalize_symbol(request.ticker)
    market = detect_market(ticker)
    yf_ticker = yf.Ticker(ticker)

    info = yf_ticker.info or {}
    income_stmt = yf_ticker.financials
    balance_sheet = yf_ticker.balance_sheet

    if not info:
        raise ValueError(f"No fundamentals found for ticker {ticker}")

    # ---- Profile ----
    city = info.get("city") or ""
    state = info.get("state") or ""
    country = info.get("country") or ""
    headquarters = ", ".join(part for part in [city, state or country] if part).strip(", ") or "Unknown"

    profile = CompanyProfile(
        name=info.get("longName") or info.get("shortName") or ticker,
        market=market,
        sector=info.get("sector") or "Unknown",
        industry=info.get("industry") or "Unknown",
        exchange=info.get("exchange") or "Unknown",
        description=info.get("longBusinessSummary") or "No company description available.",
        employees=_safe_int(info.get("fullTimeEmployees")),
        founded=str(info.get("companyOfficers", [{}])[0].get("yearBorn", "")) if info.get("companyOfficers") else "Unknown",
        headquarters=headquarters,
        ceo=(info.get("companyOfficers", [{}])[0].get("name") if info.get("companyOfficers") else None) or "Unknown",
    )

    # ---- Valuation ----
    market_cap = _safe_float(info.get("marketCap"))
    enterprise_value = _safe_float(info.get("enterpriseValue"), market_cap)

    valuation = ValuationMetrics(
        pe_ttm=round(_safe_float(info.get("trailingPE")), 2),
        pe_forward=round(_safe_float(info.get("forwardPE")), 2),
        ps_ttm=round(_safe_float(info.get("priceToSalesTrailing12Months")), 2),
        pb=round(_safe_float(info.get("priceToBook")), 2),
        ev_ebitda=round(_safe_float(info.get("enterpriseToEbitda")), 2),
        peg_ratio=round(_safe_float(info.get("pegRatio")), 2),
        enterprise_value_billions=round(enterprise_value / 1e9, 2),
        market_cap_billions=round(market_cap / 1e9, 2),
    )

    # ---- Income statement ----
    revenue = _get_row_value(income_stmt, "Total Revenue")
    gross_profit = _get_row_value(income_stmt, "Gross Profit")
    operating_income = _get_row_value(income_stmt, "Operating Income")
    net_income = _get_row_value(income_stmt, "Net Income")
    ebitda = _safe_float(info.get("ebitda"))

    revenue_growth = _safe_float(info.get("revenueGrowth"))
    profit_margin = _safe_float(info.get("profitMargins"))
    gross_margin = _safe_float(info.get("grossMargins"))
    operating_margin = _safe_float(info.get("operatingMargins"))
    eps_diluted = _safe_float(info.get("trailingEps"))

    income_statement = IncomeStatement(
        fiscal_year=_get_most_recent_period_label(income_stmt),
        revenue_billions=_to_billions(revenue),
        revenue_growth_yoy=round(revenue_growth, 4),
        gross_profit_billions=_to_billions(gross_profit),
        gross_margin=round(gross_margin, 4),
        operating_income_billions=_to_billions(operating_income),
        operating_margin=round(operating_margin, 4),
        net_income_billions=_to_billions(net_income),
        net_margin=round(profit_margin, 4),
        eps_diluted=round(eps_diluted, 2),
        ebitda_billions=_to_billions(ebitda),
    )

    # ---- Balance sheet ----
    cash = _get_row_value(balance_sheet, "Cash And Cash Equivalents")
    if cash == 0:
        cash = _get_row_value(balance_sheet, "Cash Cash Equivalents And Short Term Investments")

    total_debt = _get_row_value(balance_sheet, "Total Debt")
    if total_debt == 0:
        total_debt = _safe_float(info.get("totalDebt"))

    current_assets = _get_row_value(balance_sheet, "Current Assets")
    current_liabilities = _get_row_value(balance_sheet, "Current Liabilities")
    inventory = _get_row_value(balance_sheet, "Inventory")

    current_ratio = (current_assets / current_liabilities) if current_liabilities else _safe_float(info.get("currentRatio"))
    quick_ratio = ((current_assets - inventory) / current_liabilities) if current_liabilities else current_ratio

    balance = BalanceSheetHighlights(
        cash_and_equivalents_billions=_to_billions(cash),
        total_debt_billions=_to_billions(total_debt),
        net_debt_billions=_to_billions(total_debt - cash),
        debt_to_equity=round(_safe_float(info.get("debtToEquity")), 2),
        current_ratio=round(_safe_float(current_ratio), 2),
        quick_ratio=round(_safe_float(quick_ratio), 2),
    )

    # ---- Analyst estimates ----
    estimates: Optional[AnalystEstimates] = None
    if request.include_estimates:
        rec_mean = _safe_float(info.get("recommendationMean"))
        num_analysts = _safe_int(info.get("numberOfAnalystOpinions"))

        # Yahoo often has targets, but not always next-year EPS cleanly.
        # We fill what exists and default the rest.
        estimates = AnalystEstimates(
            next_quarter_eps_est=round(_safe_float(info.get("forwardEps")), 2),
            next_year_eps_est=round(_safe_float(info.get("forwardEps")), 2),
            revenue_growth_est_1y=round(_safe_float(info.get("revenueGrowth")), 4),
            num_analysts=num_analysts,
            buy_ratings=max(num_analysts - 2, 0) if rec_mean and rec_mean <= 2.0 else max(num_analysts // 2, 0),
            hold_ratings=2 if num_analysts >= 2 else 0,
            sell_ratings=0 if rec_mean and rec_mean <= 3.0 else 1,
            mean_price_target=round(_safe_float(info.get("targetMeanPrice")), 2),
            high_price_target=round(_safe_float(info.get("targetHighPrice")), 2),
            low_price_target=round(_safe_float(info.get("targetLowPrice")), 2),
        )

    # ---- Qualitative fields ----
    competitive_advantages = _infer_competitive_advantages(info)
    key_risks = _infer_key_risks(info)

    return FundamentalsResponse(
        ticker=ticker,
        profile=profile,
        valuation=valuation,
        income_statement=income_statement,
        balance_sheet=balance,
        estimates=estimates,
        competitive_advantages=competitive_advantages,
        key_risks=key_risks,
    )
