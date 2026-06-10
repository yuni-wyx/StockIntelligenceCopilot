from __future__ import annotations

import math
from statistics import pstdev
from typing import Any, Mapping

try:
    from ..schemas.signal import (
        SignalComponent,
        SignalFeatureSnapshot,
        SignalResponse,
    )
except ImportError:
    from schemas.signal import SignalComponent, SignalFeatureSnapshot, SignalResponse


DISCLAIMER = (
    "This signal estimates benchmark-relative strength using transparent market "
    "features. It is not a price prediction or financial advice."
)


def round2(value: float | None) -> float | None:
    if value is None or math.isnan(value):
        return None
    return round(value, 2)


def _history_date_key(record: Mapping[str, Any]) -> Any:
    return record.get("date") or record.get("timestamp") or ""


def _normalize_history(history: list[Mapping[str, Any]]) -> list[dict[str, float | str | None]]:
    normalized: list[dict[str, float | str | None]] = []
    for record in sorted(history, key=_history_date_key):
        close = record.get("close")
        if close is None:
            continue
        normalized.append(
            {
                "date": str(record.get("date") or record.get("timestamp") or ""),
                "close": float(close),
                "volume": (
                    None
                    if record.get("volume") is None
                    else float(record["volume"])
                ),
            }
        )
    return normalized


def _latest_close(history: list[dict[str, float | str | None]]) -> float | None:
    if not history:
        return None
    close = history[-1]["close"]
    return None if close is None else float(close)


def _return_pct(history: list[dict[str, float | str | None]], periods: int) -> float | None:
    if len(history) <= periods:
        return None
    current = float(history[-1]["close"])
    prior = float(history[-(periods + 1)]["close"])
    if prior == 0:
        return None
    return ((current / prior) - 1) * 100


def _sma(history: list[dict[str, float | str | None]], periods: int) -> float | None:
    if len(history) < periods:
        return None
    closes = [float(item["close"]) for item in history[-periods:]]
    return sum(closes) / periods


def _price_vs_sma20_pct(history: list[dict[str, float | str | None]]) -> float | None:
    current = _latest_close(history)
    sma20 = _sma(history, 20)
    if current is None or sma20 in {None, 0}:
        return None
    return ((current / sma20) - 1) * 100


def _sma20_vs_sma50_pct(history: list[dict[str, float | str | None]]) -> float | None:
    sma20 = _sma(history, 20)
    sma50 = _sma(history, 50)
    if sma20 is None or sma50 in {None, 0}:
        return None
    return ((sma20 / sma50) - 1) * 100


def _daily_returns(history: list[dict[str, float | str | None]], periods: int) -> list[float]:
    if len(history) < periods + 1:
        return []
    window = history[-(periods + 1) :]
    returns: list[float] = []
    for prev, current in zip(window, window[1:]):
        prev_close = float(prev["close"])
        curr_close = float(current["close"])
        if prev_close == 0:
            continue
        returns.append((curr_close / prev_close) - 1)
    return returns


def _realized_volatility_20d(history: list[dict[str, float | str | None]]) -> float | None:
    returns = _daily_returns(history, 20)
    if len(returns) < 2:
        return None
    return pstdev(returns) * math.sqrt(252) * 100


def _drawdown_from_60d_high_pct(history: list[dict[str, float | str | None]]) -> float | None:
    if len(history) < 60:
        return None
    window = history[-60:]
    high = max(float(item["close"]) for item in window)
    current = float(window[-1]["close"])
    if high == 0:
        return None
    return ((current / high) - 1) * 100


def _volume_ratio_5d_20d(history: list[dict[str, float | str | None]]) -> float | None:
    recent = history[-5:]
    medium = history[-20:]
    if len(recent) < 5 or len(medium) < 20:
        return None
    recent_volumes = [item["volume"] for item in recent if item["volume"] is not None]
    medium_volumes = [item["volume"] for item in medium if item["volume"] is not None]
    if len(recent_volumes) < 5 or len(medium_volumes) < 20:
        return None
    medium_avg = sum(float(value) for value in medium_volumes) / 20
    if medium_avg == 0:
        return None
    recent_avg = sum(float(value) for value in recent_volumes) / 5
    return recent_avg / medium_avg


def _score_relative_return(relative_return_20d: float | None) -> tuple[float, str]:
    if relative_return_20d is None:
        return 0.0, "Relative benchmark return was unavailable."
    if relative_return_20d >= 10:
        return 15.0, "20-day return materially outperformed the benchmark."
    if relative_return_20d >= 5:
        return 10.0, "20-day return outperformed the benchmark."
    if relative_return_20d >= 1:
        return 6.0, "20-day return modestly outperformed the benchmark."
    if relative_return_20d > -1:
        return 0.0, "20-day return was broadly in line with the benchmark."
    if relative_return_20d > -5:
        return -6.0, "20-day return modestly lagged the benchmark."
    if relative_return_20d > -10:
        return -10.0, "20-day return lagged the benchmark."
    return -15.0, "20-day return materially lagged the benchmark."


def _score_price_vs_sma20(price_vs_sma20_pct: float | None) -> tuple[float, str]:
    if price_vs_sma20_pct is None:
        return 0.0, "Price versus SMA20 was unavailable."
    if price_vs_sma20_pct >= 5:
        return 8.0, "Price is decisively above the 20-day moving average."
    if price_vs_sma20_pct >= 1:
        return 5.0, "Price is above the 20-day moving average."
    if price_vs_sma20_pct > -1:
        return 0.0, "Price is near the 20-day moving average."
    if price_vs_sma20_pct > -5:
        return -5.0, "Price is below the 20-day moving average."
    return -8.0, "Price is materially below the 20-day moving average."


def _score_sma20_vs_sma50(sma20_vs_sma50_pct: float | None) -> tuple[float, str]:
    if sma20_vs_sma50_pct is None:
        return 0.0, "SMA20 versus SMA50 was unavailable."
    if sma20_vs_sma50_pct >= 3:
        return 8.0, "Short-to-medium trend remains firmly positive."
    if sma20_vs_sma50_pct >= 0:
        return 4.0, "Short-to-medium trend remains positive."
    if sma20_vs_sma50_pct > -3:
        return -4.0, "Short-to-medium trend has softened."
    return -8.0, "Short-to-medium trend is negative."


def _score_return_5d(ticker_return_5d: float | None) -> tuple[float, str]:
    if ticker_return_5d is None:
        return 0.0, "5-day return was unavailable."
    if ticker_return_5d >= 3:
        return 4.0, "Short-term momentum is positive."
    if ticker_return_5d >= 1:
        return 2.0, "Short-term momentum is mildly positive."
    if ticker_return_5d > -1:
        return 0.0, "Short-term momentum is neutral."
    if ticker_return_5d > -3:
        return -2.0, "Short-term momentum is mildly negative."
    return -4.0, "Short-term momentum is negative."


def _score_volatility(realized_volatility_20d: float | None) -> tuple[float, str]:
    if realized_volatility_20d is None:
        return 0.0, "Realized volatility was unavailable."
    if realized_volatility_20d < 20:
        return 0.0, "Volatility remains controlled."
    if realized_volatility_20d < 35:
        return -2.0, "Volatility is somewhat elevated."
    if realized_volatility_20d < 50:
        return -5.0, "Volatility is elevated."
    return -8.0, "Volatility is very elevated."


def _score_drawdown(drawdown_from_60d_high_pct: float | None) -> tuple[float, str]:
    if drawdown_from_60d_high_pct is None:
        return 0.0, "Drawdown from recent high was unavailable."
    if drawdown_from_60d_high_pct >= -5:
        return 0.0, "Drawdown remains shallow."
    if drawdown_from_60d_high_pct >= -10:
        return -3.0, "Drawdown is noticeable but contained."
    if drawdown_from_60d_high_pct >= -20:
        return -7.0, "Drawdown is meaningful."
    return -12.0, "Drawdown is deep."


def _score_volume_confirmation(
    volume_ratio_5d_20d: float | None,
    ticker_return_20d: float | None,
) -> tuple[float, str]:
    if volume_ratio_5d_20d is None or ticker_return_20d is None:
        return 0.0, "Volume confirmation was unavailable."
    if ticker_return_20d > 0 and volume_ratio_5d_20d >= 1.1:
        return 4.0, "Positive move is supported by stronger recent volume."
    if ticker_return_20d > 0 and volume_ratio_5d_20d < 0.9:
        return -2.0, "Positive move lacked strong volume confirmation."
    if ticker_return_20d < 0 and volume_ratio_5d_20d >= 1.1:
        return -3.0, "Negative move is confirmed by heavier recent volume."
    return 0.0, "Volume was not a major confirming signal."


def _component_direction(contribution: float) -> str:
    if contribution > 0:
        return "positive"
    if contribution < 0:
        return "negative"
    return "neutral"


def _band_from_score(score: float) -> str:
    if score < 40:
        return "Weak"
    if score < 60:
        return "Neutral"
    return "Strong"


def _confidence_from_inputs(
    *,
    ticker_history_len: int,
    benchmark_history_len: int,
    missing_volume: bool,
    missing_core_features: int,
    positive_components: int,
    negative_components: int,
    score: float,
) -> str:
    confidence = "High"
    if ticker_history_len < 60 or benchmark_history_len < 60:
        confidence = "Medium"
    if ticker_history_len < 50 or benchmark_history_len < 50:
        confidence = "Low"
    if missing_volume and confidence == "High":
        confidence = "Medium"
    if missing_core_features >= 2:
        confidence = "Medium" if confidence == "High" else "Low"
    mixed_signals = positive_components >= 2 and negative_components >= 2 and 40 <= score < 60
    if mixed_signals:
        confidence = "Medium" if confidence == "High" else "Low"
    elif positive_components >= 2 and negative_components >= 2 and confidence == "High":
        confidence = "Medium"
    return confidence


def _collect_caveats(
    *,
    ticker_history_len: int,
    benchmark_history_len: int,
    missing_volume: bool,
    positive_components: int,
    negative_components: int,
    score: float,
) -> list[str]:
    caveats = [
        "This is a heuristic signal estimate, not a calibrated probability."
    ]
    if missing_volume:
        caveats.append("Volume confirmation was unavailable.")
    if ticker_history_len < 60:
        caveats.append(
            "History length was shorter than ideal for medium-term trend confirmation."
        )
    if benchmark_history_len < 60:
        caveats.append(
            "Benchmark history was shorter than ideal for relative signal confirmation."
        )
    if positive_components >= 2 and negative_components >= 2 and 40 <= score < 60:
        caveats.append(
            "Signals were mixed across momentum, trend, and drawdown features."
        )
    return caveats


def build_signal_response(
    *,
    ticker: str,
    benchmark: str = "SPY",
    horizon_days: int = 30,
    ticker_history: list[Mapping[str, Any]],
    benchmark_history: list[Mapping[str, Any]],
) -> SignalResponse:
    normalized_ticker_history = _normalize_history(ticker_history)
    normalized_benchmark_history = _normalize_history(benchmark_history)

    if len(normalized_ticker_history) < 20:
        raise ValueError("Insufficient ticker history. Need at least 20 records.")
    if len(normalized_benchmark_history) < 20:
        raise ValueError("Insufficient benchmark history. Need at least 20 records.")

    feature_snapshot = SignalFeatureSnapshot(
        ticker_return_5d=round2(_return_pct(normalized_ticker_history, 5)),
        ticker_return_20d=round2(_return_pct(normalized_ticker_history, 20)),
        benchmark_return_20d=round2(_return_pct(normalized_benchmark_history, 20)),
        price_vs_sma20_pct=round2(_price_vs_sma20_pct(normalized_ticker_history)),
        sma20_vs_sma50_pct=round2(_sma20_vs_sma50_pct(normalized_ticker_history)),
        realized_volatility_20d=round2(_realized_volatility_20d(normalized_ticker_history)),
        drawdown_from_60d_high_pct=round2(
            _drawdown_from_60d_high_pct(normalized_ticker_history)
        ),
        volume_ratio_5d_20d=round2(_volume_ratio_5d_20d(normalized_ticker_history)),
    )
    if (
        feature_snapshot.ticker_return_20d is not None
        and feature_snapshot.benchmark_return_20d is not None
    ):
        feature_snapshot.relative_return_20d = round2(
            feature_snapshot.ticker_return_20d
            - feature_snapshot.benchmark_return_20d
        )

    score_rules = [
        (
            "relative_return_20d",
            *_score_relative_return(feature_snapshot.relative_return_20d),
        ),
        (
            "price_vs_sma20_pct",
            *_score_price_vs_sma20(feature_snapshot.price_vs_sma20_pct),
        ),
        (
            "sma20_vs_sma50_pct",
            *_score_sma20_vs_sma50(feature_snapshot.sma20_vs_sma50_pct),
        ),
        ("ticker_return_5d", *_score_return_5d(feature_snapshot.ticker_return_5d)),
        (
            "realized_volatility_20d",
            *_score_volatility(feature_snapshot.realized_volatility_20d),
        ),
        (
            "drawdown_from_60d_high_pct",
            *_score_drawdown(feature_snapshot.drawdown_from_60d_high_pct),
        ),
        (
            "volume_confirmation",
            *_score_volume_confirmation(
                feature_snapshot.volume_ratio_5d_20d,
                feature_snapshot.ticker_return_20d,
            ),
        ),
    ]

    components = [
        SignalComponent(
            name=name,
            contribution=round2(contribution) or 0.0,
            direction=_component_direction(contribution),
            summary=summary,
        )
        for name, contribution, summary in score_rules
    ]

    raw_score = 50 + sum(component.contribution for component in components)
    signal_score = max(0.0, min(100.0, round(raw_score, 2)))
    positive_components = sum(1 for component in components if component.contribution > 0)
    negative_components = sum(1 for component in components if component.contribution < 0)
    missing_core_features = sum(
        1
        for value in (
            feature_snapshot.relative_return_20d,
            feature_snapshot.price_vs_sma20_pct,
            feature_snapshot.sma20_vs_sma50_pct,
            feature_snapshot.realized_volatility_20d,
            feature_snapshot.drawdown_from_60d_high_pct,
        )
        if value is None
    )
    missing_volume = feature_snapshot.volume_ratio_5d_20d is None

    confidence = _confidence_from_inputs(
        ticker_history_len=len(normalized_ticker_history),
        benchmark_history_len=len(normalized_benchmark_history),
        missing_volume=missing_volume,
        missing_core_features=missing_core_features,
        positive_components=positive_components,
        negative_components=negative_components,
        score=signal_score,
    )
    caveats = _collect_caveats(
        ticker_history_len=len(normalized_ticker_history),
        benchmark_history_len=len(normalized_benchmark_history),
        missing_volume=missing_volume,
        positive_components=positive_components,
        negative_components=negative_components,
        score=signal_score,
    )

    positive_signals = [
        component.summary
        for component in components
        if component.direction == "positive"
    ]
    negative_signals = [
        component.summary
        for component in components
        if component.direction == "negative"
    ]

    return SignalResponse(
        ticker=ticker,
        benchmark=benchmark,
        horizon_days=horizon_days,
        signal_score=signal_score,
        signal_band=_band_from_score(signal_score),
        confidence=confidence,
        positive_signals=positive_signals,
        negative_signals=negative_signals,
        data_caveats=caveats,
        disclaimer=DISCLAIMER,
        feature_snapshot=feature_snapshot,
        components=components,
    )
