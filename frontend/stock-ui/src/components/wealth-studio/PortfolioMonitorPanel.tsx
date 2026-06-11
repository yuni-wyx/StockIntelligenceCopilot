"use client";

import type { PortfolioMonitorResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import {
  Badge,
  EmptyState,
  ListContent,
  primaryButtonClassName,
} from "./shared";

type Props = {
  copy: WealthStudioCopy;
  loading: boolean;
  canRun: boolean;
  errorMessage: string | null;
  response: PortfolioMonitorResponse | null;
  onCheck: () => void;
};

function inferSourceLabels(
  holding: PortfolioMonitorResponse["holdings"][number],
  copy: WealthStudioCopy,
): string[] {
  const labels: string[] = [];
  if (holding.signal_score != null || holding.signal_band) {
    labels.push(copy.portfolioMonitorSourceSignal);
  }
  if (holding.news_sentiment) {
    labels.push(copy.portfolioMonitorSourceNews);
  }
  if (holding.next_earnings_date || holding.days_to_next_earnings != null) {
    labels.push(copy.portfolioMonitorSourceEarnings);
  }
  if ((holding.weight_pct ?? 0) >= 25 || (holding.return_pct ?? 0) <= -15) {
    labels.push(copy.portfolioMonitorSourceConcentration);
  }
  return labels;
}

export function PortfolioMonitorPanel({
  copy,
  loading,
  canRun,
  errorMessage,
  response,
  onCheck,
}: Props) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200/60">
            {copy.ideasSection}
          </div>
          <h2 className="mt-1 text-xl font-semibold">{copy.portfolioMonitorTitle}</h2>
        </div>
        <Badge tone="neutral">{copy.portfolioMonitorContextNote}</Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{copy.portfolioMonitorHelper}</p>

      <button
        type="button"
        onClick={onCheck}
        disabled={loading}
        className={`mt-4 ${primaryButtonClassName}`}
      >
        {loading ? copy.working : copy.portfolioMonitorCta}
      </button>

      {!canRun && !response ? (
        <EmptyState
          title={copy.portfolioMonitorEmptyTitle}
          body={copy.portfolioMonitorEmptyBody}
        />
      ) : null}

      {errorMessage ? (
        <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {errorMessage}
        </div>
      ) : null}

      {response ? (
        <div className="mt-5 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-sm font-semibold text-zinc-100">
                {copy.portfolioMonitorTopAlerts}
              </div>
              {response.workspace_id ? (
                <Badge tone="neutral">
                  {copy.portfolioMonitorWorkspaceLabel}: {response.workspace_id}
                </Badge>
              ) : null}
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              {response.portfolio_summary}
            </p>
            <div className="mt-4">
              <ListContent
                items={response.top_portfolio_alerts}
                emptyLabel={copy.portfolioMonitorNoAlerts}
              />
            </div>
          </div>

          <div className="space-y-4">
            {response.holdings.map((holding) => {
              const sourceLabels = inferSourceLabels(holding, copy);
              const title = holding.name
                ? `${holding.ticker} · ${holding.name}`
                : holding.ticker;
              return (
                <article
                  key={holding.ticker}
                  className="rounded-2xl border border-white/10 bg-black/25 p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {holding.weight_pct != null ? (
                          <Badge tone="neutral">
                            {copy.weightPct}: {holding.weight_pct.toFixed(2)}%
                          </Badge>
                        ) : null}
                        {holding.return_pct != null ? (
                          <Badge
                            tone={holding.return_pct < 0 ? "warning" : "good"}
                          >
                            {copy.returnPct}: {holding.return_pct.toFixed(2)}%
                          </Badge>
                        ) : null}
                        {holding.signal_band ? (
                          <Badge tone={holding.signal_band === "Weak" ? "warning" : "neutral"}>
                            {copy.signalBand}: {holding.signal_band}
                          </Badge>
                        ) : null}
                        {holding.news_sentiment ? (
                          <Badge tone={holding.news_sentiment === "negative" ? "warning" : "neutral"}>
                            {copy.portfolioMonitorNewsTone}: {holding.news_sentiment}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                    {sourceLabels.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {sourceLabels.map((label) => (
                          <Badge key={`${holding.ticker}-${label}`} tone="neutral">
                            {label}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_0.9fr]">
                    <div>
                      <div className="text-sm font-semibold text-zinc-100">
                        {copy.portfolioMonitorWatchItems}
                      </div>
                      <div className="mt-2">
                        <ListContent
                          items={holding.watch_items}
                          emptyLabel={copy.portfolioMonitorNoWatchItems}
                        />
                      </div>
                    </div>

                    <div className="space-y-3">
                      {holding.days_to_next_earnings != null ? (
                        <div className="rounded-xl border border-white/10 bg-black/25 p-3 text-sm text-zinc-300">
                          <div className="font-medium text-zinc-100">
                            {copy.earnings}
                          </div>
                          <p className="mt-1 leading-6">
                            {holding.next_earnings_date
                              ? `${copy.portfolioMonitorNextEarnings}: ${holding.next_earnings_date}`
                              : copy.portfolioMonitorEarningsUnavailable}
                          </p>
                          <p className="text-zinc-400">
                            {copy.portfolioMonitorDaysToEarnings}: {holding.days_to_next_earnings}
                          </p>
                        </div>
                      ) : null}

                      <div className="rounded-xl border border-white/10 bg-black/25 p-3">
                        <div className="text-sm font-semibold text-zinc-100">
                          {copy.caveats}
                        </div>
                        <div className="mt-2">
                          <ListContent
                            items={holding.caveats}
                            emptyLabel={copy.portfolioMonitorNoCaveats}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="rounded-2xl border border-amber-300/20 bg-amber-300/5 p-4">
            <div className="text-sm font-semibold text-amber-100">
              {copy.portfolioChatSafety}
            </div>
            <p className="mt-2 text-sm leading-6 text-amber-50/90">
              {response.safety_disclaimer}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
