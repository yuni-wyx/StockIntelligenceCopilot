"""
Stock Intelligence Copilot — CLI Entrypoint
============================================

Usage:
    python main.py research NVDA
    python main.py explain TSLA
    python main.py watchlist AAPL NVDA MSFT

Pipeline stages executed in order:
    1. Intent Classification Chain
    2. Planning Chain
    3. Tool Router  (tool dispatch)
    4. Evidence Aggregator
    5. Synthesis Chain
    6. Rich terminal output
"""

from __future__ import annotations

import sys
import time

# Zero-dependency shim — must come before any project imports.
# No-op when langchain/pydantic are properly installed.
import backend.compat as compat  # noqa: F401
from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ── Pipeline components ───────────────────────────────────────────────────────
from backend.chains.intent_chain import build_intent_chain
from backend.chains.planner_chain import build_planner_chain
from backend.chains.synthesis_chain import SynthesisInput, build_synthesis_chain
from backend.schemas.intent_schema import IntentInput
from backend.schemas.output_schema import (
    PriceMovementOutput,
    StockResearchOutput,
    WatchlistMonitorOutput,
)
from backend.services.evidence_aggregator import EvidenceAggregator
from backend.services.tool_router import ToolRouter

console = Console(width=110)


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def run_pipeline(raw_query: str) -> None:
    """Execute the full 6-stage pipeline and render results."""
    console.print()
    console.rule("[bold cyan]Stock Intelligence Copilot[/bold cyan]")
    console.print(f"  [dim]Query:[/dim] [italic]{raw_query}[/italic]\n")

    t0 = time.perf_counter()

    # ── Stage 1: Intent Classification ───────────────────────────────────────
    _stage("1", "Intent Classification")
    intent_chain = build_intent_chain()
    intent = intent_chain.invoke(IntentInput(raw_query=raw_query))
    console.print(
        f"  Mode: [bold green]{intent.mode}[/bold green]  |  "
        f"Tickers: [bold yellow]{', '.join(intent.tickers)}[/bold yellow]  |  "
        f"Confidence: {intent.confidence:.0%}"
    )
    console.print(f"  [dim]{intent.reasoning}[/dim]\n")

    # ── Stage 2: Planning ─────────────────────────────────────────────────────
    _stage("2", "Planning")
    planner_chain = build_planner_chain()
    plan = planner_chain.invoke(intent)
    console.print(f"  {len(plan.tool_calls)} tool call(s) planned across {len(plan.tickers)} ticker(s).")
    console.print(f"  Focus: [italic]{plan.analysis_focus}[/italic]\n")

    # ── Stage 3+4: Tool Routing & Execution ───────────────────────────────────
    _stage("3+4", "Tool Routing & Execution")
    router = ToolRouter()
    tool_results = router.execute(plan)
    ok = sum(1 for r in tool_results if r.success)
    console.print(f"  {ok}/{len(tool_results)} tool calls succeeded.\n")
    for r in tool_results:
        status = "[green]✓[/green]" if r.success else "[red]✗[/red]"
        console.print(f"  {status} [{r.ticker}] {r.tool}")

    console.print()

    # ── Stage 5: Evidence Aggregation ─────────────────────────────────────────
    _stage("5", "Evidence Aggregation")
    aggregator = EvidenceAggregator()
    evidence = aggregator.aggregate(tool_results, plan)
    console.print(
        f"  Success rate: {evidence.success_rate:.0%}  |  "
        f"Tickers with evidence: {len(evidence.tickers_evidence)}\n"
    )

    # ── Stage 6: Synthesis ────────────────────────────────────────────────────
    _stage("6", "Synthesis")
    synthesis_chain = build_synthesis_chain()
    output = synthesis_chain.invoke(SynthesisInput(evidence=evidence, plan=plan))

    elapsed = time.perf_counter() - t0
    console.print(f"  [dim]Pipeline completed in {elapsed:.2f}s[/dim]\n")
    console.rule("[bold cyan]Report[/bold cyan]")
    console.print()

    # ── Render output ─────────────────────────────────────────────────────────
    if isinstance(output, StockResearchOutput):
        _render_research(output)
    elif isinstance(output, PriceMovementOutput):
        _render_movement(output)
    elif isinstance(output, WatchlistMonitorOutput):
        _render_watchlist(output)
    else:
        console.print(output)


# ── Renderers ─────────────────────────────────────────────────────────────────

def _stage(num: str, name: str) -> None:
    console.print(f"[bold magenta]Stage {num}[/bold magenta] — [bold]{name}[/bold]")


def _render_research(out: StockResearchOutput) -> None:
    sentiment_colour = {"BULLISH": "green", "BEARISH": "red", "NEUTRAL": "yellow"}.get(
        out.overall_sentiment, "white"
    )
    console.print(Panel(
        f"[bold]{out.ticker}[/bold]  •  "
        f"Sentiment: [bold {sentiment_colour}]{out.overall_sentiment}[/bold {sentiment_colour}]  •  "
        f"Generated: {out.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        title="[bold cyan]Stock Research Report[/bold cyan]",
        box=box.ROUNDED,
    ))

    _section("Fundamental Summary", out.fundamental_summary)
    _section("Recent News", out.recent_news_summary)

    console.print(Panel(out.bull_case, title="[green]Bull Case[/green]", border_style="green"))
    console.print(Panel(out.bear_case, title="[red]Bear Case[/red]", border_style="red"))

    _watch_table(out.what_to_watch_next)


def _render_movement(out: PriceMovementOutput) -> None:
    pct = out.price_change_pct
    pct_colour = "green" if pct >= 0 else "red"
    sign = "+" if pct >= 0 else ""

    console.print(Panel(
        f"[bold]{out.ticker}[/bold]  •  "
        f"Move: [bold {pct_colour}]{sign}{pct:.2f}%[/bold {pct_colour}]  •  "
        f"Overall confidence: [bold]{out.overall_confidence:.0%}[/bold]",
        title="[bold cyan]Price Movement Explanation[/bold cyan]",
        box=box.ROUNDED,
    ))

    _section("Price Action Summary", out.price_move_summary)

    # Ranked causes table
    table = Table(
        title="Ranked Causes", box=box.SIMPLE_HEAD,
        show_header=True, header_style="bold magenta",
    )
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Cause", width=26)
    table.add_column("Confidence", width=14)
    table.add_column("Explanation", width=55)

    conf_colours = {"HIGH": "green", "MEDIUM": "yellow", "LOW": "dim"}
    for c in out.ranked_causes:
        col = conf_colours.get(c.confidence_label, "white")
        table.add_row(
            f"#{c.rank}",
            c.cause,
            f"[{col}]{c.confidence_label} ({c.confidence:.0%})[/{col}]",
            c.explanation[:120],
        )

    console.print(table)
    console.print()

    # Evidence bullets for top cause
    if out.ranked_causes:
        top = out.ranked_causes[0]
        console.print(f"[bold]Supporting evidence for #{top.rank} ({top.cause}):[/bold]")
        for ev in top.supporting_evidence:
            console.print(f"  • {ev}")
        console.print()

    _watch_table(out.what_to_watch_next)


def _render_watchlist(out: WatchlistMonitorOutput) -> None:
    console.print(Panel(
        f"Tickers: [bold yellow]{', '.join(out.tickers)}[/bold yellow]  •  "
        f"Generated: {out.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        title="[bold cyan]Watchlist Monitor — Weekly Report[/bold cyan]",
        box=box.ROUNDED,
    ))

    _section("Portfolio Summary", out.portfolio_summary)

    # Per-ticker summaries
    for ts in out.ticker_summaries:
        mom_colour = {
            "STRONG_UP": "green", "UP": "green", "FLAT": "yellow",
            "DOWN": "red", "STRONG_DOWN": "red",
        }.get(ts.momentum, "white")

        console.print(Rule(
            f"[bold yellow]{ts.ticker}[/bold yellow]  "
            f"[{mom_colour}]{ts.momentum}[/{mom_colour}]"
        ))
        console.print(f"  {ts.weekly_highlights}")
        if ts.major_news:
            console.print("  [bold]News:[/bold]")
            for h in ts.major_news:
                console.print(f"    • {h}")
        console.print(f"  [bold]Earnings:[/bold] {ts.earnings_events}")
        if ts.risk_signals:
            console.print("  [bold red]Risk signals:[/bold red]")
            for r in ts.risk_signals:
                console.print(f"    ⚠  {r}")
        console.print()

    # Macro risks
    console.print("[bold red]Macro Risks:[/bold red]")
    for r in out.macro_risks:
        console.print(f"  ⚠  {r}")
    console.print()

    # Top opportunities
    console.print("[bold green]Top Opportunities:[/bold green]")
    for o in out.top_opportunities:
        console.print(f"  ★  {o}")
    console.print()

    # Next-week watchpoints per ticker
    for ts in out.ticker_summaries:
        if ts.next_week_watchpoints:
            console.print(f"[bold]{ts.ticker} — Next Week Watchpoints:[/bold]")
            for wp in ts.next_week_watchpoints:
                console.print(f"  → {wp.item} ({wp.timeframe}): {wp.reason}")
    console.print()


def _section(title: str, body: str) -> None:
    console.print(f"[bold underline]{title}[/bold underline]")
    console.print(f"  {body}\n")


def _watch_table(watch_points: list) -> None:
    if not watch_points:
        return
    table = Table(
        title="What to Watch Next", box=box.SIMPLE_HEAD,
        show_header=True, header_style="bold cyan",
    )
    table.add_column("Item", width=36)
    table.add_column("Timeframe", width=14)
    table.add_column("Reason", width=55)
    for wp in watch_points:
        table.add_row(wp.item, wp.timeframe, wp.reason)
    console.print(table)
    console.print()


# ── CLI dispatcher ────────────────────────────────────────────────────────────

USAGE = """
[bold]Stock Intelligence Copilot[/bold]

Usage:
  python main.py research  <TICKER>
  python main.py explain   <TICKER>
  python main.py watchlist <TICKER1> [TICKER2 ...]

Examples:
  python main.py research  NVDA
  python main.py explain   TSLA
  python main.py watchlist AAPL NVDA MSFT
"""


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        console.print(USAGE)
        sys.exit(0)

    verb = argv[1].lower()
    args = argv[2:]

    if verb not in ("research", "explain", "watchlist"):
        console.print(f"[red]Unknown command:[/red] {verb}")
        console.print(USAGE)
        sys.exit(1)

    if not args:
        console.print(f"[red]Please provide at least one ticker symbol.[/red]")
        sys.exit(1)

    tickers_str = " ".join(a.upper() for a in args)
    raw_query = f"{verb} {tickers_str}"

    try:
        run_pipeline(raw_query)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
