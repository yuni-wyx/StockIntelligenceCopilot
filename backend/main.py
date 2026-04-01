# ruff: noqa: E402
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv

# Load env BEFORE importing chains/tools that may need env vars.
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

if __package__:
    from . import compat as compat  # noqa: F401
    from .api.presentation import build_sse_response, error_output, serialize_output
    from .pipeline.orchestrator import execute_pipeline, stream_pipeline_events
    from .schemas.output_schema import (
        PriceMovementOutput,
        StockResearchOutput,
        TradingDecisionOutput,
        WatchlistMonitorOutput,
    )
    from .symbols import normalize_symbol
else:
    import compat as compat  # noqa: F401
    from api.presentation import build_sse_response, error_output, serialize_output
    from pipeline.orchestrator import execute_pipeline, stream_pipeline_events
    from schemas.output_schema import (
        PriceMovementOutput,
        StockResearchOutput,
        TradingDecisionOutput,
        WatchlistMonitorOutput,
    )
    from symbols import normalize_symbol

console = Console(width=110)


def _cors_origins_from_env() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Stock Intelligence Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_from_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    ticker: str


class ExplainRequest(BaseModel):
    ticker: str


class WatchlistRequest(BaseModel):
    tickers: List[str]


class TradeRequest(BaseModel):
    ticker: str


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {"message": "Stock Intelligence Copilot API is running."}


@app.post("/api/research")
def api_research(req: ResearchRequest) -> dict:
    raw_query = f"research {normalize_symbol(req.ticker)}"
    try:
        output = execute_pipeline(raw_query)
        return serialize_output(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_output(raw_query, e)


@app.post("/api/explain")
def api_explain(req: ExplainRequest) -> dict:
    raw_query = f"explain {normalize_symbol(req.ticker)}"
    try:
        output = execute_pipeline(raw_query)
        return serialize_output(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_output(raw_query, e)


@app.post("/api/watchlist")
def api_watchlist(req: WatchlistRequest) -> dict:
    tickers_str = " ".join(normalize_symbol(t) for t in req.tickers)
    raw_query = f"watchlist {tickers_str}"
    try:
        output = execute_pipeline(raw_query)
        return serialize_output(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_output(raw_query, e)


@app.post("/api/trade")
def api_trade(req: TradeRequest) -> dict:
    raw_query = f"trade {normalize_symbol(req.ticker)}"
    try:
        output = execute_pipeline(raw_query)
        return serialize_output(output)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_output(raw_query, e)


@app.post("/api/research/stream")
def api_research_stream(req: ResearchRequest):
    raw_query = f"research {normalize_symbol(req.ticker)}"
    return build_sse_response(raw_query, stream_pipeline_events)


@app.post("/api/explain/stream")
def api_explain_stream(req: ExplainRequest):
    raw_query = f"explain {normalize_symbol(req.ticker)}"
    return build_sse_response(raw_query, stream_pipeline_events)


@app.post("/api/trade/stream")
def api_trade_stream(req: TradeRequest):
    raw_query = f"trade {normalize_symbol(req.ticker)}"
    return build_sse_response(raw_query, stream_pipeline_events)


# ── CLI renderer path (streaming UI) ─────────────────────────────────────────

def run_pipeline_streaming(raw_query: str) -> None:
    console.print()
    console.rule("[bold cyan]Stock Intelligence Copilot[/bold cyan]")
    console.print(f"  [dim]Query:[/dim] [italic]{raw_query}[/italic]\n")

    final_output: Any = None
    elapsed = 0.0

    for event in stream_pipeline_events(raw_query):
        etype = event["type"]

        if etype == "status":
            console.print(f"[dim]{event['message']}[/dim]")

        elif etype == "stage_start":
            console.print(f"[bold magenta]→ {event['message']}...[/bold magenta]")

        elif etype == "stage_done":
            console.print(f"[green]✓ {event['stage']} complete[/green]")

        elif etype == "tool_result":
            status = "[green]✓[/green]" if event["success"] else "[red]✗[/red]"
            console.print(f"   {status} [{event['ticker']}] {event['tool']}")

        elif etype == "final_output":
            final_output = event["data"]
            elapsed = event["elapsed"]

    console.print(f"\n[dim]Pipeline completed in {elapsed:.2f}s[/dim]\n")
    console.rule("[bold cyan]Report[/bold cyan]")
    console.print()

    if isinstance(final_output, StockResearchOutput):
        _render_research(final_output)
    elif isinstance(final_output, PriceMovementOutput):
        _render_movement(final_output)
    elif isinstance(final_output, WatchlistMonitorOutput):
        _render_watchlist(final_output)
    elif isinstance(final_output, TradingDecisionOutput):
        _render_trade(final_output)
    else:
        console.print(final_output)


# ── Renderers ─────────────────────────────────────────────────────────────────

def _render_research(out: StockResearchOutput) -> None:
    sentiment_colour = {"BULLISH": "green", "BEARISH": "red", "NEUTRAL": "yellow"}.get(
        out.overall_sentiment, "white"
    )
    console.print(
        Panel(
            f"[bold]{out.ticker}[/bold]  •  "
            "Sentiment: "
            f"[bold {sentiment_colour}]{out.overall_sentiment}"
            f"[/bold {sentiment_colour}]  •  "
            f"Generated: {out.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            title="[bold cyan]Stock Research Report[/bold cyan]",
            box=box.ROUNDED,
        )
    )

    _section("Fundamental Summary", out.fundamental_summary)
    _section("Recent News", out.recent_news_summary)

    console.print(Panel(out.bull_case, title="[green]Bull Case[/green]", border_style="green"))
    console.print(Panel(out.bear_case, title="[red]Bear Case[/red]", border_style="red"))

    _watch_table(out.what_to_watch_next)


def _render_movement(out: PriceMovementOutput) -> None:
    pct = out.price_change_pct
    pct_colour = "green" if pct >= 0 else "red"
    sign = "+" if pct >= 0 else ""

    console.print(
        Panel(
            f"[bold]{out.ticker}[/bold]  •  "
            f"Move: [bold {pct_colour}]{sign}{pct:.2f}%[/bold {pct_colour}]  •  "
            f"Overall confidence: [bold]{out.overall_confidence:.0%}[/bold]",
            title="[bold cyan]Price Movement Explanation[/bold cyan]",
            box=box.ROUNDED,
        )
    )

    _section("Price Action Summary", out.price_move_summary)

    table = Table(
        title="Ranked Causes",
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold magenta",
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

    if out.ranked_causes:
        top = out.ranked_causes[0]
        console.print(f"[bold]Supporting evidence for #{top.rank} ({top.cause}):[/bold]")
        for ev in top.supporting_evidence:
            console.print(f"  • {ev}")
        console.print()

    _watch_table(out.what_to_watch_next)


def _render_watchlist(out: WatchlistMonitorOutput) -> None:
    console.print(
        Panel(
            f"Tickers: [bold yellow]{', '.join(out.tickers)}[/bold yellow]  •  "
            f"Generated: {out.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            title="[bold cyan]Watchlist Monitor — Weekly Report[/bold cyan]",
            box=box.ROUNDED,
        )
    )

    _section("Portfolio Summary", out.portfolio_summary)

    for ts in out.ticker_summaries:
        mom_colour = {
            "STRONG_UP": "green",
            "UP": "green",
            "FLAT": "yellow",
            "DOWN": "red",
            "STRONG_DOWN": "red",
        }.get(ts.momentum, "white")

        console.print(
            Rule(
                f"[bold yellow]{ts.ticker}[/bold yellow]  "
                f"[{mom_colour}]{ts.momentum}[/{mom_colour}]"
            )
        )
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

    console.print("[bold red]Macro Risks:[/bold red]")
    for r in out.macro_risks:
        console.print(f"  ⚠  {r}")
    console.print()

    console.print("[bold green]Top Opportunities:[/bold green]")
    for o in out.top_opportunities:
        console.print(f"  ★  {o}")
    console.print()

    for ts in out.ticker_summaries:
        if ts.next_week_watchpoints:
            console.print(f"[bold]{ts.ticker} — Next Week Watchpoints:[/bold]")
            for wp in ts.next_week_watchpoints:
                console.print(f"  → {wp.item} ({wp.timeframe}): {wp.reason}")
    console.print()


def _render_trade(out: TradingDecisionOutput) -> None:
    bias_colour = {
        "Bullish": "green",
        "Bearish": "red",
        "Neutral": "yellow",
    }.get(out.bias, "white")

    console.print(
        Panel(
            f"[bold]{out.ticker}[/bold]  •  "
            f"Bias: [bold {bias_colour}]{out.bias}[/bold {bias_colour}]  •  "
            f"Confidence: [bold]{out.confidence}%[/bold]",
            title="[bold cyan]Trading Decision[/bold cyan]",
            box=box.ROUNDED,
        )
    )

    console.print(f"[bold]Buy Zone:[/bold] {out.buy_zone}")
    console.print(f"[bold]Stop Loss:[/bold] {out.stop_loss}")
    console.print(f"[bold]Take Profit:[/bold] {out.take_profit}")
    console.print()

    if out.reasoning:
        console.print("[bold]Reasoning:[/bold]")
        for r in out.reasoning:
            console.print(f"  • {r}")
        console.print()


def _section(title: str, body: str) -> None:
    console.print(f"[bold underline]{title}[/bold underline]")
    console.print(f"  {body}\n")


def _watch_table(watch_points: list) -> None:
    if not watch_points:
        return
    table = Table(
        title="What to Watch Next",
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
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
  python main.py trade     <TICKER>
  python main.py watchlist <TICKER1> [TICKER2 ...]

Examples:
  python main.py research  NVDA
  python main.py explain   TSLA
  python main.py trade     NVDA
  python main.py watchlist AAPL NVDA MSFT
"""


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        console.print(USAGE)
        sys.exit(0)

    verb = argv[1].lower()
    args = argv[2:]

    if verb not in ("research", "explain", "trade", "watchlist"):
        console.print(f"[red]Unknown command:[/red] {verb}")
        console.print(USAGE)
        sys.exit(1)

    if not args:
        console.print("[red]Please provide at least one ticker symbol.[/red]")
        sys.exit(1)

    tickers_str = " ".join(normalize_symbol(a) for a in args)
    raw_query = f"{verb} {tickers_str}"

    try:
        run_pipeline_streaming(raw_query)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
