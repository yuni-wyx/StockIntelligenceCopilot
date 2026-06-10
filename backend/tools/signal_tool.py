from __future__ import annotations

from pydantic import BaseModel, Field

try:
    from ..schemas.signal import SignalResponse
    from ..services.signal_engine import build_signal_response
    from ..tools.market_data_tool import MarketDataRequest, MarketDataResponse, fetch_market_data
except ImportError:
    from schemas.signal import SignalResponse
    from services.signal_engine import build_signal_response
    from tools.market_data_tool import MarketDataRequest, MarketDataResponse, fetch_market_data


class SignalToolRequest(BaseModel):
    ticker: str
    benchmark: str = "SPY"
    horizon_days: int = Field(default=30, ge=5, le=365)


def _history_from_market_data(response: MarketDataResponse) -> list[dict]:
    return [
        {
            "date": bar.date,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in response.ohlc_history
    ]


def fetch_signal(request: SignalToolRequest) -> SignalResponse:
    lookback_days = max(60, min(max(request.horizon_days, 60), 365))

    ticker_market_data = fetch_market_data(
        MarketDataRequest(
            ticker=request.ticker,
            lookback_days=lookback_days,
            include_technicals=True,
        )
    )
    benchmark_market_data = fetch_market_data(
        MarketDataRequest(
            ticker=request.benchmark,
            lookback_days=lookback_days,
            include_technicals=False,
        )
    )

    return build_signal_response(
        ticker=ticker_market_data.ticker,
        benchmark=benchmark_market_data.ticker,
        horizon_days=request.horizon_days,
        ticker_history=_history_from_market_data(ticker_market_data),
        benchmark_history=_history_from_market_data(benchmark_market_data),
    )
