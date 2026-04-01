"""
Intent Classification Chain
-----------------------------
Stage 1 of the pipeline.

Input  : IntentInput  (raw_query: str)
Output : IntentOutput (mode, tickers, confidence, reasoning)

This chain uses rule-based heuristics (fast, zero-cost, deterministic)
instead of an LLM call since intent is fully inferable from CLI commands.
Swap the _classify() function with an LLM call if you need open-ended NL input.
"""

from __future__ import annotations

from typing import List

from langchain_core.runnables import RunnableLambda

try:
    from ..schemas.intent_schema import AnalysisMode, IntentInput, IntentOutput
    from ..symbols import extract_symbols_from_text
except ImportError:
    from schemas.intent_schema import AnalysisMode, IntentInput, IntentOutput
    from symbols import extract_symbols_from_text


def _extract_tickers(text: str) -> List[str]:
    """
    Extract stock tickers from text.

    Supports:
    - US tickers: NVDA, TSLA
    - Taiwan tickers: 2330.TW
    - Dotted tickers: BRK.B
    """
    return extract_symbols_from_text(text)


def _classify(raw_query: str) -> IntentOutput:
    """
    Rule-based classifier. Maps CLI verbs to AnalysisMode.
    Extend with fuzzy matching or an LLM call for free-form text.
    """
    q = raw_query.strip().lower()
    tickers_found = _extract_tickers(raw_query)

    if q.startswith("research ") or q.startswith("analyze ") or q.startswith("deep dive "):
        mode = AnalysisMode.STOCK_RESEARCH
        confidence = 0.98
        reasoning = "Query starts with a research/analysis verb targeting a ticker."

    elif q.startswith("explain ") or q.startswith("why ") or q.startswith("move "):
        mode = AnalysisMode.PRICE_MOVEMENT
        confidence = 0.96
        reasoning = "Query starts with an explanation verb, signalling price movement analysis."

    elif q.startswith("watchlist ") or q.startswith("monitor ") or q.startswith("watch "):
        mode = AnalysisMode.WATCHLIST_MONITOR
        confidence = 0.97
        reasoning = (
            "Query starts with a monitoring verb and contains one "
            "or more ticker candidates."
        )

    elif q.startswith("trade ") or q.startswith("decision ") or q.startswith("setup "):
        mode = AnalysisMode.TRADE
        confidence = 0.98
        reasoning = "Query starts with a trading decision verb, signalling trade setup analysis."

    else:
        if len(tickers_found) > 1:
            mode = AnalysisMode.WATCHLIST_MONITOR
            confidence = 0.72
            reasoning = (
                "Multiple tickers detected with no explicit verb; "
                "defaulting to watchlist mode."
            )
        else:
            mode = AnalysisMode.STOCK_RESEARCH
            confidence = 0.65
            reasoning = "Single ticker detected with no explicit verb; defaulting to research mode."

    if not tickers_found:
        raise ValueError(
            f"No ticker symbol detected in query: '{raw_query}'. "
            "Please include at least one uppercase ticker (e.g. NVDA, AAPL)."
        )

    return IntentOutput(
        mode=mode,
        tickers=tickers_found,
        confidence=confidence,
        reasoning=reasoning,
    )


def build_intent_chain() -> RunnableLambda:
    """
    Returns the Intent Classification Chain as a LangChain Runnable.

    Usage:
        chain = build_intent_chain()
        result: IntentOutput = chain.invoke(IntentInput(raw_query="research NVDA"))
    """
    def _run(inp: IntentInput) -> IntentOutput:
        return _classify(inp.raw_query)

    return RunnableLambda(_run).with_config(run_name="IntentClassificationChain")
