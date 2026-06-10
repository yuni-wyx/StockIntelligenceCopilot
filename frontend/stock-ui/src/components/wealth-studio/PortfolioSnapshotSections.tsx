"use client";

import type { WealthStudioCopy } from "@/i18n/messages";
import {
  Badge,
  ExposureCard,
  InsightPanel,
  InsightStat,
  ListContent,
  MetricCard,
  MiniMetric,
  SnapshotRow,
  concentrationLevel,
  formatNumber,
  qualitativeLevel,
} from "./shared";
import type {
  PortfolioAnalysisWithIntelligence,
  PortfolioHoldingContribution,
  PortfolioReviewItem,
} from "./types";

export function SnapshotOverview({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  return (
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
  );
}

export function RiskAndReviewSection({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  const intelligence = analysis.portfolio_intelligence;

  return (
    <div className="space-y-4">
      {intelligence ? (
        <PortfolioIntelligenceSection analysis={analysis} copy={copy} />
      ) : null}

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
    </div>
  );
}

export function DetailedExposureSection({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  return (
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

        <NewsToMonitorPanel analysis={analysis} copy={copy} />
        <EvidenceProvenancePanel analysis={analysis} copy={copy} />
        <HoldingDetailsPanel analysis={analysis} copy={copy} />
      </div>
    </details>
  );
}

function NewsToMonitorPanel({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  return (
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
  );
}

function HoldingDetailsPanel({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  return (
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
  );
}

function EvidenceProvenancePanel({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
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

function PortfolioIntelligenceSection({
  analysis,
  copy,
}: {
  analysis: PortfolioAnalysisWithIntelligence;
  copy: WealthStudioCopy;
}) {
  const intelligence = analysis.portfolio_intelligence;
  if (!intelligence) {
    return null;
  }

  const riskAttribution = intelligence.risk_attribution;
  const concentration = intelligence.concentration;
  const incomeQuality = intelligence.income_quality;
  const reviewItems = intelligence.suggested_review_items ?? [];

  return (
    <div className="grid gap-4">
      <InsightPanel
        title={copy.riskAttribution}
        helper={copy.portfolioIntelligenceHelper}
        badge={<Badge tone="neutral">{copy.heuristicEstimate}</Badge>}
      >
        <div className="grid gap-4 xl:grid-cols-2">
          <ContributionListCard
            title={copy.downsideContributors}
            items={riskAttribution?.top_downside_weighted_holdings ?? []}
            valueKey="contribution_pct"
            copy={copy}
          />
          <ContributionListCard
            title={copy.unrealizedLosers}
            items={riskAttribution?.top_unrealized_losers ?? []}
            valueKey="contribution_pct"
            copy={copy}
          />
          <ContributionListCard
            title={copy.unrealizedWinners}
            items={riskAttribution?.top_unrealized_winners ?? []}
            valueKey="contribution_pct"
            copy={copy}
          />
          <ContributionListCard
            title={copy.stressTestContributors}
            items={riskAttribution?.top_stress_test_contributors ?? []}
            emptyLabel={copy.noStressContributors}
            valueKey="contribution_pct"
            copy={copy}
          />
        </div>
        {(riskAttribution?.flags?.length ?? 0) > 0 ? (
          <div className="mt-4">
            <ListContent items={riskAttribution?.flags ?? []} emptyLabel={copy.noRiskFlags} />
          </div>
        ) : null}
      </InsightPanel>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <InsightPanel
          title={copy.concentrationAnalysis}
          helper={copy.overallHealthHelper}
          badge={<Badge tone="warning">{copy.review}</Badge>}
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniMetric label={copy.topHoldingWeight} value={concentration?.top_holding_weight_pct} suffix="%" />
            <MiniMetric label={copy.top3HoldingsWeight} value={concentration?.top_3_weight_pct} suffix="%" />
            <MiniMetric label={copy.top5HoldingsWeight} value={concentration?.top_5_weight_pct} suffix="%" />
          </div>
          {(concentration?.top_tickers?.length ?? 0) > 0 ? (
            <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-sm font-medium text-zinc-200">{copy.topHoldings}</div>
              <div className="mt-3 space-y-3">
                {(concentration?.top_tickers ?? []).slice(0, 5).map((item) => (
                  <ContributionRow key={`${item.ticker}-${item.weight_pct}`} item={item} value={item.weight_pct} />
                ))}
              </div>
            </div>
          ) : null}
          <div className="mt-4">
            <ListContent items={concentration?.flags ?? []} emptyLabel={copy.noPortfolioIntelligence} />
          </div>
        </InsightPanel>

        <InsightPanel
          title={copy.incomeQuality}
          helper={copy.incomeQualitySectionHelper}
          badge={<Badge tone="neutral">{copy.annualDividend}</Badge>}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <MiniMetric
              label={copy.annualDividend}
              value={incomeQuality?.estimated_annual_dividend}
            />
            <MiniMetric
              label={copy.monthlyDividend}
              value={incomeQuality?.estimated_monthly_dividend}
            />
            <MiniMetric
              label={copy.dividendConcentration}
              value={incomeQuality?.dividend_concentration_pct}
              suffix="%"
            />
          </div>
          <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
            <div className="text-sm font-medium text-zinc-200">{copy.topDividendContributors}</div>
            {(incomeQuality?.top_dividend_contributors?.length ?? 0) > 0 ? (
              <div className="mt-3 space-y-3">
                {(incomeQuality?.top_dividend_contributors ?? []).slice(0, 5).map((item) => (
                  <ContributionRow
                    key={`${item.ticker}-${item.contribution_pct}`}
                    item={item}
                    value={item.contribution_pct}
                  />
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-zinc-400">{copy.noSuggestions}</p>
            )}
          </div>
          <details className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
            <summary className="cursor-pointer text-sm font-medium text-zinc-200">
              {copy.missingDividendData}
            </summary>
            <div className="mt-3 space-y-3">
              <ListContent
                items={incomeQuality?.holdings_missing_dividend_data ?? []}
                emptyLabel={copy.noDividendDataMissing}
              />
              <ListContent items={incomeQuality?.caveats ?? []} emptyLabel={copy.noCaveats} />
            </div>
          </details>
        </InsightPanel>
      </div>

      <InsightPanel
        title={copy.recommendedNextSteps}
        helper={copy.nextStepsHelper}
        badge={<Badge tone="neutral">{reviewItems.length}</Badge>}
      >
        {reviewItems.length === 0 ? (
          <p className="text-sm leading-6 text-zinc-400">{copy.noReviewItems}</p>
        ) : (
          <div className="space-y-3">
            {reviewItems.map((item) => (
              <ReviewItemCard key={`${item.title}-${item.severity}`} item={item} copy={copy} />
            ))}
          </div>
        )}
      </InsightPanel>
    </div>
  );
}

function ContributionListCard({
  title,
  items,
  copy,
  emptyLabel,
  valueKey,
}: {
  title: string;
  items: PortfolioHoldingContribution[];
  copy: WealthStudioCopy;
  emptyLabel?: string;
  valueKey: "contribution_pct" | "weight_pct";
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="text-sm font-medium text-zinc-200">{title}</div>
      {items.length > 0 ? (
        <div className="mt-3 space-y-3">
          {items.slice(0, 4).map((item) => (
            <ContributionRow
              key={`${title}-${item.ticker}`}
              item={item}
              value={valueKey === "contribution_pct" ? item.contribution_pct : item.weight_pct}
            />
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-zinc-400">{emptyLabel ?? copy.noSuggestions}</p>
      )}
    </div>
  );
}

function ContributionRow({
  item,
  value,
}: {
  item: PortfolioHoldingContribution;
  value: number | null | undefined;
}) {
  return (
    <div>
      <div className="flex items-start justify-between gap-3 text-sm">
        <div className="min-w-0">
          <div className="break-words font-medium text-zinc-200">{item.ticker}</div>
          {item.name ? <div className="text-xs text-zinc-500">{item.name}</div> : null}
        </div>
        <div className="shrink-0 text-zinc-300">{formatNumber(value)}%</div>
      </div>
      <div className="mt-2 h-2 rounded-full bg-white/10">
        <div
          className="h-2 rounded-full bg-amber-100"
          style={{ width: `${Math.min(Math.max(value ?? 0, 0), 100)}%` }}
        />
      </div>
      {item.explanation ? (
        <div className="mt-2 text-xs leading-5 text-zinc-500">{item.explanation}</div>
      ) : null}
    </div>
  );
}

function ReviewItemCard({
  item,
  copy,
}: {
  item: PortfolioReviewItem;
  copy: WealthStudioCopy;
}) {
  const tone =
    item.severity === "high"
      ? "warning"
      : item.severity === "medium"
        ? "neutral"
        : "good";
  const severityLabel =
    item.severity === "high"
      ? copy.severityHigh
      : item.severity === "medium"
        ? copy.severityMedium
        : copy.severityLow;

  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="font-medium text-zinc-100">{item.title}</div>
        <Badge tone={tone}>{severityLabel}</Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-300">{item.reason}</p>
      {item.evidence_keys && item.evidence_keys.length > 0 ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-zinc-500">{copy.evidenceKeys}</summary>
          <div className="mt-2 flex flex-wrap gap-2">
            {item.evidence_keys.map((key) => (
              <span
                key={key}
                className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-zinc-400"
              >
                {key}
              </span>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
