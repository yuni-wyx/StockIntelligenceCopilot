from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None
    ChatPromptTemplate = None
    StrOutputParser = None

try:
    from ..config import OPENAI_API_KEY, llm_portfolio_chat_enabled
    from ..schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from ..schemas.portfolio_chat import (
        EarningsEvidence,
        HoldingCalculation,
        MarketEvidence,
        NewsEvidence,
        PortfolioChatEvidenceBundle,
        PortfolioChatRequest,
        PortfolioChatResponse,
        PortfolioContext,
        PortfolioContextHolding,
        PortfolioCoverageSnapshot,
        SignalEvidence,
    )
    from ..schemas.portfolio_intelligence import ReviewItem
    from ..services.portfolio_calculator import calculate_portfolio_metrics
    from ..services.portfolio_store import PortfolioStore
    from ..tools.earnings_tool import EarningsRequest, fetch_earnings
    from ..tools.market_data_tool import MarketDataRequest, fetch_market_data
    from ..tools.news_tool import NewsRequest, fetch_news
    from ..tools.signal_tool import SignalToolRequest, fetch_signal
except ImportError:
    from config import OPENAI_API_KEY, llm_portfolio_chat_enabled
    from schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from schemas.portfolio_chat import (
        EarningsEvidence,
        HoldingCalculation,
        MarketEvidence,
        NewsEvidence,
        PortfolioChatEvidenceBundle,
        PortfolioChatRequest,
        PortfolioChatResponse,
        PortfolioContext,
        PortfolioContextHolding,
        PortfolioCoverageSnapshot,
        SignalEvidence,
    )
    from schemas.portfolio_intelligence import ReviewItem
    from services.portfolio_calculator import calculate_portfolio_metrics
    from services.portfolio_store import PortfolioStore
    from tools.earnings_tool import EarningsRequest, fetch_earnings
    from tools.market_data_tool import MarketDataRequest, fetch_market_data
    from tools.news_tool import NewsRequest, fetch_news
    from tools.signal_tool import SignalToolRequest, fetch_signal


EN_DISCLAIMER = "This is an educational portfolio review, not financial advice."
ZH_DISCLAIMER = "這是教育用途的投資組合檢視，不構成投資建議。"
PORTFOLIO_CHAT_PROVIDER = "openai"
PORTFOLIO_CHAT_MODEL = "gpt-4o-mini"
logger = logging.getLogger(__name__)

HOLDING_ALIASES = {
    "中華": "2204.TW",
    "2204": "2204.TW",
    "兆利": "3548.TW",
    "3548": "3548.TW",
    "00878": "00878.TW",
    "國泰永續高股息": "00878.TW",
}


@dataclass
class ResolvedPortfolioContext:
    portfolio: PortfolioRequest
    source: str


PortfolioChatIntent = Literal[
    "portfolio_concentration",
    "holding_comparison",
    "current_performance",
    "news_review",
    "earnings_review",
    "downside_scenario",
    "review_priority",
    "income_review",
    "holdings_summary",
]


@dataclass
class PortfolioEvidence:
    intent: PortfolioChatIntent
    named_tickers: list[str]
    enrichment: dict[str, dict[str, float | str]]
    caveats: list[str]
    evidence_used: list[str]
    tools_planned: list[str]
    tools_called: list[str]
    tools_succeeded: list[str]
    tools_failed: list[str]
    market_data: dict[str, MarketEvidence]
    news: dict[str, list[NewsEvidence]]
    earnings: dict[str, EarningsEvidence]
    signals: dict[str, SignalEvidence]
    data_as_of: str | None = None
    bundle: PortfolioChatEvidenceBundle | None = None
    caveats_before_dedup: list[str] = field(default_factory=list)
    user_caveats: list[str] = field(default_factory=list)


@dataclass
class PortfolioChatGeneration:
    answer: str | None
    mode: Literal["llm", "deterministic"]
    provider: str | None = None
    model: str | None = None
    fallback_used: bool = False


def _generation_metadata_enabled() -> bool:
    env_name = os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV")
    explicit = os.getenv("ENABLE_PORTFOLIO_CHAT_GENERATION_METADATA", "")
    return explicit.strip().lower() in {"1", "true", "yes", "on"} or (
        env_name or ""
    ).strip().lower() in {"dev", "development", "local", "test"}


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _pick_language(request: PortfolioChatRequest) -> str:
    if request.language in {"en", "zh"}:
        return request.language
    return "zh" if _contains_cjk(request.question) else "en"


def classify_portfolio_chat_intent(question: str) -> PortfolioChatIntent:
    text = question.lower()
    if any(keyword in question for keyword in ["新聞", "消息", "事件", "近期"]) or "news" in text:
        return "news_review"
    if any(keyword in question for keyword in ["配息", "股息", "收益", "收入"]):
        return "income_review"
    if any(keyword in question for keyword in ["比較", "配置", "角色", "和", "跟"]):
        return "holding_comparison"
    if any(keyword in question for keyword in ["財報", "法說"]) or any(
        keyword in text for keyword in ["q1", "q2", "q3", "q4", "earnings"]
    ):
        return "earnings_review"
    if any(keyword in question for keyword in ["目前", "現在", "報酬", "損益", "價格", "績效"]):
        return "current_performance"
    if any(keyword in question for keyword in ["下跌", "跌", "回檔", "壓力", "大盤", "科技股"]):
        return "downside_scenario"
    if any(keyword in question for keyword in ["優先", "先檢查", "注意哪", "檢視哪", "最該注意"]):
        return "review_priority"
    if any(keyword in question for keyword in ["有哪些", "整理", "持股清單", "目前有哪些"]):
        return "holdings_summary"
    if any(keyword in question for keyword in ["集中", "占比", "佔比", "太高"]) or any(
        keyword in text for keyword in ["concentrat", "weight", "too high"]
    ):
        return "portfolio_concentration"
    return "holdings_summary"


def plan_portfolio_chat_tools(
    intent: PortfolioChatIntent,
    *,
    named_tickers: list[str],
) -> list[str]:
    plan = ["portfolio_context", "portfolio_calculator"]
    if intent in {
        "portfolio_concentration",
        "holding_comparison",
        "current_performance",
        "news_review",
        "earnings_review",
        "downside_scenario",
        "review_priority",
    }:
        plan.append("market_data")
    if intent in {"portfolio_concentration", "review_priority", "income_review"}:
        plan.append("portfolio_intelligence")
    if intent in {"holding_comparison", "news_review", "review_priority"}:
        plan.append("news")
    if intent in {"holding_comparison", "earnings_review", "review_priority"}:
        plan.append("earnings")
    if intent in {"holding_comparison", "current_performance", "review_priority"}:
        plan.append("signal")
    if intent == "downside_scenario":
        plan.append("stress_test")
    if named_tickers:
        plan.append("named_holding_context")
    return _dedupe_preserve_order(plan)


def _extract_named_tickers(question: str, portfolio: PortfolioRequest) -> list[str]:
    found: list[str] = []
    normalized_question = question.lower()
    for alias, ticker in HOLDING_ALIASES.items():
        if alias.lower() in normalized_question and ticker not in found:
            found.append(ticker)
    for holding in portfolio.holdings:
        candidates = [holding.ticker, holding.name or ""]
        for candidate in candidates:
            if (
                candidate
                and candidate.lower() in normalized_question
                and holding.ticker not in found
            ):
                found.append(holding.ticker)
    return found


def _has_current_value_data(context: PortfolioContext) -> bool:
    return any(holding.current_value is not None for holding in context.holdings)


def _has_missing_price_data(context: PortfolioContext) -> bool:
    return any(
        holding.current_value is None and holding.current_price is None
        for holding in context.holdings
    )


def _round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value + 1e-12, 2)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        results.append(item)
    return results


def _build_coverage_snapshot(
    holdings: list[PortfolioContextHolding],
    source_holdings: list[HoldingInput],
) -> PortfolioCoverageSnapshot:
    material_holdings = [holding for holding in holdings if (holding.cost_basis or 0) > 0]
    material_count = len(material_holdings)
    priced_holdings = [
        holding for holding in material_holdings if holding.current_value is not None
    ]
    total_cost_basis = sum(holding.cost_basis or 0 for holding in material_holdings)
    priced_cost_basis = sum(holding.cost_basis or 0 for holding in priced_holdings)
    priced_current_value = sum(holding.current_value or 0 for holding in priced_holdings)
    classified_count = sum(
        1
        for holding in source_holdings
        if holding.asset_type or holding.category
    )
    total_source_count = len(source_holdings)
    return PortfolioCoverageSnapshot(
        total_holdings_count=material_count,
        priced_holdings_count=len(priced_holdings),
        unpriced_holdings_count=max(material_count - len(priced_holdings), 0),
        classified_holdings_count=classified_count,
        unclassified_holdings_count=max(total_source_count - classified_count, 0),
        priced_current_value=_round2(priced_current_value),
        priced_cost_basis=_round2(priced_cost_basis),
        total_cost_basis=_round2(total_cost_basis),
        current_price_coverage_pct_by_count=(
            _round2(len(priced_holdings) / material_count * 100)
            if material_count
            else None
        ),
        current_price_coverage_pct_by_cost_basis=(
            _round2(priced_cost_basis / total_cost_basis * 100)
            if total_cost_basis
            else None
        ),
        classification_coverage_pct=(
            _round2(classified_count / total_source_count * 100)
            if total_source_count
            else None
        ),
        allocation_complete=material_count > 0 and len(priced_holdings) == material_count,
        classification_complete=total_source_count > 0 and classified_count == total_source_count,
    )


def _has_complete_allocation(context: PortfolioContext) -> bool:
    return context.coverage.allocation_complete


def _holding_to_context_holding(
    holding: HoldingInput,
    analysis_holding: HoldingMetrics | None = None,
) -> PortfolioContextHolding:
    return PortfolioContextHolding(
        ticker=holding.ticker,
        name=holding.name or (analysis_holding.name if analysis_holding else None),
        shares=(
            holding.shares
            if holding.shares is not None
            else (analysis_holding.shares if analysis_holding else None)
        ),
        avg_cost=holding.avg_cost,
        current_price=(
            holding.current_price
            if holding.current_price is not None
            else (analysis_holding.current_price if analysis_holding else None)
        ),
        current_value=(
            holding.current_value
            if holding.current_value is not None
            else (analysis_holding.current_value if analysis_holding else None)
        ),
        cost_basis=analysis_holding.cost_basis if analysis_holding else None,
        unrealized_gain_loss=(
            analysis_holding.unrealized_gain_loss if analysis_holding else None
        ),
        return_pct=analysis_holding.return_pct if analysis_holding else None,
        weight_pct=analysis_holding.portfolio_weight_pct if analysis_holding else None,
    )


def _summarise_concentration(analysis: PortfolioAnalysisResponse) -> str:
    concentration = (
        analysis.portfolio_intelligence.concentration
        if analysis.portfolio_intelligence
        else None
    )
    if concentration is not None and concentration.top_tickers:
        lead = concentration.top_tickers[0]
        return (
            f"Top holding is {lead.ticker} at {lead.weight_pct or 0:.2f}% of portfolio value. "
            f"Top 3 holdings account for {concentration.top_3_weight_pct or 0:.2f}%."
        )

    lead = max(
        analysis.holdings,
        key=lambda item: item.portfolio_weight_pct or 0.0,
        default=None,
    )
    if lead is None:
        return (
            "No concentration summary is available because the portfolio has no "
            "priced holdings."
        )
    return (
        f"Top holding is {lead.ticker} at "
        f"{lead.portfolio_weight_pct or 0:.2f}% of portfolio value."
    )


def _summarise_income(analysis: PortfolioAnalysisResponse) -> str:
    annual = analysis.estimated_annual_dividend
    monthly = analysis.estimated_monthly_dividend
    if annual is None and monthly is None:
        return "Dividend or income estimates are limited by the current holding data."
    return (
        f"Estimated annual income is {annual or 0:.2f} and estimated monthly equivalent is "
        f"{monthly or 0:.2f}. These figures are heuristic estimates."
    )


def _build_followups(language: str, intent: PortfolioChatIntent) -> list[str]:
    zh_followups = {
        "portfolio_concentration": [
            "要查看前 3 大持股占比嗎？",
            "要模擬最大持股下跌 15% 嗎？",
            "要比較成本基礎占比和目前市值占比嗎？",
        ],
        "holding_comparison": [
            "要比較兩檔的目前權重嗎？",
            "要查看近期財報與訊號嗎？",
            "要加入壓力測試比較它們的影響嗎？",
        ],
        "current_performance": [
            "要查看目前損益最大的持股嗎？",
            "要比較目前市值權重和成本基礎占比嗎？",
            "要檢查近期相對訊號嗎？",
        ],
        "news_review": [
            "要整理每檔持股最近的新聞重點嗎？",
            "要查看新聞資料缺口嗎？",
            "要把新聞和目前權重一起比較嗎？",
        ],
        "earnings_review": [
            "要查看哪些持股缺少財報日期嗎？",
            "要把財報風險和持股權重一起比較嗎？",
            "要檢查近期財報後股價變動嗎？",
        ],
        "downside_scenario": [
            "要模擬科技股下跌 15% 嗎？",
            "要看哪一檔對下行情境影響最大嗎？",
            "要檢查防禦型配置是否足夠嗎？",
        ],
        "review_priority": [
            "要列出前三個優先檢查項目嗎？",
            "要把未實現虧損和集中度一起比較嗎？",
            "要查看監控清單中的新聞或財報提醒嗎？",
        ],
        "income_review": [
            "要查看配息資料缺口嗎？",
            "要比較收益來源是否太集中嗎？",
            "要估算如果某檔配息降低的影響嗎？",
        ],
        "holdings_summary": [
            "要看每檔持股的成本基礎嗎？",
            "要補上目前價格後重新分析嗎？",
            "要查看集中度或收益品質嗎？",
        ],
    }
    en_followups = {
        "portfolio_concentration": [
            "Review the top 3 holding weights?",
            "Run a 15% drawdown scenario on the largest holding?",
            "Compare cost-basis exposure with current-value exposure?",
        ],
        "holding_comparison": [
            "Compare the current weights for those holdings?",
            "Review recent earnings and relative signals?",
            "Add a stress scenario for the compared holdings?",
        ],
        "current_performance": [
            "Review the largest current unrealized gains or losses?",
            "Compare current-value weight with cost-basis exposure?",
            "Check recent relative signal evidence?",
        ],
        "news_review": [
            "Summarize recent news by holding?",
            "Review where news coverage is missing?",
            "Compare news context with current portfolio weights?",
        ],
        "earnings_review": [
            "Review which holdings lack earnings dates?",
            "Compare earnings event risk with portfolio weight?",
            "Check recent post-earnings move history?",
        ],
        "downside_scenario": [
            "Run a technology selloff stress test?",
            "Review the largest downside contributors?",
            "Check whether defensive exposure is enough?",
        ],
        "review_priority": [
            "List the top three review items?",
            "Compare unrealized losses with concentration?",
            "Review monitoring alerts from news or earnings?",
        ],
        "income_review": [
            "Review missing dividend data?",
            "Check whether income sources are concentrated?",
            "Estimate sensitivity to lower dividend assumptions?",
        ],
        "holdings_summary": [
            "Show cost basis by holding?",
            "Refresh analysis after adding current prices?",
            "Review concentration or income quality?",
        ],
    }
    if language == "zh":
        return zh_followups[intent]
    return en_followups[intent]


def _format_holding_line(
    holding: PortfolioContextHolding,
    *,
    language: str,
    include_weight: bool = True,
) -> str:
    label = holding.name or holding.ticker
    if language == "zh":
        pieces = [
            f"{label}（{holding.ticker}）",
            f"{holding.shares:g} 股" if holding.shares is not None else "股數缺少",
            f"平均成本 {holding.avg_cost:.2f}" if holding.avg_cost is not None else "成本缺少",
        ]
        if holding.cost_basis is not None:
            pieces.append(f"成本基礎 {holding.cost_basis:.2f}")
        if holding.current_value is not None:
            pieces.append(f"目前市值 {holding.current_value:.2f}")
        if include_weight and holding.weight_pct is not None:
            pieces.append(f"權重 {holding.weight_pct:.2f}%")
        if holding.return_pct is not None:
            pieces.append(f"報酬 {holding.return_pct:.2f}%")
        return "、".join(pieces)

    pieces = [
        f"{label} ({holding.ticker})",
        f"{holding.shares:g} shares" if holding.shares is not None else "shares missing",
        f"average cost {holding.avg_cost:.2f}" if holding.avg_cost is not None else "cost missing",
    ]
    if holding.cost_basis is not None:
        pieces.append(f"cost basis {holding.cost_basis:.2f}")
    if holding.current_value is not None:
        pieces.append(f"current value {holding.current_value:.2f}")
    if include_weight and holding.weight_pct is not None:
        pieces.append(f"weight {holding.weight_pct:.2f}%")
    if holding.return_pct is not None:
        pieces.append(f"return {holding.return_pct:.2f}%")
    return ", ".join(pieces)


def _missing_price_caveat(language: str) -> str:
    if language == "zh":
        return (
            "部分持股缺少目前價格或目前市值；以下只能使用成本基礎占比，"
            "不能視為目前配置或目前集中度。"
        )
    return (
        "Some holdings are missing current price or current value; this can only use "
        "cost-basis exposure, not current allocation or current concentration."
    )


def _format_missing_price_for_ticker(ticker: str, *, language: str) -> str:
    if language == "zh":
        return (
            f"目前無法取得 {ticker} 的現價，因此無法計算其持有現值、"
            "未實現報酬與目前權重。"
        )
    return (
        f"Current price was unavailable for {ticker}, so current value, "
        "unrealized return, and current portfolio weight could not be calculated."
    )


def _format_news_unavailable(ticker: str | None, *, language: str) -> str:
    if language == "zh":
        if ticker:
            return f"新聞工具目前未取得 {ticker} 的可用近期新聞。"
        return "新聞工具目前未取得可用的近期新聞。"
    if ticker:
        return f"No recent news evidence was available for {ticker} from the current provider."
    return "No recent news evidence was available from the current provider."


def _format_earnings_unavailable(ticker: str | None, *, language: str) -> str:
    if language == "zh":
        if ticker:
            return f"目前無法取得 {ticker} 的可靠財報時間，因此不會猜測財報日期或數字。"
        return "目前無法取得可靠財報時間，因此不會猜測財報日期或數字。"
    if ticker:
        return f"Earnings timing was unavailable for {ticker}; no dates or figures were inferred."
    return "Earnings timing was unavailable; no dates or figures were inferred."


def _format_signal_unavailable(ticker: str | None, *, language: str) -> str:
    if language == "zh":
        if ticker:
            return f"目前無法取得 {ticker} 的相對訊號，因此不會加入訊號結論。"
        return "目前無法取得相對訊號，因此不會加入訊號結論。"
    if ticker:
        return f"Signal evidence was unavailable for {ticker}, so no signal conclusion was added."
    return "Signal evidence was unavailable, so no signal conclusion was added."


def _format_signal_low_confidence(ticker: str | None, *, language: str) -> str:
    if language == "zh":
        if ticker:
            return f"{ticker} 的相對訊號信心偏低，請只把它當作輔助檢查。"
        return "相對訊號信心偏低，請只把它當作輔助檢查。"
    if ticker:
        return f"Signal confidence was low for {ticker}; treat it as a secondary check."
    return "Signal confidence was low; treat it as a secondary check."


def _format_missing_cost_basis(ticker: str | None, *, language: str) -> str:
    if language == "zh":
        if ticker:
            return f"{ticker} 缺少平均成本或股數，因此無法計算成本基礎。"
        return "部分持股缺少平均成本或股數，因此無法計算成本基礎。"
    if ticker:
        return f"{ticker} is missing average cost or shares, so cost basis could not be calculated."
    return (
        "Some holdings are missing average cost or shares, so cost basis could "
        "not be calculated."
    )


def _format_dividend_missing(*, language: str) -> str:
    if language == "zh":
        return "部分持股缺少股息資料，因此收益品質只能作為估算檢查。"
    return "Some holdings are missing dividend data, so income quality is only an estimate."


def _format_classification_incomplete(*, language: str) -> str:
    if language == "zh":
        return "部分持股缺少資產類型或分類資料，因此防禦型配置判讀只能作為粗略檢查。"
    return (
        "Some holdings are missing asset type or classification data, so defensive "
        "allocation conclusions are only rough checks."
    )


def _format_allocation_incomplete(*, language: str) -> str:
    if language == "zh":
        return "目前無法完整計算持股權重，因部分持股缺少現價。"
    return (
        "Current portfolio weights could not be calculated completely because "
        "some holdings lack current prices."
    )


def _extract_caveat_ticker(message: str) -> str | None:
    for token in message.replace("(", " ").replace(")", " ").replace("。", " ").split():
        cleaned = token.strip(".,;:，；：")
        if "." in cleaned or any(char.isdigit() for char in cleaned):
            if len(cleaned) <= 12:
                return cleaned
    return None


def _normalise_caveat_message(message: str, *, language: str) -> tuple[str, str]:
    lowered = message.lower()
    ticker = _extract_caveat_ticker(message)

    if "current price evidence was unavailable" in lowered:
        key = f"missing_price:{ticker or '*'}"
        return key, _format_missing_price_for_ticker(ticker or "this holding", language=language)
    if "missing current value and price/shares" in lowered:
        key = "missing_price:*"
        return key, _missing_price_caveat(language)
    if (
        "recent news evidence was unavailable" in lowered
        or "recent news coverage was limited" in lowered
    ):
        key = f"news_unavailable:{ticker or '*'}"
        return key, _format_news_unavailable(ticker, language=language)
    if "earnings timing was unavailable" in lowered:
        key = f"earnings_unavailable:{ticker or '*'}"
        return key, _format_earnings_unavailable(ticker, language=language)
    if "signal evidence was unavailable" in lowered:
        key = f"signal_unavailable:{ticker or '*'}"
        return key, _format_signal_unavailable(ticker, language=language)
    if "signal confidence was low" in lowered or "low confidence" in lowered:
        key = f"signal_low:{ticker or '*'}"
        return key, _format_signal_low_confidence(ticker, language=language)
    if "missing average cost or shares" in lowered:
        key = f"missing_cost_basis:{ticker or '*'}"
        return key, _format_missing_cost_basis(ticker, language=language)
    if "dividend" in lowered or "income" in lowered or "股息" in message or "配息" in message:
        return "missing_dividend:*", _format_dividend_missing(language=language)
    if "classification data was incomplete" in lowered:
        return "classification_incomplete:*", _format_classification_incomplete(
            language=language
        )
    if "portfolio allocation coverage was incomplete" in lowered:
        return "allocation_incomplete:*", _format_allocation_incomplete(
            language=language
        )
    if "short history" in lowered or "insufficient history" in lowered:
        if language == "zh":
            return "short_history:*", "市場歷史資料不足，因此相對訊號或技術特徵信心較低。"
        return (
            "short_history:*",
            "Market history was short, so signal or technical evidence has lower confidence.",
        )
    if "provider" in lowered or "unavailable" in lowered:
        if language == "zh":
            return f"provider:{ticker or message}", "部分資料供應商目前沒有回傳完整資料。"
        return (
            f"provider:{ticker or message}",
            "One or more data providers did not return complete evidence.",
        )
    return f"raw:{message}", message


def _build_user_caveats(
    context: PortfolioContext,
    evidence_caveats: list[str],
    *,
    language: str,
) -> list[str]:
    keyed: dict[str, str] = {}

    missing_price_tickers = [
        holding.ticker
        for holding in context.holdings
        if holding.current_price is None and holding.current_value is None
    ]
    for ticker in missing_price_tickers:
        keyed[f"missing_price:{ticker}"] = _format_missing_price_for_ticker(
            ticker,
            language=language,
        )

    for message in [*context.data_caveats, *evidence_caveats]:
        key, formatted = _normalise_caveat_message(message, language=language)
        if key == "missing_price:*" and missing_price_tickers:
            continue
        if key.startswith("raw:") and formatted in keyed.values():
            continue
        keyed.setdefault(key, formatted)

    return list(keyed.values())


def _cost_basis_exposure_lines(context: PortfolioContext, *, language: str) -> list[str]:
    total_cost = sum(holding.cost_basis or 0 for holding in context.holdings)
    lines: list[str] = []
    if total_cost <= 0:
        return lines
    sorted_holdings = sorted(
        context.holdings,
        key=lambda item: item.cost_basis or 0,
        reverse=True,
    )
    for holding in sorted_holdings:
        exposure = (holding.cost_basis or 0) / total_cost * 100
        label = holding.name or holding.ticker
        if language == "zh":
            lines.append(f"- {label}（{holding.ticker}）：成本基礎占比 {exposure:.2f}%")
        else:
            lines.append(f"- {label} ({holding.ticker}): cost-basis exposure {exposure:.2f}%")
    return lines[:5]


def _calculation_map(context: PortfolioContext) -> dict[str, HoldingCalculation]:
    return {
        holding.ticker: HoldingCalculation(
            ticker=holding.ticker,
            cost_basis=holding.cost_basis,
            current_value=holding.current_value,
            unrealized_gain_loss=holding.unrealized_gain_loss,
            return_pct=holding.return_pct,
            weight_pct=holding.weight_pct,
        )
        for holding in context.holdings
    }


def _build_evidence_bundle(
    context: PortfolioContext,
    evidence: PortfolioEvidence,
) -> PortfolioChatEvidenceBundle:
    return PortfolioChatEvidenceBundle(
        portfolio_context=context,
        coverage=context.coverage,
        market_data=evidence.market_data,
        calculations=_calculation_map(context),
        news=evidence.news,
        earnings=evidence.earnings,
        signals=evidence.signals,
        tool_errors=evidence.tools_failed,
        data_caveats=evidence.user_caveats or _dedupe_preserve_order(
            [*context.data_caveats, *evidence.caveats]
        ),
        generated_at=datetime.now(timezone.utc),
    )


def _has_grounding_violation(answer: str) -> bool:
    lowered = answer.lower()
    forbidden_phrases = [
        "guaranteed",
        "target price",
        "must buy",
        "must sell",
        "一定獲利",
        "保證",
        "目標價",
        "必須買",
        "必須賣",
    ]
    if any(phrase in lowered for phrase in forbidden_phrases):
        return True

    mismatched_pairs = [
        ("兆利（2204.TW", "兆利 (2204.TW", "兆利(2204.TW"),
        ("中華（3548.TW", "中華 (3548.TW", "中華(3548.TW"),
    ]
    return any(any(pattern in answer for pattern in group) for group in mismatched_pairs)


def _build_answer(
    question: str,
    context: PortfolioContext,
    *,
    language: str,
    intent: PortfolioChatIntent,
    named_tickers: list[str] | None = None,
    evidence_caveats: list[str] | None = None,
) -> str:
    named_tickers = named_tickers or []
    evidence_caveats = evidence_caveats or []
    review_items = context.suggested_review_items[:4]
    has_current_values = _has_complete_allocation(context)
    user_caveats = _build_user_caveats(context, evidence_caveats, language=language)

    def formatted_caveats() -> list[str]:
        return [f"- {item}" for item in user_caveats[:6]]

    if language == "zh":
        if intent == "portfolio_concentration":
            if has_current_values:
                exposure_lines = [
                    f"- {_format_holding_line(item, language='zh')}"
                    for item in context.top_holdings[:3]
                ]
                headline = f"集中度判讀：{context.concentration_summary}"
            else:
                exposure_lines = _cost_basis_exposure_lines(context, language="zh")
                headline = (
                    "集中度判讀：目前無法可靠計算完整投資組合權重，"
                    "因為部分重要持股缺少現價；以下改用成本基礎占比檢視。"
                )
            return "\n".join(
                [
                    "結論：你的投資組合集中度值得檢視，但需要區分目前市值占比與成本基礎占比。",
                    headline,
                    "主要占比：",
                    *exposure_lines,
                    "情境下一步：如果要更保守，可以接著模擬最大持股下跌 15% 的影響。",
                    "資料限制：",
                    *(formatted_caveats() or ["- 目前沒有額外資料限制。"]),
                ]
            )

        if intent == "holding_comparison":
            requested = [
                item for item in context.holdings if item.ticker in set(named_tickers)
            ] or context.top_holdings[:2]
            lines = [f"- {_format_holding_line(item, language='zh')}" for item in requested]
            reliable_lines = _cost_basis_exposure_lines(context, language="zh")
            return "\n".join(
                [
                    "比較重點：我會先比較你問到的持股在組合中的角色與資料完整性。",
                    (
                        "目前無法可靠計算完整投資組合權重；若只有部分持股有現價，"
                        "不能把有價格的 subset 視為完整配置。"
                    )
                    if not has_current_values
                    else "目前價格資料完整，因此可以比較目前權重。",
                    "持股比較：",
                    *lines,
                    "可可靠計算的內容：",
                    *(reliable_lines or ["- 目前缺少成本基礎資料。"]),
                    "暫時無法可靠計算：完整目前權重、完整集中度、總現值與總未實現損益。"
                    if not has_current_values
                    else "目前可比較完整權重與持股損益。",
                    "資料限制：",
                    *(formatted_caveats() or ["- 新聞、財報或訊號若不可用，不會被編入結論。"]),
                ]
            )

        if intent == "current_performance":
            lines = [
                f"- {_format_holding_line(item, language='zh')}"
                for item in context.top_holdings[:5]
            ]
            return "\n".join(
                [
                    "目前表現檢視：以下數字來自工具或你提供的目前價格，不由模型自行計算。",
                    *lines,
                    "資料限制：",
                    *(formatted_caveats() or ["- 目前沒有額外資料限制。"]),
                ]
            )

        if intent == "news_review":
            exposure_lines = (
                _cost_basis_exposure_lines(context, language="zh")
                if not has_current_values
                else [
                    f"- {_format_holding_line(item, language='zh')}"
                    for item in context.top_holdings[:3]
                ]
            )
            return "\n".join(
                [
                    "新聞檢視：我會先使用已知持股與可用工具證據；新聞不可用時不會補編內容。",
                    "目前仍可用的投資組合脈絡：",
                    *exposure_lines,
                    "建議追蹤：先看權重或成本投入較高的持股，再等新聞工具恢復後補查近期事件。",
                    "資料限制：",
                    *(formatted_caveats() or ["- 目前沒有額外資料限制。"]),
                ]
            )

        if intent == "earnings_review":
            earnings_holdings = (
                context.top_holdings[:3] if has_current_values else context.holdings[:3]
            )
            exposure_lines = [
                f"- {_format_holding_line(item, language='zh')}"
                for item in earnings_holdings
            ]
            return "\n".join(
                [
                    "財報檢視：若工具沒有確認日期或財務數字，這裡不會猜測 Q2 或其他財報資訊。",
                    "目前仍可用的持股脈絡：",
                    *exposure_lines,
                    "建議追蹤：等財報工具有資料後，再把事件風險和目前權重一起看。",
                    "資料限制：",
                    *(formatted_caveats() or ["- 目前沒有額外資料限制。"]),
                ]
            )

        if intent == "downside_scenario":
            top = context.top_holdings[:3] if has_current_values else context.holdings[:3]
            lines = [f"- {_format_holding_line(item, language='zh')}" for item in top]
            return "\n".join(
                [
                    "下行情境檢視：這不是預測，而是用目前持股資料找出壓力測試時最需要監控的部位。",
                    "可能影響較大的持股：",
                    *lines,
                    (
                        "建議檢查：可以接著模擬科技股或最大持股下跌 "
                        "15% 的情境，看哪一檔對組合影響最大。"
                    ),
                    "資料限制：",
                    *(
                        formatted_caveats()
                        or ["- 若沒有即時價格，壓力測試只能使用你輸入的價值基準。"]
                    ),
                ]
            )

        if intent == "review_priority":
            review_lines = [
                f"- {item.title}: {item.reason}"
                for item in review_items
            ] or ["- 目前沒有觸發高優先檢查項目，先補齊價格、分類與配息資料。"]
            return "\n".join(
                [
                    "優先檢查順序：我會以集中度、未實現虧損、資料缺口與監控訊號排序。",
                    *review_lines,
                    "資料限制：",
                    *(formatted_caveats() or ["- 目前沒有額外資料限制。"]),
                ]
            )

        if intent == "income_review":
            return "\n".join(
                [
                    "收益品質檢視：配息估算只能當作啟發式檢查，不代表保證收入。",
                    f"收益摘要：{context.income_summary}",
                    "建議檢查：",
                    "- 檢查是否有持股缺少股息資料。",
                    "- 檢查預估收益是否集中在單一 ETF 或單一股票。",
                    "資料限制：",
                    *(formatted_caveats() or ["- 若沒有股息輸入或工具資料，收益估算會偏保守。"]),
                ]
            )

        holding_lines = [
            f"- {_format_holding_line(item, language='zh')}"
            for item in context.holdings
        ]
        return "\n".join(
            [
                "持股整理：以下是目前投資組合記憶中的完整持股。",
                *holding_lines,
                "資料限制：",
                *(formatted_caveats() or ["- 沒有市價時，不會推論目前報酬或目前配置。"]),
            ]
        )

    if intent == "portfolio_concentration":
        if has_current_values:
            exposure_lines = [
                f"- {_format_holding_line(item, language='en')}"
                for item in context.top_holdings[:3]
            ]
            headline = f"Concentration read: {context.concentration_summary}"
        else:
            exposure_lines = _cost_basis_exposure_lines(context, language="en")
            headline = (
                "Concentration read: full current portfolio weights cannot be "
                "calculated reliably because some material holdings lack current "
                "prices; this uses cost-basis exposure instead."
            )
        return "\n".join(
            [
                (
                    "Conclusion: portfolio concentration is worth reviewing, but "
                    "current-value exposure and cost-basis exposure must stay separate."
                ),
                headline,
                "Largest exposures:",
                *exposure_lines,
                "Data caveats:",
                *(formatted_caveats() or ["- No additional data caveats."]),
            ]
        )

    if intent == "holding_comparison":
        requested = [
            item for item in context.holdings if item.ticker in set(named_tickers)
        ] or context.top_holdings[:2]
        lines = [f"- {_format_holding_line(item, language='en')}" for item in requested]
        reliable_lines = _cost_basis_exposure_lines(context, language="en")
        return "\n".join(
            [
                "Comparison focus: compare the requested holdings by role, size, and data quality.",
                (
                    "Full current portfolio weights are unavailable because at least "
                    "one material holding lacks a current price."
                )
                if not has_current_values
                else "Current price coverage is complete, so current weights can be compared.",
                "Holding comparison:",
                *lines,
                "Reliable calculations:",
                *(reliable_lines or ["- Cost-basis data is incomplete."]),
                (
                    "Temporarily unavailable: complete current allocation, full "
                    "concentration, total current value, and total unrealized P/L."
                )
                if not has_current_values
                else (
                    "Current allocation and unrealized P/L are available from "
                    "supplied or fetched prices."
                ),
                "Data caveats:",
                *(
                    formatted_caveats()
                    or [
                        "- News, earnings, or signal evidence was not fabricated "
                        "when unavailable."
                    ]
                ),
            ]
        )

    if intent == "current_performance":
        lines = [
            f"- {_format_holding_line(item, language='en')}"
            for item in context.top_holdings[:5]
        ]
        return "\n".join(
            [
                "Current performance review: values come from tools or supplied prices, "
                "not model arithmetic.",
                *lines,
                "Data caveats:",
                *(formatted_caveats() or ["- No additional data caveats."]),
            ]
        )

    if intent == "news_review":
        exposure_lines = (
            _cost_basis_exposure_lines(context, language="en")
            if not has_current_values
            else [
                f"- {_format_holding_line(item, language='en')}"
                for item in context.top_holdings[:3]
            ]
        )
        return "\n".join(
            [
                (
                    "News review: use known portfolio context first; "
                    "tool-missing news is not fabricated."
                ),
                "Portfolio context still available:",
                *exposure_lines,
                (
                    "Suggested check: monitor the largest exposures first, then "
                    "refresh news evidence later."
                ),
                "Data caveats:",
                *(formatted_caveats() or ["- No additional data caveats."]),
            ]
        )

    if intent == "earnings_review":
        exposure_lines = [
            f"- {_format_holding_line(item, language='en')}"
            for item in (context.top_holdings[:3] if has_current_values else context.holdings[:3])
        ]
        return "\n".join(
            [
                (
                    "Earnings review: if confirmed dates or metrics are unavailable, "
                    "they are not guessed."
                ),
                "Portfolio context still available:",
                *exposure_lines,
                "Suggested check: refresh earnings evidence before making any event-risk review.",
                "Data caveats:",
                *(formatted_caveats() or ["- No additional data caveats."]),
            ]
        )

    if intent == "downside_scenario":
        top = context.top_holdings[:3] if has_current_values else context.holdings[:3]
        lines = [f"- {_format_holding_line(item, language='en')}" for item in top]
        return "\n".join(
            [
                "Downside scenario review: this is a what-if review, not a prediction.",
                "Holdings most worth monitoring in a stress scenario:",
                *lines,
                (
                    "Suggested check: run a 15% drawdown scenario on technology "
                    "or the largest holding."
                ),
                "Data caveats:",
                *(
                    formatted_caveats()
                    or [
                        "- Without live prices, stress testing can only use "
                        "user-provided value assumptions."
                    ]
                ),
            ]
        )

    if intent == "review_priority":
        review_lines = [
            f"- {item.title}: {item.reason}"
            for item in review_items
        ] or [
            "- No high-priority review item was triggered; first improve price, "
            "category, and dividend coverage."
        ]
        return "\n".join(
            [
                (
                    "Review priority: rank by concentration, unrealized losses, "
                    "data gaps, and monitoring signals."
                ),
                *review_lines,
                "Data caveats:",
                *(formatted_caveats() or ["- No additional data caveats."]),
            ]
        )

    if intent == "income_review":
        return "\n".join(
            [
                (
                    "Income quality review: dividend estimates are heuristic and "
                    "not guaranteed income."
                ),
                f"Income summary: {context.income_summary}",
                "Suggested checks:",
                "- Review holdings with missing dividend data.",
                "- Review whether estimated income depends too heavily on one ETF or stock.",
                "Data caveats:",
                *(
                    formatted_caveats()
                    or [
                        "- If dividend data is missing, income estimates may be "
                        "conservative."
                    ]
                ),
            ]
        )

    holding_lines = [
        f"- {_format_holding_line(item, language='en')}"
        for item in context.holdings
    ]
    return "\n".join(
        [
            "Holdings summary: these are the complete holdings currently in portfolio memory.",
            *holding_lines,
            "Data caveats:",
            *(
                formatted_caveats()
                or [
                    "- Without prices, current return and current allocation are "
                    "not inferred."
                ]
            ),
        ]
    )


def _build_llm_answer(
    question: str,
    evidence_bundle: PortfolioChatEvidenceBundle,
    *,
    language: str,
    intent: PortfolioChatIntent,
    named_tickers: list[str],
    evidence_caveats: list[str],
) -> PortfolioChatGeneration:
    if not (llm_portfolio_chat_enabled() and OPENAI_API_KEY):
        return PortfolioChatGeneration(answer=None, mode="deterministic")
    if not (ChatPromptTemplate and ChatOpenAI and StrOutputParser):
        return PortfolioChatGeneration(
            answer=None,
            mode="deterministic",
            provider=PORTFOLIO_CHAT_PROVIDER,
            model=PORTFOLIO_CHAT_MODEL,
        )

    prompt = ChatPromptTemplate.from_template(
        """
You are a calm portfolio copilot for a demo product.
Use only the supplied structured evidence bundle.
Do not invent holdings, numbers, or market data.
Do not say buy or sell.
Do not promise returns or guaranteed outcomes.
Do not use target price language.
Do not add a reminder to save the workspace unless the user explicitly asks how memory works.
Do not invent current prices, current values, news, earnings dates, signal scores, or dividends.
Do not recalculate numeric values; use the calculations field exactly.
Preserve all provided numeric values exactly.
Lead with the strongest available portfolio evidence: saved holdings, shares,
average cost, cost basis, current market data if present, portfolio intelligence,
signal evidence, news, then earnings.
Do not lead with tool errors unless no usable portfolio context exists.
Use partial evidence productively.
If current prices are missing, use cost-basis exposure only and never describe it
as current allocation, current concentration, current return, or current weight.
Never describe a priced subset as the full portfolio.
Never calculate full allocation when any material holding lacks current value.
Never say a holding is 100% of the portfolio unless coverage.allocation_complete is true.
Distinguish current-value weight from cost-basis exposure.
If price coverage is incomplete, state that full allocation is unavailable.
Do not present defensive allocation as reliable when classification or
current-value coverage is incomplete.
If market data, news, earnings, or signal evidence is missing, mention the
deduplicated limitation once near the end.
Do not repeat caveats.
Do not claim news, earnings, or signal conclusions unless those sections contain evidence.
Make the response specific to the detected intent and the user's question.
Use review-oriented language such as review, monitor, concentration, scenario, and risk threshold.
Respond in the same language as the user when possible.

User question:
{question}

Detected intent:
{intent}

Named holdings or tickers from question:
{named_tickers}

Structured evidence bundle:
{evidence_bundle}

Evidence caveats:
{evidence_caveats}

Preferred response language:
{language}

Write a concise, friendly answer that:
- acknowledges the question
- uses a structure appropriate for the detected intent
- summarizes only evidence that is present
- highlights 2-4 review or monitoring items
- includes data limitations once at the end
- ends with a short non-advisory reminder
"""
    )
    llm = ChatOpenAI(model=PORTFOLIO_CHAT_MODEL, temperature=0)
    chain = prompt | llm | StrOutputParser()
    try:
        answer = chain.invoke(
            {
                "question": question,
                "intent": intent,
                "named_tickers": named_tickers,
                "evidence_bundle": evidence_bundle.model_dump(mode="json"),
                "evidence_caveats": evidence_caveats,
                "language": language,
            }
        ).strip()
        return PortfolioChatGeneration(
            answer=answer,
            mode="llm",
            provider=PORTFOLIO_CHAT_PROVIDER,
            model=PORTFOLIO_CHAT_MODEL,
            fallback_used=False,
        )
    except Exception:
        logger.warning(
            "Portfolio chat LLM provider failed; using deterministic fallback",
            extra={
                "provider": PORTFOLIO_CHAT_PROVIDER,
                "model": PORTFOLIO_CHAT_MODEL,
            },
        )
        return PortfolioChatGeneration(
            answer=None,
            mode="deterministic",
            provider=PORTFOLIO_CHAT_PROVIDER,
            model=PORTFOLIO_CHAT_MODEL,
            fallback_used=True,
        )


class PortfolioContextBuilder:
    def __init__(self, store: PortfolioStore | None = None) -> None:
        self.store = store or PortfolioStore()

    def build_evidence(
        self,
        request: PortfolioChatRequest,
        portfolio: PortfolioRequest,
    ) -> PortfolioEvidence:
        intent = classify_portfolio_chat_intent(request.question)
        named_tickers = _extract_named_tickers(request.question, portfolio)
        tools_planned = plan_portfolio_chat_tools(
            intent,
            named_tickers=named_tickers,
        )
        relevant_tickers = named_tickers or [
            holding.ticker for holding in portfolio.holdings
        ]
        enrichment: dict[str, dict[str, float | str]] = {}
        caveats: list[str] = []
        evidence_used: list[str] = []
        tools_called: list[str] = []
        tools_succeeded: list[str] = []
        tools_failed: list[str] = []
        market_evidence: dict[str, MarketEvidence] = {}
        news_evidence: dict[str, list[NewsEvidence]] = {}
        earnings_evidence: dict[str, EarningsEvidence] = {}
        signal_evidence: dict[str, SignalEvidence] = {}
        generated_at = datetime.now(timezone.utc).isoformat()

        if "market_data" in tools_planned:
            for ticker in relevant_tickers[:5]:
                tools_called.append("market_data")
                try:
                    market_data = fetch_market_data(
                        MarketDataRequest(
                            ticker=ticker,
                            lookback_days=30,
                            include_technicals=False,
                        )
                    )
                    enrichment[ticker] = {
                        "current_price": market_data.current_price,
                        "market": market_data.market,
                    }
                    market_evidence[ticker] = MarketEvidence(
                        ticker=ticker,
                        market=market_data.market,
                        current_price=market_data.current_price,
                        as_of=market_data.as_of,
                    )
                    evidence_used.append("market_data")
                    tools_succeeded.append("market_data")
                except Exception:
                    caveats.append(f"Current price evidence was unavailable for {ticker}.")
                    tools_failed.append("market_data")

        for holding in portfolio.holdings:
            data = enrichment.get(holding.ticker)
            if data:
                continue
            if holding.current_price is not None:
                enrichment[holding.ticker] = {
                    "current_price": holding.current_price,
                    "market": "TW" if holding.ticker.endswith(".TW") else "US",
                }
                market_evidence[holding.ticker] = MarketEvidence(
                    ticker=holding.ticker,
                    market="TW" if holding.ticker.endswith(".TW") else "US",
                    current_price=holding.current_price,
                    as_of=generated_at,
                )

        if "named_holding_context" in tools_planned and named_tickers:
            evidence_used.append("named_holding_context")

        if "signal" in tools_planned:
            for ticker in relevant_tickers[:3]:
                tools_called.append("signal")
                try:
                    signal = fetch_signal(SignalToolRequest(ticker=ticker))
                    evidence_used.append("signal")
                    tools_succeeded.append("signal")
                    signal_evidence[ticker] = SignalEvidence(
                        ticker=signal.ticker,
                        benchmark=signal.benchmark,
                        horizon_days=signal.horizon_days,
                        signal_score=signal.signal_score,
                        signal_band=signal.signal_band,
                        confidence=signal.confidence,
                        positive_signals=signal.positive_signals,
                        negative_signals=signal.negative_signals,
                        data_caveats=signal.data_caveats,
                        disclaimer=signal.disclaimer,
                    )
                    if signal.confidence == "Low":
                        caveats.append(f"Signal confidence was low for {ticker}.")
                    caveats.extend(signal.data_caveats[:2])
                except Exception:
                    caveats.append(f"Signal evidence was unavailable for {ticker}.")
                    tools_failed.append("signal")

        if "news" in tools_planned:
            for ticker in relevant_tickers[:3]:
                tools_called.append("news")
                try:
                    news = fetch_news(NewsRequest(ticker=ticker, max_articles=3))
                    evidence_used.append("news")
                    tools_succeeded.append("news")
                    news_evidence[ticker] = [
                        NewsEvidence(
                            ticker=ticker,
                            title=article.title,
                            published_at=article.published_at,
                            source=article.source,
                            summary=article.summary,
                            url=article.url,
                            sentiment=article.sentiment,
                            retrieved_at=generated_at,
                        )
                        for article in news.articles[:3]
                    ]
                    if news.total_articles == 0:
                        caveats.append(f"Recent news coverage was limited for {ticker}.")
                except Exception:
                    caveats.append(f"Recent news evidence was unavailable for {ticker}.")
                    tools_failed.append("news")

        if "earnings" in tools_planned:
            for ticker in relevant_tickers[:3]:
                tools_called.append("earnings")
                try:
                    earnings = fetch_earnings(EarningsRequest(ticker=ticker))
                    evidence_used.append("earnings")
                    tools_succeeded.append("earnings")
                    latest_report_date = (
                        earnings.earnings_history[0].report_date
                        if earnings.earnings_history
                        else None
                    )
                    earnings_caveats: list[str] = []
                    if earnings.next_earnings is None:
                        earnings_caveats.append(
                            f"Earnings timing was unavailable for {ticker}."
                        )
                    earnings_evidence[ticker] = EarningsEvidence(
                        ticker=ticker,
                        next_earnings_date=(
                            earnings.next_earnings.report_date
                            if earnings.next_earnings
                            else None
                        ),
                        days_to_next_earnings=earnings.days_to_next_earnings,
                        latest_report_date=latest_report_date,
                        avg_eps_surprise_pct=earnings.avg_eps_surprise_pct,
                        avg_post_earnings_move_pct=earnings.avg_post_earnings_move_pct,
                        beat_rate=earnings.beat_rate,
                        caveats=earnings_caveats,
                    )
                    caveats.extend(earnings_caveats)
                except Exception:
                    caveats.append(f"Earnings timing was unavailable for {ticker}.")
                    tools_failed.append("earnings")

        return PortfolioEvidence(
            intent=intent,
            named_tickers=named_tickers,
            enrichment=enrichment,
            caveats=sorted(set(caveats)),
            evidence_used=_dedupe_preserve_order(evidence_used),
            tools_planned=tools_planned,
            tools_called=_dedupe_preserve_order(tools_called),
            tools_succeeded=_dedupe_preserve_order(tools_succeeded),
            tools_failed=_dedupe_preserve_order(tools_failed),
            market_data=market_evidence,
            news=news_evidence,
            earnings=earnings_evidence,
            signals=signal_evidence,
            data_as_of=generated_at,
        )

    def resolve_portfolio(
        self,
        request: PortfolioChatRequest,
    ) -> ResolvedPortfolioContext:
        if request.portfolio is not None:
            return ResolvedPortfolioContext(
                portfolio=request.portfolio,
                source="direct_portfolio",
            )

        if request.workspace_id:
            record = self.store.load_portfolio(request.workspace_id)
            if record is None:
                raise ValueError(f"Saved workspace '{request.workspace_id}' was not found.")
            return ResolvedPortfolioContext(
                portfolio=record.portfolio,
                source="saved_workspace",
            )

        raise ValueError(
            "A portfolio or workspace_id is required to build portfolio context."
        )

    def build_context(
        self,
        request: PortfolioChatRequest,
        evidence: PortfolioEvidence | None = None,
    ) -> PortfolioContext:
        resolved = self.resolve_portfolio(request)
        evidence = evidence or self.build_evidence(request, resolved.portfolio)
        analysis = calculate_portfolio_metrics(
            resolved.portfolio,
            enrichment=evidence.enrichment,
        )
        data_caveats = list(analysis.missing_data)
        incomplete_classification = any(
            not (holding.asset_type or holding.category)
            for holding in resolved.portfolio.holdings
        )
        if incomplete_classification and any(
            "Defensive allocation" in flag for flag in analysis.risk_flags
        ):
            data_caveats.append(
                "Portfolio classification data was incomplete, so defensive "
                "allocation conclusions are only rough checks."
            )
        context_holdings = [
            _holding_to_context_holding(
                holding_input,
                analysis_holding,
            )
            for holding_input, analysis_holding in zip(
                resolved.portfolio.holdings,
                analysis.holdings,
                strict=False,
            )
        ]
        coverage = _build_coverage_snapshot(context_holdings, resolved.portfolio.holdings)
        allocation_complete = coverage.allocation_complete
        if not allocation_complete:
            data_caveats.append(
                "Portfolio allocation coverage was incomplete because some "
                "material holdings lack current prices."
            )
            context_holdings = [
                holding.model_copy(update={"weight_pct": None})
                for holding in context_holdings
            ]

        top_holdings = sorted(
            context_holdings,
            key=(
                (lambda item: item.weight_pct or 0.0)
                if allocation_complete
                else (lambda item: item.cost_basis or 0.0)
            ),
            reverse=True,
        )[:5]
        review_items: list[ReviewItem] = []
        if analysis.portfolio_intelligence is not None:
            review_items = analysis.portfolio_intelligence.suggested_review_items
        if not allocation_complete:
            review_items = [
                item
                for item in review_items
                if not any("concentration." in key for key in item.evidence_keys)
            ]
            review_items.insert(
                0,
                ReviewItem(
                    title="Review incomplete current allocation coverage",
                    reason=(
                        "Current portfolio weights could not be calculated "
                        "completely because some material holdings lack current prices."
                    ),
                    evidence_keys=["coverage.allocation_complete"],
                    severity="medium",
                ),
            )
        risk_flags = analysis.risk_flags
        if not allocation_complete:
            risk_flags = [
                flag
                for flag in risk_flags
                if "concentration" not in flag.lower()
            ]
        if incomplete_classification or not allocation_complete:
            risk_flags = [
                flag
                for flag in risk_flags
                if "defensive allocation" not in flag.lower()
            ]

        return PortfolioContext(
            total_current_value=(
                analysis.total_current_value if allocation_complete else None
            ),
            total_cost_basis=analysis.total_cost_basis,
            total_unrealized_gain_loss=(
                analysis.total_unrealized_gain_loss if allocation_complete else None
            ),
            total_return_pct=analysis.total_return_pct if allocation_complete else None,
            top_holdings=top_holdings,
            risk_flags=risk_flags,
            suggested_review_items=review_items,
            concentration_summary=(
                _summarise_concentration(analysis)
                if allocation_complete
                else (
                    "Current allocation is incomplete because one or more "
                    "material holdings lack current prices."
                )
            ),
            income_summary=_summarise_income(analysis),
            holdings=context_holdings,
            data_caveats=sorted(set([*data_caveats, *evidence.caveats])),
            coverage=coverage,
        )

    def build_response(self, request: PortfolioChatRequest) -> PortfolioChatResponse:
        request_id = str(uuid.uuid4())
        language = _pick_language(request)
        resolved = self.resolve_portfolio(request)
        evidence = self.build_evidence(request, resolved.portfolio)
        context = self.build_context(
            request.model_copy(update={"portfolio": resolved.portfolio}),
            evidence=evidence,
        )
        caveats_before_dedup = [*context.data_caveats, *evidence.caveats]
        user_caveats = _build_user_caveats(
            context,
            evidence.caveats,
            language=language,
        )
        evidence.caveats_before_dedup = caveats_before_dedup
        evidence.user_caveats = user_caveats
        context = context.model_copy(update={"data_caveats": user_caveats})
        evidence.bundle = _build_evidence_bundle(context, evidence)
        generation = _build_llm_answer(
            request.question,
            evidence.bundle,
            language=language,
            intent=evidence.intent,
            named_tickers=evidence.named_tickers,
            evidence_caveats=user_caveats,
        )
        if generation.answer and _has_grounding_violation(generation.answer):
            logger.warning(
                "Portfolio chat LLM answer failed grounding validation; using fallback",
                extra={
                    "request_id": request_id,
                    "provider": generation.provider,
                    "model": generation.model,
                    "intent": evidence.intent,
                },
            )
            generation = PortfolioChatGeneration(
                answer=None,
                mode="deterministic",
                provider=generation.provider,
                model=generation.model,
                fallback_used=True,
            )
        evidence_used = [
            resolved.source,
            "portfolio_calculator",
            (
                "portfolio_intelligence"
                if context.suggested_review_items
                else "base_portfolio_analysis"
            ),
            *evidence.evidence_used,
        ]
        if generation.answer is not None:
            evidence_used.append("llm_portfolio_chat")
        metadata = {
            "mode": generation.mode,
            "provider": generation.provider,
            "model": generation.model,
            "fallback_used": generation.fallback_used,
            "request_id": request_id,
            "intent": evidence.intent,
            "tools_planned": evidence.tools_planned,
            "tools_called": evidence.tools_called,
            "tools_succeeded": evidence.tools_succeeded,
            "tools_failed": evidence.tools_failed,
            "data_as_of": evidence.data_as_of,
            "evidence_available": _dedupe_preserve_order(
                [
                    *evidence.evidence_used,
                    *list(evidence.market_data.keys()),
                    *list(evidence.signals.keys()),
                    *list(evidence.news.keys()),
                    *list(evidence.earnings.keys()),
                ]
            ),
            "evidence_missing": evidence.tools_failed,
            "caveats_before_dedup": caveats_before_dedup,
            "caveats_after_dedup": user_caveats,
        }
        logger.info(
            "Portfolio chat generation completed",
            extra={
                "request_id": request_id,
                "mode": generation.mode,
                "provider": generation.provider,
                "model": generation.model,
                "fallback_used": generation.fallback_used,
                "intent": evidence.intent,
            },
        )
        return PortfolioChatResponse(
            answer=generation.answer
            if generation.answer is not None
            else _build_answer(
                request.question,
                context,
                language=language,
                intent=evidence.intent,
                named_tickers=evidence.named_tickers,
                evidence_caveats=user_caveats,
            ),
            portfolio_context=context,
            evidence_used=_dedupe_preserve_order(evidence_used),
            suggested_followups=_build_followups(language, evidence.intent),
            safety_disclaimer=ZH_DISCLAIMER if language == "zh" else EN_DISCLAIMER,
            generation_metadata=metadata if _generation_metadata_enabled() else None,
        )
