"use client";

import type { WealthStudioCopy } from "@/i18n/messages";
import { Badge, EmptyState, qualitativeLevel, qualitativeTone } from "./shared";
import {
  DetailedExposureSection,
  RiskAndReviewSection,
  SnapshotOverview,
} from "./PortfolioSnapshotSections";
import type { PortfolioAnalysisWithIntelligence, WealthStudioOperation } from "./types";

type Props = {
  copy: WealthStudioCopy;
  analysis: PortfolioAnalysisWithIntelligence | null;
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
          <SnapshotOverview analysis={analysis} copy={copy} />
          <RiskAndReviewSection analysis={analysis} copy={copy} />
          <DetailedExposureSection analysis={analysis} copy={copy} />
        </div>
      )}
    </section>
  );
}
