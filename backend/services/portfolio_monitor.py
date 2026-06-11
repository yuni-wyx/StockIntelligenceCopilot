from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from ..schemas.portfolio import HoldingMetrics, PortfolioAnalysisResponse, PortfolioRequest
    from ..schemas.portfolio_monitor import (
        PortfolioHoldingMonitor,
        PortfolioMonitorRequest,
        PortfolioMonitorResponse,
    )
    from ..services.portfolio_calculator import calculate_portfolio_metrics
    from ..services.portfolio_store import PortfolioStore
    from ..tools.earnings_tool import EarningsRequest, fetch_earnings
    from ..tools.news_tool import NewsRequest, fetch_news
    from ..tools.signal_tool import SignalToolRequest, fetch_signal
except ImportError:
    from schemas.portfolio import HoldingMetrics, PortfolioAnalysisResponse, PortfolioRequest
    from schemas.portfolio_monitor import (
        PortfolioHoldingMonitor,
        PortfolioMonitorRequest,
        PortfolioMonitorResponse,
    )
    from services.portfolio_calculator import calculate_portfolio_metrics
    from services.portfolio_store import PortfolioStore
    from tools.earnings_tool import EarningsRequest, fetch_earnings
    from tools.news_tool import NewsRequest, fetch_news
    from tools.signal_tool import SignalToolRequest, fetch_signal


logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "These monitoring items are heuristic review prompts, not predictions or financial advice."
)


@dataclass
class ResolvedPortfolioMonitor:
    portfolio: PortfolioRequest
    workspace_id: str | None
    source: str


def _dedupe(items: list[str], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if limit is not None and len(deduped) >= limit:
            break
    return deduped


def _signal_watch_items(metric: HoldingMetrics, signal_response) -> tuple[list[str], list[str]]:
    watch_items: list[str] = []
    caveats = list(signal_response.data_caveats)

    if signal_response.signal_band == "Weak":
        watch_items.append(
            f"{metric.ticker} shows weak benchmark-relative strength versus "
            f"{signal_response.benchmark} over {signal_response.horizon_days} days."
        )
    elif signal_response.signal_band == "Strong" and (metric.portfolio_weight_pct or 0) >= 20:
        watch_items.append(
            f"{metric.ticker} carries a large portfolio weight and currently has a strong "
            "relative signal, so monitor whether that strength remains durable."
        )

    if signal_response.confidence == "Low":
        watch_items.append(
            f"{metric.ticker} signal confidence is low, so treat the relative signal as a "
            "review input rather than a standalone conclusion."
        )

    return watch_items, caveats


def _news_watch_items(metric: HoldingMetrics, news_response) -> tuple[list[str], list[str]]:
    watch_items: list[str] = []
    caveats: list[str] = []

    if news_response.overall_sentiment == "negative":
        title = news_response.articles[0].title if news_response.articles else "recent coverage"
        watch_items.append(
            f"{metric.ticker} has negative recent news tone; monitor the latest headline flow "
            f"starting with: {title}"
        )
    elif news_response.overall_sentiment == "positive" and (metric.portfolio_weight_pct or 0) >= 20:
        watch_items.append(
            f"{metric.ticker} has supportive recent news tone, but its portfolio weight is large "
            "enough that headline reversals still deserve monitoring."
        )

    if news_response.total_articles == 0:
        caveats.append(f"Structured news coverage was limited for {metric.ticker}.")

    return watch_items, caveats


def _earnings_watch_items(metric: HoldingMetrics, earnings_response) -> tuple[list[str], list[str]]:
    watch_items: list[str] = []
    caveats: list[str] = []

    if (
        earnings_response.next_earnings is not None
        and earnings_response.days_to_next_earnings is not None
        and earnings_response.days_to_next_earnings <= 30
    ):
        watch_items.append(
            f"{metric.ticker} reports earnings in about "
            f"{earnings_response.days_to_next_earnings} day(s), which may raise event risk."
        )

    if earnings_response.next_earnings is None:
        caveats.append(f"Upcoming earnings timing was unavailable for {metric.ticker}.")

    return watch_items, caveats


class PortfolioMonitorService:
    def __init__(self, store: PortfolioStore | None = None) -> None:
        self.store = store or PortfolioStore()

    def resolve_portfolio(
        self,
        request: PortfolioMonitorRequest,
    ) -> ResolvedPortfolioMonitor:
        if request.portfolio is not None:
            return ResolvedPortfolioMonitor(
                portfolio=request.portfolio,
                workspace_id=request.workspace_id,
                source="direct_portfolio",
            )

        workspace_name = request.workspace_id or "current"
        record = self.store.load_portfolio(workspace_name)
        if record is None:
            if request.workspace_id:
                raise ValueError(f"Saved workspace '{request.workspace_id}' was not found.")
            raise ValueError(
                "No saved current portfolio was found. Save holdings in Wealth Studio or "
                "provide a portfolio payload."
            )

        return ResolvedPortfolioMonitor(
            portfolio=record.portfolio,
            workspace_id=record.name,
            source="saved_workspace",
        )

    def _build_holding_monitor(
        self,
        metric: HoldingMetrics,
        request: PortfolioMonitorRequest,
    ) -> PortfolioHoldingMonitor:
        watch_items: list[str] = []
        caveats = list(metric.missing_data)

        if (metric.portfolio_weight_pct or 0) >= 25:
            watch_items.append(
                f"{metric.ticker} exceeds 25% of portfolio value and should be monitored as a "
                "concentration risk."
            )
        if (metric.return_pct or 0) <= -15:
            watch_items.append(
                f"{metric.ticker} is down {metric.return_pct or 0:.2f}% versus cost basis, so "
                "review drawdown tolerance and thesis drift."
            )

        try:
            signal_response = fetch_signal(
                SignalToolRequest(
                    ticker=metric.ticker,
                    benchmark=request.benchmark,
                    horizon_days=request.signal_horizon_days,
                )
            )
            signal_watch_items, signal_caveats = _signal_watch_items(metric, signal_response)
            watch_items.extend(signal_watch_items)
            caveats.extend(signal_caveats)
            signal_score = signal_response.signal_score
            signal_band = signal_response.signal_band
            signal_confidence = signal_response.confidence
        except Exception as exc:
            logger.warning("Signal monitoring failed for %s: %s", metric.ticker, exc)
            caveats.append(f"Signal evidence was unavailable for {metric.ticker}.")
            signal_score = None
            signal_band = None
            signal_confidence = None

        try:
            news_response = fetch_news(
                NewsRequest(
                    ticker=metric.ticker,
                    max_articles=request.max_news_articles,
                )
            )
            news_watch_items, news_caveats = _news_watch_items(metric, news_response)
            watch_items.extend(news_watch_items)
            caveats.extend(news_caveats)
            news_sentiment = news_response.overall_sentiment
        except Exception as exc:
            logger.warning("News monitoring failed for %s: %s", metric.ticker, exc)
            caveats.append(f"Recent news evidence was unavailable for {metric.ticker}.")
            news_sentiment = None

        next_earnings_date = None
        days_to_next_earnings = None
        if request.include_earnings:
            try:
                earnings_response = fetch_earnings(EarningsRequest(ticker=metric.ticker))
                earnings_watch_items, earnings_caveats = _earnings_watch_items(
                    metric,
                    earnings_response,
                )
                watch_items.extend(earnings_watch_items)
                caveats.extend(earnings_caveats)
                next_earnings_date = (
                    earnings_response.next_earnings.report_date
                    if earnings_response.next_earnings is not None
                    else None
                )
                days_to_next_earnings = earnings_response.days_to_next_earnings
            except Exception as exc:
                logger.warning("Earnings monitoring failed for %s: %s", metric.ticker, exc)
                caveats.append(f"Earnings timing was unavailable for {metric.ticker}.")

        return PortfolioHoldingMonitor(
            ticker=metric.ticker,
            name=metric.name,
            weight_pct=metric.portfolio_weight_pct,
            return_pct=metric.return_pct,
            signal_score=signal_score,
            signal_band=signal_band,
            signal_confidence=signal_confidence,
            news_sentiment=news_sentiment,
            next_earnings_date=next_earnings_date,
            days_to_next_earnings=days_to_next_earnings,
            watch_items=_dedupe(watch_items),
            caveats=_dedupe(caveats),
        )

    def _build_top_alerts(
        self,
        analysis: PortfolioAnalysisResponse,
        holdings: list[PortfolioHoldingMonitor],
    ) -> list[str]:
        alerts = list(analysis.risk_flags)

        intelligence = analysis.portfolio_intelligence
        if intelligence is not None:
            alerts.extend(
                f"{item.title}: {item.reason}"
                for item in intelligence.suggested_review_items[:3]
            )

        for holding in holdings[:3]:
            alerts.extend(holding.watch_items[:2])

        return _dedupe(alerts, limit=8)

    def generate(self, request: PortfolioMonitorRequest) -> PortfolioMonitorResponse:
        resolved = self.resolve_portfolio(request)
        analysis = calculate_portfolio_metrics(resolved.portfolio)
        ranked_holdings = sorted(
            analysis.holdings,
            key=lambda metric: metric.portfolio_weight_pct or 0.0,
            reverse=True,
        )
        holding_monitors = [
            self._build_holding_monitor(metric, request) for metric in ranked_holdings
        ]

        return PortfolioMonitorResponse(
            generated_at=datetime.now(timezone.utc),
            workspace_id=resolved.workspace_id,
            portfolio_summary=analysis.summary,
            risk_flags=analysis.risk_flags,
            top_portfolio_alerts=self._build_top_alerts(analysis, holding_monitors),
            holdings=holding_monitors,
            safety_disclaimer=SAFETY_DISCLAIMER,
        )
