"use client";

import type { PortfolioAnalysisResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import {
  Badge,
  EmptyState,
  ExposureCard,
  InsightPanel,
  InsightStat,
  ListContent,
  MetricCard,
  SnapshotRow,
  concentrationLevel,
  formatNumber,
  qualitativeLevel,
  qualitativeTone,
} from "./shared";
import type { WealthStudioOperation } from "./types";

type Props = {
  copy: WealthStudioCopy;
  analysis: PortfolioAnalysisResponse | null;
  activeOperation: WealthStudioOperation | null;
  insightsError: string | null;
};

export function PortfolioSnapshotPanel({
  copy,
  analysis,
  activeOperation,
  insightsError,
}: Props) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{copy.portfolioInsights}</h2>
          <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.insightsHelper}</p>
        </div>
        {analysis ? (
          <Badge tone={qualitativeTone(analysis.overall_score)}>
            {qualitativeLevel(analysis.overall_score, copy)}
          </Badge>
        ) : null}
      </div>

      {activeOperation === "analyze" ? (
        <div className="mt-4 rounded-2xl border border-sky-300/25 bg-sky-300/10 p-5">
          <h3 className="font-medium text-sky-100">{copy.analyzingTitle}</h3>
          <p className="mt-2 text-sm leading-6 text-sky-100/75">{copy.analyzingBody}</p>
        </div>
      ) : insightsError ? (
        <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-300/10 p-5">
          <h3 className="font-medium text-rose-100">{copy.insightsErrorTitle}</h3>
          <p className="mt-2 break-words text-sm leading-6 text-rose-100/80">{insightsError}</p>
        </div>
      ) : !analysis ? (
        <EmptyState title={copy.noAnalysisTitle} body={copy.noAnalysisBody} />
      ) : (
        <div className="mt-5 space-y-6">
          <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
            <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{copy.overallHealth}</h3>
                  <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.overallHealthHelper}</p>
                </div>
                <div className="text-left sm:text-right">
                  <div className="text-3xl font-semibold">
                    {qualitativeLevel(analysis.overall_score, copy)}
                  </div>
                  <Badge tone="neutral">{copy.heuristicEstimate}</Badge>
                </div>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <SnapshotRow
                  label={copy.diversification}
                  level={qualitativeLevel(analysis.diversification_score, copy)}
                />
                <SnapshotRow
                  label={copy.concentration}
                  level={concentrationLevel(analysis.concentration_score, copy)}
                />
                <SnapshotRow label={copy.income} level={qualitativeLevel(analysis.income_score, copy)} />
                <SnapshotRow
                  label={copy.defensive}
                  level={qualitativeLevel(analysis.defensive_score, copy)}
                />
                <SnapshotRow label={copy.growth} level={qualitativeLevel(analysis.growth_score, copy)} />
              </div>

              <p className="mt-5 text-sm leading-6 text-zinc-300">{analysis.summary}</p>
              <p className="mt-3 rounded-xl border border-amber-200/20 bg-amber-200/10 px-4 py-3 text-xs leading-5 text-amber-100/85">
                {copy.heuristicDisclaimer}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <InsightStat label={copy.totalValue} value={analysis.total_current_value} helper={copy.totalValueHelper} />
              <InsightStat
                label={copy.unrealizedPL}
                value={analysis.total_unrealized_gain_loss}
                helper={`${formatNumber(analysis.total_return_pct)}% ${copy.totalReturn}`}
              />
              <InsightStat label={copy.costBasis} value={analysis.total_cost_basis} helper={copy.totalCostHelper} />
              <InsightStat
                label={copy.returnPct}
                value={analysis.total_return_pct}
                suffix="%"
                helper={copy.totalReturn}
              />
              <InsightStat
                label={copy.annualDividend}
                value={analysis.estimated_annual_dividend}
                helper={copy.annualDividendHelper}
              />
              <InsightStat
                label={copy.monthlyDividend}
                value={analysis.estimated_monthly_dividend}
                helper={copy.monthlyDividendHelper}
              />
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <InsightPanel
              title={copy.keyRisks}
              helper={copy.keyRisksHelper}
              badge={
                <Badge tone={analysis.risk_flags.length > 0 ? "warning" : "good"}>
                  {analysis.risk_flags.length > 0 ? copy.review : copy.clear}
                </Badge>
              }
            >
              <ListContent items={analysis.risk_flags} emptyLabel={copy.noRiskFlags} />
              {analysis.risk_attribution && Object.keys(analysis.risk_attribution).length > 0 ? (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-zinc-200">{copy.riskAttribution}</h4>
                  <div className="mt-3 space-y-3">
                    {Object.entries(analysis.risk_attribution)
                      .filter(([, value]) => value > 0)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 4)
                      .map(([label, value]) => (
                        <div key={label}>
                          <div className="flex items-center justify-between gap-3 text-xs text-zinc-400">
                            <span className="break-words">{label.replaceAll("_", " ")}</span>
                            <span>{formatNumber(value)}%</span>
                          </div>
                          <div className="mt-1 h-2 rounded-full bg-white/10">
                            <div
                              className="h-2 rounded-full bg-amber-100"
                              style={{ width: `${Math.min(value, 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : null}
            </InsightPanel>

            <InsightPanel
              title={copy.recommendedNextSteps}
              helper={copy.nextStepsHelper}
              badge={<Badge tone="neutral">{analysis.suggestions.length}</Badge>}
            >
              <ListContent items={analysis.suggestions} emptyLabel={copy.noSuggestions} />
            </InsightPanel>
          </div>

          <details className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
              {copy.detailedExposureSection}
            </summary>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{copy.detailedExposureHelper}</p>

            <div className="mt-4 grid gap-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                <ExposureCard title={copy.assetTypeExposure} items={analysis.asset_type_exposure} copy={copy} />
                <ExposureCard title={copy.categoryExposure} items={analysis.category_exposure} copy={copy} />
                <ExposureCard title={copy.sectorExposure} items={analysis.sector_exposure} copy={copy} />
                <ExposureCard title={copy.themeExposure} items={analysis.theme_exposure} copy={copy} />
                <ExposureCard title={copy.marketExposure} items={analysis.market_exposure} copy={copy} />
              </div>

              <InsightPanel
                title={copy.incomeDataQuality}
                helper={copy.incomeDataQualityHelper}
                badge={
                  <Badge tone={analysis.missing_data.length > 0 ? "warning" : "good"}>
                    {analysis.missing_data.length > 0 ? copy.checkData : copy.dataOk}
                  </Badge>
                }
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <InsightStat
                    label={copy.incomeScore}
                    value={undefined}
                    displayValue={qualitativeLevel(analysis.income_score, copy)}
                    helper={copy.incomeScoreHelper}
                  />
                  <InsightStat label={copy.totalCost} value={analysis.total_cost_basis} helper={copy.totalCostHelper} />
                </div>
                <div className="mt-4">
                  <ListContent items={analysis.missing_data} emptyLabel={copy.noMissingData} />
                </div>
              </InsightPanel>

              <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="font-semibold">{copy.newsToMonitor}</h3>
                    <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.newsHelper}</p>
                  </div>
                  <Badge tone={Object.keys(analysis.news_to_monitor).length > 0 ? "neutral" : "good"}>
                    {Object.keys(analysis.news_to_monitor).length} {copy.tickerCount}
                    {Object.keys(analysis.news_to_monitor).length === 1 ? "" : "s"}
                  </Badge>
                </div>
                <div className="mt-4 space-y-4">
                  {Object.keys(analysis.news_to_monitor).length === 0 ? (
                    <p className="text-sm text-zinc-400">{copy.noNews}</p>
                  ) : (
                    Object.entries(analysis.news_to_monitor).map(([ticker, headlines]) => (
                      <div key={ticker} className="rounded-xl border border-white/10 bg-black/20 p-3">
                        <h4 className="font-medium text-white">{ticker}</h4>
                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-300">
                          {headlines.map((headline) => (
                            <li key={headline}>{headline}</li>
                          ))}
                        </ul>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <EvidenceProvenancePanel analysis={analysis} copy={copy} />

              <details className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
                  {copy.holdingDetails}
                </summary>
                <p className="mt-2 text-sm leading-6 text-zinc-500">{copy.holdingDetailsHelper}</p>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-[620px] text-left text-sm">
                    <thead className="text-zinc-400">
                      <tr>
                        {[copy.ticker, copy.weightPct, "P/L", copy.returnPct, copy.annualDiv, copy.theme].map(
                          (label) => (
                            <th key={label} className="px-2 py-2 font-medium">
                              {label}
                            </th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.holdings.map((holding) => (
                        <tr key={holding.ticker} className="border-t border-white/5">
                          <td className="px-2 py-2">{holding.ticker}</td>
                          <td className="px-2 py-2">{formatNumber(holding.portfolio_weight_pct)}%</td>
                          <td className="px-2 py-2">{formatNumber(holding.unrealized_gain_loss)}</td>
                          <td className="px-2 py-2">{formatNumber(holding.return_pct)}%</td>
                          <td className="px-2 py-2">{formatNumber(holding.estimated_annual_dividend)}</td>
                          <td className="px-2 py-2">{holding.theme ?? "N/A"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </div>
          </details>
        </div>
      )}
    </section>
  );
}

function EvidenceProvenancePanel({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisResponse;
  copy: Pick<
    WealthStudioCopy,
    | "evidenceProvenance"
    | "evidenceProvenanceHelper"
    | "evidenceSources"
    | "claimLinks"
    | "unsupportedClaims"
    | "noUnsupportedClaims"
    | "confidence"
  >;
}) {
  const sources = analysis.evidence_provenance ?? [];
  const claimLinks = analysis.claim_evidence ?? [];
  const unsupportedClaims = analysis.unsupported_claims ?? [];

  return (
    <details className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
        {copy.evidenceProvenance}
      </summary>
      <p className="mt-2 text-sm leading-6 text-zinc-500">{copy.evidenceProvenanceHelper}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MetricCard label={copy.evidenceSources} value={sources.length} />
        <MetricCard label={copy.claimLinks} value={claimLinks.length} />
        <MetricCard
          label={copy.confidence}
          value={analysis.confidence_score !== undefined ? analysis.confidence_score * 100 : undefined}
          suffix="%"
        />
      </div>
      {unsupportedClaims.length > 0 ? (
        <div className="mt-4 rounded-xl border border-amber-300/25 bg-amber-300/10 p-3">
          <div className="text-sm font-medium text-amber-100">{copy.unsupportedClaims}</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-100/80">
            {unsupportedClaims.slice(0, 4).map((claim) => (
              <li key={`${claim.output_field}-${claim.reason}`} className="break-words">
                {claim.output_field}: {claim.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-4 text-sm text-zinc-400">{copy.noUnsupportedClaims}</p>
      )}
      {sources.length > 0 ? (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {sources.slice(0, 6).map((source) => (
            <div key={source.source_id} className="rounded-xl border border-white/10 bg-black/25 p-3 text-sm">
              <div className="font-medium text-zinc-200">
                {source.source_type}
                {source.ticker ? ` · ${source.ticker}` : ""}
              </div>
              <div className="mt-1 break-words text-zinc-400">
                {source.title || source.provider || source.source_id}
              </div>
              {source.url ? (
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block break-all text-xs text-amber-100 hover:text-white"
                >
                  {source.url}
                </a>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </details>
  );
}
