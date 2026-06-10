from __future__ import annotations

from dataclasses import dataclass

try:
    from ..schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from ..schemas.portfolio_chat import (
        PortfolioChatRequest,
        PortfolioChatResponse,
        PortfolioContext,
        PortfolioContextHolding,
    )
    from ..schemas.portfolio_intelligence import ReviewItem
    from ..services.portfolio_calculator import calculate_portfolio_metrics
    from ..services.portfolio_store import PortfolioStore
except ImportError:
    from schemas.portfolio import (
        HoldingInput,
        HoldingMetrics,
        PortfolioAnalysisResponse,
        PortfolioRequest,
    )
    from schemas.portfolio_chat import (
        PortfolioChatRequest,
        PortfolioChatResponse,
        PortfolioContext,
        PortfolioContextHolding,
    )
    from schemas.portfolio_intelligence import ReviewItem
    from services.portfolio_calculator import calculate_portfolio_metrics
    from services.portfolio_store import PortfolioStore


EN_DISCLAIMER = "This is an educational portfolio review, not financial advice."
ZH_DISCLAIMER = "這是教育用途的投資組合檢視，不構成投資建議。"


@dataclass
class ResolvedPortfolioContext:
    portfolio: PortfolioRequest
    source: str


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _pick_language(request: PortfolioChatRequest) -> str:
    if request.language in {"en", "zh"}:
        return request.language
    return "zh" if _contains_cjk(request.question) else "en"


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


def _build_followups(language: str) -> list[str]:
    if language == "zh":
        return [
            "我是不是太集中在單一持股或主題？",
            "如果科技股回檔，我的風險門檻會怎麼變化？",
            "哪些持股需要優先檢視未實現虧損或收入穩定性？",
        ]
    return [
        "Is my portfolio too concentrated in one holding or theme?",
        "How would a technology drawdown affect my current risk threshold?",
        "Which holdings deserve the first review for losses or income stability?",
    ]


def _build_answer(
    question: str,
    context: PortfolioContext,
    *,
    language: str,
) -> str:
    review_items = context.suggested_review_items[:4]
    if language == "zh":
        review_lines = [
            f"- {item.title}: {item.reason}"
            for item in review_items
        ] or [
            "- 目前沒有觸發新的高優先檢查項目，建議持續留意集中度與資料完整性。"
        ]
        return "\n".join(
            [
                f"問題重點：{question}",
                (
                    f"目前投資組合市值約為 {context.total_current_value or 0:.2f}，"
                    f"未實現損益約為 {context.total_unrealized_gain_loss or 0:.2f}。"
                ),
                f"集中度摘要：{context.concentration_summary}",
                f"收益摘要：{context.income_summary}",
                "建議優先檢視：",
                *review_lines,
                "後續可以考慮做情境比較、壓力測試，或持續監控集中風險門檻與資料缺口。",
            ]
        )

    review_lines = [
        f"- {item.title}: {item.reason}"
        for item in review_items
    ] or [
        "- No new high-priority review item was triggered, so continue "
        "monitoring concentration and data quality."
    ]
    return "\n".join(
        [
            f"Question acknowledged: {question}",
            (
                f"Current portfolio value is approximately {context.total_current_value or 0:.2f}, "
                f"with unrealized P/L near {context.total_unrealized_gain_loss or 0:.2f}."
            ),
            f"Concentration summary: {context.concentration_summary}",
            f"Income summary: {context.income_summary}",
            "Suggested review items:",
            *review_lines,
            "Consider a scenario review, stress test, or concentration threshold "
            "check before changing assumptions.",
        ]
    )


class PortfolioContextBuilder:
    def __init__(self, store: PortfolioStore | None = None) -> None:
        self.store = store or PortfolioStore()

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

    def build_context(self, request: PortfolioChatRequest) -> PortfolioContext:
        resolved = self.resolve_portfolio(request)
        analysis = calculate_portfolio_metrics(resolved.portfolio)
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
        top_holdings = sorted(
            context_holdings,
            key=lambda item: item.weight_pct or 0.0,
            reverse=True,
        )[:5]
        review_items: list[ReviewItem] = []
        if analysis.portfolio_intelligence is not None:
            review_items = analysis.portfolio_intelligence.suggested_review_items

        return PortfolioContext(
            total_current_value=analysis.total_current_value,
            total_cost_basis=analysis.total_cost_basis,
            total_unrealized_gain_loss=analysis.total_unrealized_gain_loss,
            total_return_pct=analysis.total_return_pct,
            top_holdings=top_holdings,
            risk_flags=analysis.risk_flags,
            suggested_review_items=review_items,
            concentration_summary=_summarise_concentration(analysis),
            income_summary=_summarise_income(analysis),
            holdings=context_holdings,
            data_caveats=analysis.missing_data,
        )

    def build_response(self, request: PortfolioChatRequest) -> PortfolioChatResponse:
        language = _pick_language(request)
        resolved = self.resolve_portfolio(request)
        context = self.build_context(
            request.model_copy(update={"portfolio": resolved.portfolio})
        )
        evidence_used = [
            resolved.source,
            "portfolio_calculator",
            (
                "portfolio_intelligence"
                if context.suggested_review_items
                else "base_portfolio_analysis"
            ),
        ]
        return PortfolioChatResponse(
            answer=_build_answer(request.question, context, language=language),
            portfolio_context=context,
            evidence_used=evidence_used,
            suggested_followups=_build_followups(language),
            safety_disclaimer=ZH_DISCLAIMER if language == "zh" else EN_DISCLAIMER,
        )
