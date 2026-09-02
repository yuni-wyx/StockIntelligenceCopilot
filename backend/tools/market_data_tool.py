"""
Market Data Tool
-----------------
Returns intraday / daily price/volume/technicals for a ticker.
Mock implementation — replace fetch_market_data() with real API calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf
from langsmith import traceable
from pydantic import BaseModel, Field

try:
    from ..config import PROVIDER_TIMEOUT_SECONDS
    from ..services.yfinance_timeout import configure_yfinance_timeout
    from ..symbols import detect_market, normalize_symbol
except ImportError:
    from config import PROVIDER_TIMEOUT_SECONDS
    from services.yfinance_timeout import configure_yfinance_timeout
    from symbols import detect_market, normalize_symbol


# ── I/O models ───────────────────────────────────────────────────────────────

class MarketDataRequest(BaseModel):
    ticker: str
    lookback_days: int = Field(default=30, ge=1, le=365)
    include_technicals: bool = True


class OHLCBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float


class TechnicalIndicators(BaseModel):
    rsi_14: float | None = Field(None, description="14-day RSI (0–100).")
    sma_20: float | None = None
    sma_50: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None
    atr_14: float | None = Field(None, description="14-day Average True Range.")


class MarketDataResponse(BaseModel):
    ticker: str
    market: str
    as_of: str
    current_price: float
    price_change_1d: float
    price_change_pct_1d: float
    price_change_1w: float
    price_change_pct_1w: float
    price_change_1m: float
    price_change_pct_1m: float
    volume_today: int
    avg_volume_30d: int
    volume_ratio: float = Field(..., description="Today volume / 30-day avg.")
    market_cap_billions: float | None
    beta: float | None
    week_52_high: float | None
    week_52_low: float | None
    ohlc_history: List[OHLCBar]
    technicals: TechnicalIndicators | None
    data_caveats: List[str] = Field(default_factory=list)


# ── Mock data registry ───────────────────────────────────────────────────────

_TICKER_SEEDS: Dict[str, Dict[str, Any]] = {
    "NVDA": {"base_price": 875.0,  "mcap": 2150.0, "beta": 1.72, "52h": 974.0,  "52l": 402.0},
    "TSLA": {"base_price": 185.0,  "mcap": 588.0,  "beta": 2.31, "52h": 299.0,  "52l": 138.0},
    "AAPL": {"base_price": 189.0,  "mcap": 2940.0, "beta": 1.23, "52h": 199.6,  "52l": 164.1},
    "MSFT": {"base_price": 415.0,  "mcap": 3080.0, "beta": 0.89, "52h": 468.4,  "52l": 309.5},
    "AMZN": {"base_price": 190.0,  "mcap": 2000.0, "beta": 1.31, "52h": 201.2,  "52l": 118.4},
    "META": {"base_price": 510.0,  "mcap": 1300.0, "beta": 1.44, "52h": 544.8,  "52l": 279.4},
    "GOOGL": {"base_price": 175.0, "mcap": 2180.0, "beta": 1.05, "52h": 196.0,  "52l": 130.7},
}

_DEFAULT_SEED = {"base_price": 100.0, "mcap": 50.0, "beta": 1.10, "52h": 130.0, "52l": 70.0}


def _seed_for(ticker: str) -> Dict[str, Any]:
    return _TICKER_SEEDS.get(ticker.upper(), _DEFAULT_SEED)


def _read_live_price(yf_ticker: yf.Ticker) -> float | None:
    """Read Yahoo's latest quote without treating a history close as live."""
    try:
        fast_info = yf_ticker.fast_info
        raw_price = (
            fast_info.get("last_price")
            if isinstance(fast_info, dict)
            else getattr(fast_info, "last_price", None)
        )
        price = float(raw_price) if raw_price is not None else None
        return round(price, 2) if price is not None and price > 0 else None
    except (AttributeError, TypeError, ValueError, KeyError):
        return None


# ── Core mock implementation ─────────────────────────────────────────────────
@traceable(name="market_data_tool", run_type="tool", tags=["tool", "market-data"])
def fetch_market_data(request: MarketDataRequest) -> MarketDataResponse:
    """
    Real market data implementation using Yahoo Finance (yfinance).
    """
    ticker = normalize_symbol(request.ticker)
    market = detect_market(ticker)
    yf_ticker = yf.Ticker(ticker)
    configure_yfinance_timeout(yf_ticker, PROVIDER_TIMEOUT_SECONDS)

    hist = yf_ticker.history(
        period="3mo",
        interval="1d",
        timeout=PROVIDER_TIMEOUT_SECONDS,
    )

    if hist.empty:
        raise ValueError(f"No data found for ticker {ticker}")

    hist = hist.dropna()

    # Prefer Yahoo's latest quote. The history close is only a fallback and is
    # explicitly labelled as such in data_caveats below.
    live_price = _read_live_price(yf_ticker)
    current = live_price if live_price is not None else round(hist["Close"].iloc[-1], 2)
    prev_close = round(hist["Close"].iloc[-2], 2)

    change_1d = round(current - prev_close, 2)
    change_pct_1d = round((change_1d / prev_close) * 100, 2)

    close_1w = hist["Close"].iloc[-5]
    change_1w = round(current - close_1w, 2)
    change_pct_1w = round((change_1w / close_1w) * 100, 2)

    close_1m = hist["Close"].iloc[0]
    change_1m = round(current - close_1m, 2)
    change_pct_1m = round((change_1m / close_1m) * 100, 2)

    vol_today = int(hist["Volume"].iloc[-1])
    avg_vol_30 = int(hist["Volume"].tail(30).mean())
    vol_ratio = round(vol_today / avg_vol_30, 2) if avg_vol_30 else 1.0

    # OHLC history
    ohlc = []
    for idx, row in hist.tail(request.lookback_days).iterrows():
        ohlc.append(OHLCBar(
            date=idx.date().isoformat(),
            open=round(row["Open"], 2),
            high=round(row["High"], 2),
            low=round(row["Low"], 2),
            close=round(row["Close"], 2),
            volume=int(row["Volume"]),
            vwap=round((row["High"] + row["Low"] + row["Close"]) / 3, 2),
        ))

    # Info (fundamental-lite)
    info = yf_ticker.info

    market_cap_raw = info.get("marketCap")
    market_cap = float(market_cap_raw) / 1e9 if market_cap_raw is not None else None
    beta = info.get("beta")
    week_52_high = info.get("fiftyTwoWeekHigh")
    week_52_low = info.get("fiftyTwoWeekLow")

    # Simple technicals
    closes = hist["Close"].tail(50)

    sma_20 = round(closes.tail(20).mean(), 2)
    sma_50 = round(closes.mean(), 2)

    ema_12 = round(closes.ewm(span=12).mean().iloc[-1], 2)
    ema_26 = round(closes.ewm(span=26).mean().iloc[-1], 2)

    macd = round(ema_12 - ema_26, 2)
    macd_signal = round(
        closes.ewm(span=12).mean().iloc[-1] - closes.ewm(span=26).mean().iloc[-1], 2
    )

    deltas = closes.diff().dropna()
    gains = deltas.clip(lower=0).rolling(14).mean()
    losses = (-deltas.clip(upper=0)).rolling(14).mean()
    rs = gains / losses.replace(0, float("nan"))
    rsi_value = 100 - (100 / (1 + rs.iloc[-1])) if not rs.empty and pd.notna(rs.iloc[-1]) else None

    true_range = pd.concat(
        [
            hist["High"] - hist["Low"],
            (hist["High"] - hist["Close"].shift()).abs(),
            (hist["Low"] - hist["Close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_raw = true_range.rolling(14).mean().iloc[-1]
    atr = round(float(atr_raw), 2) if pd.notna(atr_raw) else None

    bb_upper = round(sma_20 + 2 * atr, 2) if atr is not None else None
    bb_lower = round(sma_20 - 2 * atr, 2) if atr is not None else None

    technicals = TechnicalIndicators(
        rsi_14=round(float(rsi_value), 2) if rsi_value is not None else None,
        sma_20=sma_20,
        sma_50=sma_50,
        ema_12=ema_12,
        ema_26=ema_26,
        macd=macd,
        macd_signal=macd_signal,
        bollinger_upper=bb_upper,
        bollinger_lower=bb_lower,
        atr_14=atr,
    ) if request.include_technicals else None

    quote_caveat = (
        "Latest quote returned by Yahoo Finance; quote may be exchange-delayed."
        if live_price is not None
        else "Live quote was unavailable; current price uses the latest daily Yahoo Finance close."
    )
    return MarketDataResponse(
        ticker=ticker,
        market=market,
        as_of=(
            datetime.now(timezone.utc).isoformat()
            if live_price is not None
            else hist.index[-1].to_pydatetime().astimezone(timezone.utc).isoformat()
        ),
        current_price=current,
        price_change_1d=change_1d,
        price_change_pct_1d=change_pct_1d,
        price_change_1w=change_1w,
        price_change_pct_1w=change_pct_1w,
        price_change_1m=change_1m,
        price_change_pct_1m=change_pct_1m,
        volume_today=vol_today,
        avg_volume_30d=avg_vol_30,
        volume_ratio=vol_ratio,
        market_cap_billions=round(market_cap, 2) if market_cap is not None else None,
        beta=float(beta) if beta is not None else None,
        week_52_high=float(week_52_high) if week_52_high is not None else None,
        week_52_low=float(week_52_low) if week_52_low is not None else None,
        ohlc_history=ohlc,
        technicals=technicals,
        data_caveats=[
            quote_caveat,
            *(
                ["Market capitalization, beta, or 52-week range was unavailable."]
                if market_cap is None
                or beta is None
                or week_52_high is None
                or week_52_low is None
                else []
            ),
        ],
    )
