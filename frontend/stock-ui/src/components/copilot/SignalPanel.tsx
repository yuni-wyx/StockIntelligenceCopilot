"use client";

import { useLanguage } from "@/context/LanguageContext";
import { SignalViewModel } from "./signal";

type SignalPanelProps = {
  signal: SignalViewModel | null;
};

function scoreTone(score: number) {
  if (score >= 60) return "text-emerald-300";
  if (score < 40) return "text-rose-300";
  return "text-amber-200";
}

function confidenceTone(confidence: SignalViewModel["confidence"]) {
  if (confidence === "High") return "border-emerald-400/20 bg-emerald-400/10 text-emerald-100";
  if (confidence === "Low") return "border-amber-300/30 bg-amber-300/10 text-amber-100";
  return "border-sky-400/20 bg-sky-400/10 text-sky-100";
}

export function SignalPanel({ signal }: SignalPanelProps) {
  const { t } = useLanguage();

  if (!signal) {
    return null;
  }

  const showLowConfidenceAlert = signal.confidence === "Low";
  const showBreakdownFallback =
    signal.usedFallbackParsing &&
    signal.positiveSignals.length === 0 &&
    signal.negativeSignals.length === 0;

  return (
    <section className="mt-4 rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">{t.heuristicEstimateShort}</div>
          <h3 className="mt-1 text-base font-semibold text-zinc-100">{t.relativeSignal}</h3>
          <p className="mt-1 text-xs leading-5 text-zinc-400">{t.benchmarkRelativeStrength}</p>
        </div>
        <div className={`text-right ${scoreTone(signal.signalScore)}`}>
          <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">{t.signalScore}</div>
          <div className="mt-1 text-2xl font-semibold">{signal.signalScore.toFixed(1)}</div>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <SignalMetric label={t.signalBand} value={signal.signalBand} />
        <SignalMetric label={t.signalConfidence} value={signal.confidence} />
        <SignalMetric label={t.signalBenchmark} value={signal.benchmark} />
        <SignalMetric label={t.signalHorizon} value={`${signal.horizonDays} ${t.signalDays}`} />
      </div>

      {showLowConfidenceAlert ? (
        <div className={`mt-3 rounded-xl border px-3 py-2 text-sm ${confidenceTone(signal.confidence)}`}>
          {t.signalLowConfidenceNote}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <SignalList
          title={t.signalPositiveSignals}
          items={signal.positiveSignals}
          emptyLabel={showBreakdownFallback ? t.signalNoDetailedBreakdown : null}
          tone="positive"
        />
        <SignalList
          title={t.signalNegativeSignals}
          items={signal.negativeSignals}
          emptyLabel={showBreakdownFallback ? t.signalNoDetailedBreakdown : null}
          tone="negative"
        />
      </div>

      {signal.dataCaveats.length > 0 ? (
        <div className="mt-4 rounded-xl border border-amber-300/20 bg-amber-300/10 p-3">
          <div className="text-sm font-medium text-amber-100">{t.signalDataCaveats}</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-amber-100/80">
            {signal.dataCaveats.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
        <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">{t.signalDisclaimerLabel}</div>
        <p className="mt-2 text-xs leading-5 text-zinc-400">{signal.disclaimer}</p>
      </div>
    </section>
  );
}

function SignalMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-zinc-100">{value}</div>
    </div>
  );
}

function SignalList({
  title,
  items,
  emptyLabel,
  tone,
}: {
  title: string;
  items: string[];
  emptyLabel: string | null;
  tone: "positive" | "negative";
}) {
  const titleClass = tone === "positive" ? "text-emerald-200" : "text-rose-200";

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
      <div className={`text-sm font-medium ${titleClass}`}>{title}</div>
      {items.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-zinc-300">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs leading-5 text-zinc-500">{emptyLabel ?? "N/A"}</p>
      )}
    </div>
  );
}
