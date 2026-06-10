from __future__ import annotations

try:
    from ..schemas.portfolio_chat import PortfolioChatRequest, PortfolioChatResponse
    from ..services.portfolio_context_builder import PortfolioContextBuilder
    from ..services.portfolio_store import PortfolioStore
except ImportError:
    from schemas.portfolio_chat import PortfolioChatRequest, PortfolioChatResponse
    from services.portfolio_context_builder import PortfolioContextBuilder
    from services.portfolio_store import PortfolioStore


class PortfolioChatOrchestrator:
    def __init__(self, store: PortfolioStore | None = None) -> None:
        self.builder = PortfolioContextBuilder(store=store)

    def orchestrate(self, request: PortfolioChatRequest) -> PortfolioChatResponse:
        return self.builder.build_response(request)
