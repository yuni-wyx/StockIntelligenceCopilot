"""
Synthesis Chain
----------------
Stage 6 (final) of the pipeline.

Input  : AggregatedEvidence + ExecutionPlan
Output : One of
         - StockResearchOutput
         - PriceMovementOutput
         - WatchlistMonitorOutput
         - TradingDecisionOutput

Synthesises all tool evidence into structured, human-readable reports.
Research / explain / watchlist remain deterministic.
Trade mode uses an LLM to produce a structured trading decision.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, List, Tuple

from langchain_core.runnables import RunnableLambda

try:
    from ..schemas.evidence_schema import AggregatedEvidence
    from ..schemas.intent_schema import AnalysisMode
    from ..schemas.output_schema import (
        PriceMovementOutput,
        RankedCause,
        StockResearchOutput,
        TickerWeeklySummary,
        TradingDecisionOutput,
        WatchlistMonitorOutput,
        WatchPoint,
    )
    from ..schemas.planner_schema import ExecutionPlan
except ImportError:
    from schemas.evidence_schema import AggregatedEvidence
    from schemas.intent_schema import AnalysisMode
    from schemas.output_schema import (
        PriceMovementOutput,
        RankedCause,
        StockResearchOutput,
        TickerWeeklySummary,
        TradingDecisionOutput,
        WatchlistMonitorOutput,
        WatchPoint,
    )
    from schemas.planner_schema import ExecutionPlan

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _sentiment_label(score: float) -> str:
    if score > 0.2:
        return "BULLISH"
    if score < -0.2:
        return "BEARISH"
    return "NEUTRAL"


def _confidence_label(conf: float) -> str:
    if conf >= 0.75:
        return "HIGH"
    if conf >= 0.45:
        return "MEDIUM"
    return "LOW"


def _momentum_label(pct_1w: float) -> str:
    if pct_1w >= 5:
        return "STRONG_UP"
    if pct_1w >= 1.5:
        return "UP"
    if pct_1w <= -5:
        return "STRONG_DOWN"
    if pct_1w <= -1.5:
        return "DOWN"
    return "FLAT"


def _safe_confidence_int(value: Any) -> int:
    try:
        conf = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, conf))


def _llm_trade_synthesis_enabled() -> bool:
    return os.getenv("ENABLE_LLM_TRADE_SYNTHESIS", "").strip().lower() in {"1", "true", "yes", "on"}


def _heuristic_trade_decision(
    ticker: str,
    ev,
    error_note: str | None = None,
) -> TradingDecisionOutput:
    md = ev.market_data if ev and ev.market_data else {}
    fundamentals = ev.fundamentals if ev and ev.fundamentals else {}
    earnings = ev.earnings if ev and ev.earnings else {}
    news = ev.news if ev and ev.news else []

    current = float(md.get("current_price", 0) or 0)
    day_move = float(md.get("price_change_pct_1d", 0) or 0)
    month_move = float(md.get("price_change_pct_1m", 0) or 0)
    atr = float(((md.get("technicals") or {}).get("atr_14", 0)) or 0)
    risk_buffer = atr if atr > 0 else (current * 0.05 if current > 0 else 0)
    reward_buffer = max(risk_buffer * 1.8, current * 0.08 if current > 0 else 0)

    positive_news = sum(1 for article in news if article.get("sentiment") == "positive")
    negative_news = sum(1 for article in news if article.get("sentiment") == "negative")

    score = 0.0
    if month_move > 3:
        score += 1.0
    elif month_move < -3:
        score -= 1.0
    if day_move > 0.5:
        score += 0.5
    elif day_move < -0.5:
        score -= 0.5
    score += min(positive_news, 2) * 0.25
    score -= min(negative_news, 2) * 0.25

    if score >= 0.75:
        bias = "Bullish"
    elif score <= -0.75:
        bias = "Bearish"
    else:
        bias = "Neutral"

    if current > 0:
        buy_zone = f"Current reference: ${current:.2f}"
        stop_loss = f"${max(current - risk_buffer, 0):.2f}"
        take_profit = f"${current + reward_buffer:.2f}"
    else:
        buy_zone = "Current price unavailable"
        stop_loss = "Risk review required"
        take_profit = "Upside target pending"

    confidence = 35
    if md:
        confidence += 10
    if fundamentals:
        confidence += 10
    if news:
        confidence += 5
    if earnings:
        confidence += 5
    confidence = max(20, min(65, confidence))

    reasoning: List[str] = []
    if current > 0:
        reasoning.append(f"Fallback setup anchored to the latest retrieved price (${current:.2f}).")
    if month_move or day_move:
        reasoning.append(
            "Recent momentum snapshot: "
            f"{_fmt_pct(day_move)} on the day and "
            f"{_fmt_pct(month_move)} over one month."
        )
    if fundamentals.get("competitive_advantages"):
        reasoning.append(f"Fundamental support: {fundamentals['competitive_advantages'][0]}.")
    if earnings.get("days_to_next_earnings") is not None:
        reasoning.append(
            "Earnings timing remains relevant: "
            f"~{earnings['days_to_next_earnings']} days to next report."
        )
    if error_note:
        reasoning.append(error_note)

    return TradingDecisionOutput(
        ticker=ticker,
        generated_at=datetime.utcnow(),
        bias=bias,
        buy_zone=buy_zone,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=confidence,
        reasoning=reasoning,
    )


# ── Mode 1: Stock Research ────────────────────────────────────────────────────

def _synthesise_research(
    evidence: AggregatedEvidence, plan: ExecutionPlan
) -> StockResearchOutput:
    ticker = plan.tickers[0]
    ev = evidence.get_ticker(ticker)

    if ev and ev.fundamentals:
        f = ev.fundamentals
        profile = f.get("profile", {})
        val = f.get("valuation", {})
        inc = f.get("income_statement", {})
        adv = f.get("competitive_advantages", [])

        fund_summary = (
            f"{profile.get('name', ticker)} ({ticker}) operates in the "
            f"{profile.get('sector', 'N/A')} sector. "
            f"Revenue: ${inc.get('revenue_billions', 0):.1f}B "
            f"({_fmt_pct(inc.get('revenue_growth_yoy', 0) * 100)} YoY). "
            f"Net margin: {inc.get('net_margin', 0) * 100:.1f}%. "
            f"Forward P/E: {val.get('pe_forward', 'N/A')}x. "
            f"Key strength: {adv[0] if adv else 'N/A'}."
        )
    else:
        fund_summary = f"Fundamental data unavailable for {ticker}."

    if ev and ev.news:
        headlines = [a.get("title", "") for a in ev.news[:3]]
        news_summary = "Top recent headlines: " + " | ".join(headlines)
        scores = [a.get("sentiment_score", 0) for a in ev.news]
        avg_score = sum(scores) / len(scores) if scores else 0
    else:
        news_summary = "No recent news data available."
        avg_score = 0.0

    bull_points: List[str] = []
    if ev and ev.fundamentals:
        adv = ev.fundamentals.get("competitive_advantages", [])
        bull_points.extend(adv[:2])

    if ev and ev.market_data:
        md = ev.market_data
        if md.get("price_change_pct_1m", 0) > 0:
            bull_points.append(
                f"Strong 1-month momentum ({_fmt_pct(md['price_change_pct_1m'])})"
            )
        if md.get("volume_ratio", 1) > 1.3:
            bull_points.append("Above-average volume confirms buying interest")

    if ev and ev.earnings:
        beat_rate = ev.earnings.get("beat_rate", 0)
        if beat_rate >= 0.75:
            bull_points.append(
                f"Strong earnings track record ({beat_rate * 100:.0f}% beat rate)"
            )

    bull_case = (
        "BULL CASE: " + "; ".join(bull_points)
        if bull_points
        else "Insufficient data for bull case."
    )

    bear_points: List[str] = []
    if ev and ev.fundamentals:
        risks = ev.fundamentals.get("key_risks", [])
        bear_points.extend(risks[:2])

    if ev and ev.market_data:
        md = ev.market_data
        if md.get("technicals"):
            rsi = md["technicals"].get("rsi_14", 50)
            if rsi > 70:
                bear_points.append(f"Technically overbought (RSI: {rsi:.0f})")

    if ev and ev.news:
        neg = [a for a in ev.news if a.get("sentiment") == "negative"]
        if neg:
            bear_points.append(f"{len(neg)} negative news articles in recent coverage")

    bear_case = (
        "BEAR CASE: " + "; ".join(bear_points)
        if bear_points
        else "Insufficient data for bear case."
    )

    watch_points: List[WatchPoint] = []

    if ev and ev.earnings and ev.earnings.get("next_earnings"):
        ne = ev.earnings["next_earnings"]
        days = ev.earnings.get("days_to_next_earnings", "?")
        watch_points.append(
            WatchPoint(
                item=f"Earnings Report ({ne.get('period', 'next quarter')})",
                reason="Potential catalyst for significant price movement",
                timeframe=f"~{days} days",
            )
        )

    if ev and ev.market_data:
        rsi = (ev.market_data.get("technicals") or {}).get("rsi_14", 50)
        if rsi > 65 or rsi < 35:
            watch_points.append(
                WatchPoint(
                    item="RSI Reversal Signal",
                    reason=(
                        f"RSI at {rsi:.0f} suggests "
                        f"{'overbought' if rsi > 65 else 'oversold'} condition"
                    ),
                    timeframe="1–2 weeks",
                )
            )

    watch_points.append(
        WatchPoint(
            item="Macro data releases (CPI, Fed decisions)",
            reason="Broad market risk-on/risk-off shifts the sector",
            timeframe="Rolling",
        )
    )

    sentiment = _sentiment_label(avg_score)

    return StockResearchOutput(
        ticker=ticker,
        generated_at=datetime.utcnow(),
        fundamental_summary=fund_summary,
        recent_news_summary=news_summary,
        bull_case=bull_case,
        bear_case=bear_case,
        what_to_watch_next=watch_points,
        overall_sentiment=sentiment,
    )


# ── Mode 2: Price Movement Explanation ───────────────────────────────────────

def _synthesise_price_movement(
    evidence: AggregatedEvidence, plan: ExecutionPlan
) -> PriceMovementOutput:
    ticker = plan.tickers[0]
    ev = evidence.get_ticker(ticker)

    md = ev.market_data if ev else {}
    price_pct = md.get("price_change_pct_1d", 0.0) if md else 0.0
    price_chg = md.get("price_change_1d", 0.0) if md else 0.0
    current = md.get("current_price", 0.0) if md else 0.0
    vol_ratio = md.get("volume_ratio", 1.0) if md else 1.0

    move_direction = "rallied" if price_pct >= 0 else "declined"
    volume_label = (
        "strong conviction"
        if vol_ratio > 1.5
        else "moderate participation"
        if vol_ratio > 1.0
        else "light volume, possible noise"
    )
    vol_context = (
        f"Volume was {vol_ratio:.1f}x the 30-day average, suggesting "
        f"{volume_label}."
    )

    price_move_summary = (
        f"{ticker} {move_direction} {_fmt_pct(price_pct)} "
        f"(${price_chg:+.2f}) to ${current:.2f}. {vol_context}"
    )

    candidates: List[Tuple[str, str, List[str], float]] = []

    if ev and ev.news:
        high_rel = [a for a in ev.news if a.get("relevance_score", 0) > 0.8]
        if high_rel:
            top = high_rel[0]
            conf = min(0.92, 0.6 + abs(top.get("sentiment_score", 0)) * 0.35)
            candidates.append(
                (
                    "News catalyst",
                    f"High-relevance news: '{top['title']}'",
                    [
                        f"Source: {top['source']}",
                        f"Sentiment score: {top['sentiment_score']:+.2f}",
                        top.get("summary", "")[:120],
                    ],
                    conf,
                )
            )

    if ev and ev.earnings:
        days = ev.earnings.get("days_to_next_earnings")
        if days is not None and days <= 14:
            candidates.append(
                (
                    "Pre-earnings positioning",
                    "Earnings are "
                    f"{days} days away; traders often position aggressively "
                    "in the week prior.",
                    [
                        "Next report: "
                        f"{ev.earnings.get('next_earnings', {}).get('period', 'N/A')}",
                        "Avg post-earnings move: "
                        f"{ev.earnings.get('avg_post_earnings_move_pct', 0):+.1f}%",
                    ],
                    0.65,
                )
            )

    if md and md.get("technicals"):
        tech = md["technicals"]
        rsi = tech.get("rsi_14", 50)
        macd = tech.get("macd", 0)
        tech_conf = 0.40
        if (price_pct > 0 and macd > 0) or (price_pct < 0 and macd < 0):
            tech_conf = 0.55
        candidates.append(
            (
                "Technical / momentum",
                "Price action aligns with short-term technical indicators.",
                [f"RSI-14: {rsi:.1f}", f"MACD: {macd:+.2f}", f"Volume ratio: {vol_ratio:.2f}x"],
                tech_conf,
            )
        )

    candidates.append(
        (
            "Sector / macro rotation",
            "Broad sector or macro conditions may be contributing to the move.",
            ["Check S&P 500 and sector ETF performance", "Review any macro data released today"],
            0.30,
        )
    )

    candidates.sort(key=lambda x: x[3], reverse=True)
    ranked_causes = [
        RankedCause(
            rank=i + 1,
            cause=c[0],
            explanation=c[1],
            supporting_evidence=c[2],
            confidence=round(c[3], 2),
            confidence_label=_confidence_label(c[3]),
        )
        for i, c in enumerate(candidates)
    ]

    if ranked_causes:
        top2 = ranked_causes[:2]
        weights = [1.0, 0.5]
        overall_conf = round(
            sum(c.confidence * w for c, w in zip(top2, weights)) / sum(weights[: len(top2)]),
            2,
        )
    else:
        overall_conf = 0.0

    watch_points = [
        WatchPoint(
            item="Follow-through volume tomorrow",
            reason="Confirms whether today's move was genuine or noise",
            timeframe="1 day",
        ),
        WatchPoint(
            item="Sector ETF performance",
            reason="Determines whether this is stock-specific or sector-wide",
            timeframe="2–3 days",
        ),
    ]

    if ev and ev.earnings and ev.earnings.get("days_to_next_earnings", 999) <= 21:
        watch_points.append(
            WatchPoint(
                item="Earnings report",
                reason="Major binary event approaching",
                timeframe=f"~{ev.earnings['days_to_next_earnings']} days",
            )
        )

    return PriceMovementOutput(
        ticker=ticker,
        generated_at=datetime.utcnow(),
        price_move_summary=price_move_summary,
        price_change_pct=price_pct,
        volume_context=vol_context,
        ranked_causes=ranked_causes,
        overall_confidence=overall_conf,
        what_to_watch_next=watch_points,
    )


# ── Mode 3: Watchlist Monitoring ──────────────────────────────────────────────

def _synthesise_watchlist(
    evidence: AggregatedEvidence, plan: ExecutionPlan
) -> WatchlistMonitorOutput:
    tickers = plan.tickers
    ticker_summaries: List[TickerWeeklySummary] = []
    all_news_sentiments: List[float] = []
    movers: List[Tuple[str, float]] = []

    for ticker in tickers:
        ev = evidence.get_ticker(ticker)

        md = ev.market_data if ev else {}
        pct_1w = md.get("price_change_pct_1w", 0.0) if md else 0.0
        movers.append((ticker, pct_1w))

        highlights = (
            f"{ticker} moved {_fmt_pct(pct_1w)} over the past week. "
            f"Current price: ${md.get('current_price', 0):.2f}."
            if md
            else f"No price data available for {ticker}."
        )

        news_headlines: List[str] = []
        if ev and ev.news:
            news_headlines = [a.get("title", "") for a in ev.news[:3]]
            scores = [a.get("sentiment_score", 0) for a in ev.news]
            all_news_sentiments.extend(scores)

        earnings_str = "No upcoming earnings data."
        if ev and ev.earnings:
            ne = ev.earnings.get("next_earnings")
            days = ev.earnings.get("days_to_next_earnings")
            if ne and days is not None:
                earnings_str = (
                    f"Next earnings: {ne.get('period', 'N/A')} "
                    f"in ~{days} days ({ne.get('report_time', 'TBD')})."
                )

        risk_signals: List[str] = []
        if ev and ev.fundamentals:
            risks = ev.fundamentals.get("key_risks", [])
            risk_signals.extend(risks[:1])

        if md and md.get("technicals"):
            rsi = md["technicals"].get("rsi_14", 50)
            if rsi > 72:
                risk_signals.append(f"Overbought: RSI {rsi:.0f}")
            elif rsi < 28:
                risk_signals.append(f"Oversold: RSI {rsi:.0f}")

        if ev and ev.earnings and ev.earnings.get("days_to_next_earnings", 999) <= 14:
            risk_signals.append(
                f"Earnings in {ev.earnings['days_to_next_earnings']} days — binary event risk"
            )

        wps = [
            WatchPoint(
                item=(
                    f"{ticker} price level $"
                    + (f"{md.get('current_price', 0) * 1.05:.0f}" if md else "N/A")
                ),
                reason="Key resistance if uptrend continues",
                timeframe="1 week",
            )
        ]

        if ev and ev.earnings and ev.earnings.get("days_to_next_earnings", 999) <= 21:
            wps.append(
                WatchPoint(
                    item="Earnings report",
                    reason="Potential for significant post-earnings move",
                    timeframe=f"~{ev.earnings['days_to_next_earnings']} days",
                )
            )

        ticker_summaries.append(
            TickerWeeklySummary(
                ticker=ticker,
                weekly_highlights=highlights,
                major_news=news_headlines,
                earnings_events=earnings_str,
                risk_signals=risk_signals or ["No material risk signals detected."],
                next_week_watchpoints=wps,
                momentum=_momentum_label(pct_1w),
            )
        )

    movers.sort(key=lambda x: x[1], reverse=True)
    top_mover = movers[0] if movers else ("N/A", 0.0)
    bot_mover = movers[-1] if movers else ("N/A", 0.0)

    portfolio_summary = (
        f"Weekly watchlist review across {len(tickers)} names. "
        f"Top performer: {top_mover[0]} ({_fmt_pct(top_mover[1])}). "
        f"Laggard: {bot_mover[0]} ({_fmt_pct(bot_mover[1])}). "
        f"Overall news sentiment: "
        f"{_sentiment_label(
            sum(all_news_sentiments) / len(all_news_sentiments)
            if all_news_sentiments
            else 0
        )}."
    )

    macro_risks = [
        "Fed interest rate trajectory — watch next FOMC meeting",
        "AI capex spending durability from hyperscalers",
        "U.S.–China trade/tech restrictions escalation risk",
    ]

    opportunities = [
        f"{t.ticker}: {t.weekly_highlights[:80]}..."
        for t in ticker_summaries
        if t.momentum in ("UP", "STRONG_UP")
    ][:3]

    return WatchlistMonitorOutput(
        tickers=tickers,
        generated_at=datetime.utcnow(),
        portfolio_summary=portfolio_summary,
        ticker_summaries=ticker_summaries,
        macro_risks=macro_risks,
        top_opportunities=opportunities or ["No strong momentum signals this week."],
    )


# ── Mode 4: Trading Decision ──────────────────────────────────────────────────

def build_llm_synthesis_chain():
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    prompt = ChatPromptTemplate.from_template(
        """
You are a professional trading assistant.

You will receive structured market evidence for one ticker.

Market evidence:
{input}

Based only on the evidence above, output a structured trading decision.

Return valid JSON only in this exact format:
{{
  "bias": "Bullish | Neutral | Bearish",
  "buy_zone": "price range",
  "stop_loss": "price or range",
  "take_profit": "price or range",
  "confidence": 0,
  "reasoning": ["short bullet reasons"]
}}

Rules:
- Be concise and realistic
- Do NOT hallucinate precise numbers if uncertain; prefer ranges
- Confidence must be an integer from 0 to 100
- Use only the provided ticker evidence
- If evidence is weak or mixed, return Neutral with lower confidence
"""
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return prompt | llm | JsonOutputParser()


def _synthesise_trade(
    evidence: AggregatedEvidence, plan: ExecutionPlan
) -> TradingDecisionOutput:
    ticker = plan.tickers[0]
    ev = evidence.get_ticker(ticker)

    if not _llm_trade_synthesis_enabled():
        return _heuristic_trade_decision(ticker, ev)

    chain = build_llm_synthesis_chain()

    payload = {
        "ticker": ticker,
        "market_data": ev.market_data if ev else {},
        "fundamentals": ev.fundamentals if ev else {},
        "earnings": ev.earnings if ev else {},
        "news": ev.news[:8] if ev and ev.news else [],
    }

    try:
        result = chain.invoke({"input": payload})
    except Exception as exc:
        logger.exception("Trade LLM synthesis failed for %s", ticker)
        return _heuristic_trade_decision(ticker, ev, error_note=f"Final synthesis failed: {exc}")

    reasoning = result.get("reasoning", [])
    if not isinstance(reasoning, list):
        reasoning = [str(reasoning)]

    return TradingDecisionOutput(
        ticker=ticker,
        generated_at=datetime.utcnow(),
        bias=str(result.get("bias", "Neutral")),
        buy_zone=str(result.get("buy_zone", "N/A")),
        stop_loss=str(result.get("stop_loss", "N/A")),
        take_profit=str(result.get("take_profit", "N/A")),
        confidence=_safe_confidence_int(result.get("confidence", 0)),
        reasoning=[str(r) for r in reasoning],
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

_SYNTHESISERS = {
    AnalysisMode.STOCK_RESEARCH: _synthesise_research,
    AnalysisMode.PRICE_MOVEMENT: _synthesise_price_movement,
    AnalysisMode.WATCHLIST_MONITOR: _synthesise_watchlist,
    AnalysisMode.TRADE: _synthesise_trade,
}


class SynthesisInput:
    """Container passed into the Synthesis chain."""

    def __init__(self, evidence: AggregatedEvidence, plan: ExecutionPlan):
        self.evidence = evidence
        self.plan = plan


def build_synthesis_chain() -> RunnableLambda:
    """
    Returns the Synthesis Chain as a LangChain Runnable.
    """
    def _run(inp: SynthesisInput) -> Any:
        mode = AnalysisMode(inp.plan.mode)
        synth = _SYNTHESISERS.get(mode)
        if synth is None:
            raise ValueError(f"No synthesiser for mode: {inp.plan.mode}")
        return synth(inp.evidence, inp.plan)

    return RunnableLambda(_run).with_config(run_name="SynthesisChain")
