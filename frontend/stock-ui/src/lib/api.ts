import { buildApiUrl } from "@/lib/apiBase";

export type WatchlistResult = {
  tickers: string[];
  portfolioSummary: string;
  tickerSummaries: {
    ticker: string;
    weeklyHighlights: string;
    momentum: string;
    majorNews: string[];
    earningsEvents: string;
    riskSignals: string[];
    nextWeekWatchpoints: {
      item: string;
      timeframe: string;
      reason: string;
    }[];
  }[];
  macroRisks: string[];
  topOpportunities: string[];
};

type RawWatchpoint = {
  item?: string;
  timeframe?: string;
  reason?: string;
};

type RawTickerSummary = {
  ticker?: string;
  weekly_highlights?: string;
  momentum?: string;
  major_news?: string[];
  earnings_events?: string;
  risk_signals?: string[];
  next_week_watchpoints?: RawWatchpoint[];
};

export async function fetchWatchlist(tickers: string[]): Promise<WatchlistResult> {
  const res = await fetch(buildApiUrl("/watchlist"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ tickers }),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch watchlist");
  }

  const raw = await res.json();

  return {
    tickers: Array.isArray(raw.tickers) ? raw.tickers : [],
    portfolioSummary: raw.portfolio_summary ?? "",
    tickerSummaries: Array.isArray(raw.ticker_summaries)
      ? raw.ticker_summaries.map((item: RawTickerSummary) => ({
          ticker: item.ticker ?? "",
          weeklyHighlights: item.weekly_highlights ?? "",
          momentum: item.momentum ?? "",
          majorNews: Array.isArray(item.major_news) ? item.major_news : [],
          earningsEvents: item.earnings_events ?? "",
          riskSignals: Array.isArray(item.risk_signals) ? item.risk_signals : [],
          nextWeekWatchpoints: Array.isArray(item.next_week_watchpoints)
            ? item.next_week_watchpoints.map((wp: RawWatchpoint) => ({
                item: wp.item ?? "",
                timeframe: wp.timeframe ?? "",
                reason: wp.reason ?? "",
              }))
            : [],
        }))
      : [],
    macroRisks: Array.isArray(raw.macro_risks) ? raw.macro_risks : [],
    topOpportunities: Array.isArray(raw.top_opportunities) ? raw.top_opportunities : [],
  };
}
