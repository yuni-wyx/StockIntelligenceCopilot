from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import requests
import yfinance as yf
from langsmith import traceable
from pydantic import BaseModel, Field

try:
    from ..config import ALPHA_VANTAGE_API_KEY, PROVIDER_TIMEOUT_SECONDS
    from ..symbols import detect_market, normalize_symbol
except ImportError:
    from config import ALPHA_VANTAGE_API_KEY, PROVIDER_TIMEOUT_SECONDS
    from symbols import detect_market, normalize_symbol

# ── I/O models ───────────────────────────────────────────────────────────────

class NewsRequest(BaseModel):
    ticker: str
    lookback_days: int = Field(default=7, ge=1, le=90)
    max_articles: int = Field(default=10, ge=1, le=50)
    sentiment_filter: Optional[str] = None


class NewsArticle(BaseModel):
    article_id: str
    published_at: str
    title: str
    source: str
    url: str
    summary: str
    sentiment: str
    sentiment_score: float
    relevance_score: float
    tickers_mentioned: List[str]
    topics: List[str]


class NewsResponse(BaseModel):
    ticker: str
    market: str
    query_window_days: int
    total_articles: int
    articles: List[NewsArticle]
    overall_sentiment: str
    avg_sentiment_score: float
    data_caveats: List[str] = Field(default_factory=list)


# ── Core ─────────────────────────────────────────────────────────────────────

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

def _get_api_key() -> str:
    key = ALPHA_VANTAGE_API_KEY
    if not key:
        raise ValueError("Missing ALPHA_VANTAGE_API_KEY")
    return key


def _map_sentiment(score: float) -> str:
    if score > 0.2:
        return "positive"
    elif score < -0.2:
        return "negative"
    return "neutral"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_yahoo_news(ticker: str, limit: int) -> list[NewsArticle]:
    yf_ticker = yf.Ticker(ticker)
    feed = getattr(yf_ticker, "news", None) or []
    articles: list[NewsArticle] = []

    for item in feed[:limit]:
        content = item.get("content") or {}
        title = content.get("title") or item.get("title") or ""
        summary = (
            content.get("summary")
            or content.get("description")
            or item.get("summary")
            or ""
        )
        url = content.get("canonicalUrl", {}).get("url") or item.get("link") or ""
        source = (
            content.get("provider", {}).get("displayName")
            or item.get("publisher")
            or "Yahoo Finance"
        )
        published_ts = content.get("pubDate") or item.get("providerPublishTime")

        if isinstance(published_ts, (int, float)):
            published_at = datetime.fromtimestamp(published_ts, tz=timezone.utc).isoformat()
        elif isinstance(published_ts, str):
            published_at = published_ts
        else:
            # An article without a publication timestamp cannot be safely
            # presented as recent; retain it only if the provider supplied a
            # usable timestamp.
            continue

        articles.append(
            NewsArticle(
                article_id=(url or title)[:16],
                published_at=published_at,
                title=title or f"{ticker} market update",
                source=source,
                url=url,
                summary=summary or f"Recent market coverage for {ticker}.",
                sentiment="neutral",
                sentiment_score=0.0,
                relevance_score=0.6,
                tickers_mentioned=[ticker],
                topics=["general"],
            )
        )

    return articles

@traceable(name="news_tool", run_type="tool", tags=["tool", "news"])
def fetch_news(request: NewsRequest) -> NewsResponse:
    """
    Fetch real news from Alpha Vantage NEWS_SENTIMENT API.
    """

    ticker = normalize_symbol(request.ticker)
    market = detect_market(ticker)
    articles: List[NewsArticle] = []

    if market == "US":
        api_key = _get_api_key()
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": request.max_articles,
            "apikey": api_key,
        }

        try:
            res = requests.get(
                ALPHA_VANTAGE_URL,
                params=params,
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
            res.raise_for_status()
            data = res.json()
            feed = data.get("feed", [])

            for item in feed:
                title = item.get("title", "")
                summary = item.get("summary", "")
                url = item.get("url", "")
                source = item.get("source", "Unknown")

                sentiment_score = _safe_float(item.get("overall_sentiment_score", 0))
                sentiment = _map_sentiment(sentiment_score)

                if request.sentiment_filter and sentiment != request.sentiment_filter:
                    continue

                relevance = 0.5
                ticker_sentiments = item.get("ticker_sentiment", [])
                for topic in ticker_sentiments:
                    if topic.get("ticker") == ticker:
                        relevance = _safe_float(topic.get("relevance_score", 0.5), 0.5)

                published = item.get("time_published")
                if published:
                    dt = datetime.strptime(published, "%Y%m%dT%H%M%S")
                    published_at = dt.replace(tzinfo=timezone.utc).isoformat()
                else:
                    continue

                articles.append(
                    NewsArticle(
                        article_id=item.get("url", title)[:16],
                        published_at=published_at,
                        title=title,
                        source=source,
                        url=url,
                        summary=summary,
                        sentiment=sentiment,
                        sentiment_score=round(sentiment_score, 3),
                        relevance_score=round(relevance, 3),
                        tickers_mentioned=[ticker],
                        topics=[
                            topic.get("topic")
                            for topic in item.get("topics", [])
                            if "topic" in topic
                        ]
                        or ["general"],
                    )
                )
        except Exception:
            articles = []

    if not articles:
        articles = _extract_yahoo_news(ticker, request.max_articles)

    cutoff = datetime.now(timezone.utc) - timedelta(days=request.lookback_days)
    recent_articles = []
    for article in articles:
        try:
            published = datetime.fromisoformat(article.published_at.replace("Z", "+00:00"))
            if published >= cutoff:
                recent_articles.append(article)
        except ValueError:
            continue

    articles = recent_articles
    articles.sort(
        key=lambda x: (x.relevance_score, x.published_at),
        reverse=True
    )

    articles = articles[: request.max_articles]

    scores = [a.sentiment_score for a in articles]
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

    if avg_score > 0.1:
        overall = "positive"
    elif avg_score < -0.1:
        overall = "negative"
    else:
        overall = "neutral"

    return NewsResponse(
        ticker=ticker,
        market=market,
        query_window_days=request.lookback_days,
        total_articles=len(articles),
        articles=articles,
        overall_sentiment=overall,
        avg_sentiment_score=avg_score,
        data_caveats=(
            ["No provider articles were available for this ticker and period."]
            if not articles
            else []
        ),
    )
