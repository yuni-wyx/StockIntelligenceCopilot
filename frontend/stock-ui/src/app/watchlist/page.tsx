"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { TopNav } from "@/components/TopNav";
import { fetchWatchlist, WatchlistResult } from "@/lib/api";
import { getWatchlist, removeFromWatchlist } from "@/lib/watchlist";

export default function WatchlistPage() {
  const { t } = useLanguage();

  const [inputTicker, setInputTicker] = useState("");
  const [tickers, setTickers] = useState<string[]>(() => getWatchlist());
  const [data, setData] = useState<WatchlistResult | null>(null);

  useEffect(() => {
    if (tickers.length === 0) {
      return;
    }

    fetchWatchlist(tickers)
      .then(setData)
      .catch(console.error)
  }, [tickers]);

  const loading = tickers.length > 0 && data === null;

  const handleRemove = (ticker: string) => {
    const next = removeFromWatchlist(ticker);
    setTickers(next);
    if (next.length === 0) {
      setData(null);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 p-4 text-white">
      <div className="mx-auto max-w-5xl">
        <TopNav
          inputTicker={inputTicker}
          setInputTicker={setInputTicker}
          active="watchlist"
        />

        <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <h1 className="text-xl font-semibold">{t.myWatchlist}</h1>
          <p className="mt-2 text-sm text-zinc-400">{t.savedLocally}</p>

          <div className="mt-4 flex flex-wrap gap-2">
            {tickers.length === 0 && (
              <p className="text-sm text-zinc-400">{t.noData}</p>
            )}

            {tickers.map((ticker) => (
              <div
                key={ticker}
                className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-2"
              >
                <span className="text-sm font-medium">{ticker}</span>
                <button
                  onClick={() => handleRemove(ticker)}
                  className="text-xs text-rose-300"
                >
                  {t.removeFromWatchlist}
                </button>
              </div>
            ))}
          </div>
        </div>

        {loading && <div className="mt-6">{t.loading}</div>}

        {!loading && data && (
          <div className="mt-6 space-y-4">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <h2 className="text-base font-semibold">{t.portfolioSummary}</h2>
              <p className="mt-2 text-sm text-zinc-300">{data.portfolioSummary}</p>
            </div>

            {data.tickerSummaries.map((item) => (
              <div
                key={item.ticker}
                className="rounded-2xl border border-white/10 bg-black/30 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold">{item.ticker}</h3>
                  <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-zinc-300">
                    {item.momentum}
                  </span>
                </div>

                <p className="mt-3 text-sm text-zinc-300">{item.weeklyHighlights}</p>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-semibold text-zinc-200">{t.majorNews}</p>
                    <ul className="mt-2 space-y-2">
                      {item.majorNews.map((news, idx) => (
                        <li key={idx} className="text-sm text-zinc-300">
                          • {news}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-zinc-200">{t.earnings}</p>
                    <p className="mt-2 text-sm text-zinc-300">{item.earningsEvents}</p>
                  </div>
                </div>

                {item.riskSignals.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-semibold text-rose-300">{t.riskSignals}</p>
                    <ul className="mt-2 space-y-2">
                      {item.riskSignals.map((risk, idx) => (
                        <li key={idx} className="text-sm text-zinc-300">
                          • {risk}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {item.nextWeekWatchpoints.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-semibold text-zinc-200">
                      {t.nextWeekWatchpoints}
                    </p>
                    <div className="mt-2 space-y-2">
                      {item.nextWeekWatchpoints.map((wp, idx) => (
                        <div
                          key={idx}
                          className="rounded-xl border border-white/10 bg-white/[0.03] p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-medium">{wp.item}</p>
                            <span className="text-xs text-zinc-500">{wp.timeframe}</span>
                          </div>
                          <p className="mt-1 text-sm text-zinc-300">{wp.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
                <h2 className="text-base font-semibold text-rose-300">{t.macroRisks}</h2>
                <ul className="mt-2 space-y-2">
                  {data.macroRisks.map((risk, idx) => (
                    <li key={idx} className="text-sm text-zinc-300">
                      • {risk}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
                <h2 className="text-base font-semibold text-emerald-300">
                  {t.topOpportunities}
                </h2>
                <ul className="mt-2 space-y-2">
                  {data.topOpportunities.map((item, idx) => (
                    <li key={idx} className="text-sm text-zinc-300">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
