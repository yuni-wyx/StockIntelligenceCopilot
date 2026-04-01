from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from langsmith import traceable
from pydantic import BaseModel, Field

try:
    from ..symbols import normalize_symbol
except ImportError:
    from symbols import normalize_symbol


# ── I/O models ───────────────────────────────────────────────────────────────

class EarningsRequest(BaseModel):
    ticker: str
    include_history: bool = True
    history_quarters: int = Field(default=4, ge=1, le=12)


class EarningsEstimate(BaseModel):
    period: str = Field(..., description="Quarter label, e.g. 'Q2 FY2025'.")
    report_date: str
    report_time: str = Field(
        ...,
        description="BMO (before market open) or AMC (after market close).",
    )
    eps_estimate_consensus: float
    eps_estimate_high: float
    eps_estimate_low: float
    revenue_estimate_billions: float
    num_analysts: int


class EarningsResult(BaseModel):
    period: str
    report_date: str
    eps_actual: float
    eps_estimate: float
    eps_surprise: float = Field(..., description="Actual minus estimate.")
    eps_surprise_pct: float
    revenue_actual_billions: float
    revenue_estimate_billions: float
    revenue_surprise_pct: float
    guidance_raised: bool
    post_earnings_move_pct: float = Field(
        ...,
        description="Stock price % change in the session after earnings.",
    )
    key_metrics: Dict[str, Any]
    management_commentary: str


class EarningsResponse(BaseModel):
    ticker: str
    next_earnings: Optional[EarningsEstimate]
    days_to_next_earnings: Optional[int]
    earnings_history: List[EarningsResult]
    avg_eps_surprise_pct: float
    avg_post_earnings_move_pct: float
    beat_rate: float = Field(..., description="Fraction of quarters with positive EPS surprise.")


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


def _normalize_report_time(value: Any) -> str:
    """
    Map Yahoo-style values into BMO / AMC when possible.
    """
    if value is None:
        return "AMC"

    text = str(value).strip().lower()
    if "before" in text or "bmo" in text:
        return "BMO"
    if "after" in text or "amc" in text:
        return "AMC"
    return "AMC"


def _make_period_label(dt_like: Any) -> str:
    try:
        ts = pd.Timestamp(dt_like)
        quarter = ((ts.month - 1) // 3) + 1
        return f"Q{quarter} FY{ts.year}"
    except Exception:
        return "Unknown Quarter"


def _extract_next_earnings_from_calendar(calendar_obj: Any) -> tuple[Optional[str], str]:
    """
    Try to extract next earnings date + report time from yfinance calendar.
    Returns (report_date_iso, report_time_code)
    """
    if calendar_obj is None:
        return None, "AMC"

    try:
        if isinstance(calendar_obj, pd.DataFrame):
            # Often index-based table with columns
            cal = calendar_obj.copy()
            lowered_index = [str(idx).lower() for idx in cal.index]

            report_time = "AMC"
            if "earnings date" in lowered_index:
                row = cal.iloc[lowered_index.index("earnings date")]
                raw = row.iloc[0]
                if isinstance(raw, (list, tuple)) and raw:
                    raw = raw[0]
                dt = pd.Timestamp(raw)
                return dt.date().isoformat(), report_time

            if "ex-dividend date" in lowered_index:
                pass
        elif isinstance(calendar_obj, dict):
            report_time = _normalize_report_time(
                calendar_obj.get("Earnings Call Time") or calendar_obj.get("earningsCallTime")
            )

            raw_date = (
                calendar_obj.get("Earnings Date")
                or calendar_obj.get("earningsDate")
                or calendar_obj.get("Ex-Dividend Date")
            )
            if isinstance(raw_date, (list, tuple)) and raw_date:
                raw_date = raw_date[0]

            if raw_date:
                dt = pd.Timestamp(raw_date)
                return dt.date().isoformat(), report_time
    except Exception:
        pass

    return None, "AMC"


def _extract_revenue_series(yf_ticker: yf.Ticker) -> Dict[str, float]:
    """
    Return revenue by quarter-end date string if available.
    """
    candidates = [
        getattr(yf_ticker, "quarterly_income_stmt", None),
        getattr(yf_ticker, "quarterly_financials", None),
    ]

    for df in candidates:
        try:
            if df is not None and not df.empty:
                possible_rows = ["Total Revenue", "Operating Revenue", "Revenue"]
                for row_name in possible_rows:
                    if row_name in df.index:
                        series = df.loc[row_name]
                        return {
                            pd.Timestamp(idx).date().isoformat(): _safe_float(val)
                            for idx, val in series.items()
                        }
        except Exception:
            continue

    return {}


def _price_move_after_date(yf_ticker: yf.Ticker, report_date: str) -> float:
    """
    Approximate post-earnings move using next available daily close vs prior close.
    """
    try:
        start = pd.Timestamp(report_date) - pd.Timedelta(days=3)
        end = pd.Timestamp(report_date) + pd.Timedelta(days=5)
        hist = yf_ticker.history(
            start=start.date().isoformat(),
            end=end.date().isoformat(),
            interval="1d",
        )
        hist = hist.dropna()
        if len(hist) < 2:
            return 0.0

        closes = hist["Close"].tolist()
        prev_close = closes[0]
        next_close = closes[1]
        if prev_close == 0:
            return 0.0
        return round(((next_close - prev_close) / prev_close) * 100, 2)
    except Exception:
        return 0.0


# ── Core implementation ───────────────────────────────────────────────────────
@traceable(name="earnings_tool", run_type="tool", tags=["tool", "earnings"])
def fetch_earnings(request: EarningsRequest) -> EarningsResponse:
    """
    Real earnings implementation using yfinance.
    """
    ticker = normalize_symbol(request.ticker)
    yf_ticker = yf.Ticker(ticker)
    info = yf_ticker.info or {}

    # ---- Next earnings ----
    next_earnings: Optional[EarningsEstimate] = None
    days_to_next_earnings: Optional[int] = None

    report_date_iso: Optional[str] = None
    report_time = "AMC"

    try:
        report_date_iso, report_time = _extract_next_earnings_from_calendar(yf_ticker.calendar)
    except Exception:
        report_date_iso, report_time = None, "AMC"

    try:
        earnings_dates = yf_ticker.get_earnings_dates(limit=max(request.history_quarters + 4, 8))
    except Exception:
        earnings_dates = pd.DataFrame()

    if report_date_iso is None and earnings_dates is not None and not earnings_dates.empty:
        try:
            future_rows = earnings_dates[earnings_dates.index.date >= date.today()]
            if not future_rows.empty:
                next_idx = future_rows.index[0]
                report_date_iso = pd.Timestamp(next_idx).date().isoformat()
        except Exception:
            pass

    if report_date_iso:
        revenue_est_b = 0.0
        eps_consensus = 0.0
        eps_high = 0.0
        eps_low = 0.0
        num_analysts = 0

        if earnings_dates is not None and not earnings_dates.empty:
            try:
                matched = earnings_dates[
                    earnings_dates.index.date == date.fromisoformat(report_date_iso)
                ]
                if not matched.empty:
                    row = matched.iloc[0]
                    eps_consensus = _safe_float(
                        row.get("EPS Estimate") or row.get("EPS Estimate".lower())
                    )
                    num_analysts = _safe_int(
                        row.get("No. of Analysts") or row.get("numberOfAnalysts")
                    )
            except Exception:
                pass

        # Yahoo often doesn't expose high/low EPS estimate cleanly here; use conservative fallback
        eps_high = round(eps_consensus * 1.08, 2) if eps_consensus else 0.0
        eps_low = round(eps_consensus * 0.92, 2) if eps_consensus else 0.0

        revenue_est_b = round(
            _safe_float(info.get("revenueQuarterlyGrowth")) * 0,
            2,
        )  # placeholder if unavailable
        period = _make_period_label(report_date_iso)
        days_to_next_earnings = (date.fromisoformat(report_date_iso) - date.today()).days

        next_earnings = EarningsEstimate(
            period=period,
            report_date=report_date_iso,
            report_time=report_time,
            eps_estimate_consensus=round(eps_consensus, 2),
            eps_estimate_high=eps_high,
            eps_estimate_low=eps_low,
            revenue_estimate_billions=revenue_est_b,
            num_analysts=num_analysts,
        )

    # ---- Earnings history ----
    earnings_history: List[EarningsResult] = []

    revenue_map = _extract_revenue_series(yf_ticker)

    if request.include_history and earnings_dates is not None and not earnings_dates.empty:
        try:
            hist_rows = earnings_dates[earnings_dates.index.date < date.today()].copy()
            hist_rows = hist_rows.sort_index(ascending=False).head(request.history_quarters)

            for idx, row in hist_rows.iterrows():
                report_date = pd.Timestamp(idx).date().isoformat()
                period = _make_period_label(idx)

                eps_estimate = _safe_float(row.get("EPS Estimate"))
                eps_actual = _safe_float(row.get("Reported EPS"))
                eps_surprise = (
                    round(eps_actual - eps_estimate, 3)
                    if eps_estimate or eps_actual
                    else 0.0
                )
                eps_surprise_pct = (
                    round((eps_surprise / eps_estimate) * 100, 2)
                    if eps_estimate
                    else 0.0
                )

                revenue_actual = revenue_map.get(report_date, 0.0)
                revenue_estimate = revenue_actual
                revenue_surprise_pct = 0.0

                post_move = _price_move_after_date(yf_ticker, report_date)

                earnings_history.append(
                    EarningsResult(
                        period=period,
                        report_date=report_date,
                        eps_actual=round(eps_actual, 2),
                        eps_estimate=round(eps_estimate, 2),
                        eps_surprise=eps_surprise,
                        eps_surprise_pct=eps_surprise_pct,
                        revenue_actual_billions=_to_billions(revenue_actual),
                        revenue_estimate_billions=_to_billions(revenue_estimate),
                        revenue_surprise_pct=revenue_surprise_pct,
                        guidance_raised=False,
                        post_earnings_move_pct=post_move,
                        key_metrics={
                            "source": "yfinance",
                            "reported_eps": round(eps_actual, 2),
                            "eps_estimate": round(eps_estimate, 2),
                        },
                        management_commentary=(
                            "Management commentary not available "
                            "from Yahoo Finance feed."
                        ),
                    )
                )
        except Exception:
            earnings_history = []

    beats = sum(1 for r in earnings_history if r.eps_surprise > 0)
    avg_eps_surprise_pct = (
        round(sum(r.eps_surprise_pct for r in earnings_history) / len(earnings_history), 2)
        if earnings_history else 0.0
    )
    avg_post_earnings_move_pct = (
        round(sum(r.post_earnings_move_pct for r in earnings_history) / len(earnings_history), 2)
        if earnings_history else 0.0
    )
    beat_rate = round(beats / len(earnings_history), 2) if earnings_history else 0.0

    return EarningsResponse(
        ticker=ticker,
        next_earnings=next_earnings,
        days_to_next_earnings=days_to_next_earnings,
        earnings_history=earnings_history,
        avg_eps_surprise_pct=avg_eps_surprise_pct,
        avg_post_earnings_move_pct=avg_post_earnings_move_pct,
        beat_rate=beat_rate,
    )
