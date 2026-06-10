"use client";

import type { WealthStudioCopy } from "@/i18n/messages";
import {
  EmptyState,
  Field,
  MetricCard,
  formatNumber,
  inputClassName,
} from "./shared";
import { stressTestPresets } from "./stressTest";
import type { StressTestForm, StressTestPreset, StressTestResult } from "./types";

type Props = {
  copy: WealthStudioCopy;
  loading: boolean;
  stressTestForm: StressTestForm;
  stressTestError: string | null;
  stressTestResult: StressTestResult | null;
  onStressTestFormChange: (updater: (prev: StressTestForm) => StressTestForm) => void;
  onRunStressTest: () => void;
};

function presetLabel(preset: StressTestPreset, copy: WealthStudioCopy): string {
  switch (preset) {
    case "broad_market_20":
      return copy.stressTestBroadMarket;
    case "technology_selloff_15":
      return copy.stressTestTechnologySelloff;
    case "taiwan_market_15":
      return copy.stressTestTaiwanMarket;
    case "bond_rate_sensitive_10":
      return copy.stressTestBondRate;
    case "custom_ticker":
      return copy.stressTestCustomTicker;
  }
}

function presetDescription(preset: StressTestPreset, copy: WealthStudioCopy): string {
  switch (preset) {
    case "broad_market_20":
      return copy.stressTestBroadMarketHelper;
    case "technology_selloff_15":
      return copy.stressTestTechnologySelloffHelper;
    case "taiwan_market_15":
      return copy.stressTestTaiwanMarketHelper;
    case "bond_rate_sensitive_10":
      return copy.stressTestBondRateHelper;
    case "custom_ticker":
      return copy.stressTestCustomTickerHelper;
  }
}

export function PortfolioStressTestSection({
  copy,
  loading,
  stressTestForm,
  stressTestError,
  stressTestResult,
  onStressTestFormChange,
  onRunStressTest,
}: Props) {
  const isCustomPreset = stressTestForm.preset === "custom_ticker";

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
      <h2 className="text-xl font-semibold">{copy.stressTest}</h2>
      <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.stressTestHelper}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {stressTestPresets.map((preset) => {
          const selected = stressTestForm.preset === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() =>
                onStressTestFormChange((prev) => ({
                  ...prev,
                  preset,
                }))
              }
              className={`rounded-2xl border p-4 text-left transition ${
                selected
                  ? "border-amber-200/60 bg-amber-200/10"
                  : "border-white/10 bg-black/20 hover:border-white/20"
              }`}
            >
              <div className="text-sm font-semibold text-white">{presetLabel(preset, copy)}</div>
              <p className="mt-2 text-xs leading-5 text-zinc-400">
                {presetDescription(preset, copy)}
              </p>
            </button>
          );
        })}
      </div>

      {isCustomPreset ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Field label={copy.customTicker}>
            <input
              value={stressTestForm.customTicker}
              onChange={(event) =>
                onStressTestFormChange((prev) => ({
                  ...prev,
                  customTicker: event.target.value,
                }))
              }
              placeholder="NVDA"
              className={inputClassName}
            />
          </Field>
          <Field label={copy.stressTestShockPercent}>
            <input
              value={stressTestForm.customShockPct}
              onChange={(event) =>
                onStressTestFormChange((prev) => ({
                  ...prev,
                  customShockPct: event.target.value,
                }))
              }
              inputMode="decimal"
              placeholder="-20"
              className={inputClassName}
            />
          </Field>
        </div>
      ) : null}

      {stressTestError ? (
        <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">
          {stressTestError}
        </div>
      ) : null}

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-zinc-500">{copy.stressTestDisclaimer}</p>
        <button
          type="button"
          onClick={onRunStressTest}
          disabled={loading}
          className="rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
        >
          {copy.runStressTest}
        </button>
      </div>

      <div className="mt-6">
        <h3 className="text-lg font-semibold">{copy.stressTestResult}</h3>
        {!stressTestResult ? (
          <EmptyState
            title={copy.noStressTestTitle}
            body={copy.noStressTestBody}
          />
        ) : (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <MetricCard label={copy.currentValueStress} value={stressTestResult.beforeValue} />
              <MetricCard label={copy.stressedValue} value={stressTestResult.afterValue} />
              <MetricCard
                label={copy.estimatedImpact}
                value={stressTestResult.delta}
                suffix={` (${formatNumber(stressTestResult.deltaPct)}%)`}
              />
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <h4 className="font-semibold">{copy.stressTestExplanation}</h4>
              <p className="mt-2 text-sm leading-6 text-zinc-300">
                {stressTestResult.explanation}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <h4 className="font-semibold">{copy.biggestImpactedHoldings}</h4>
              {stressTestResult.impactedHoldings.length === 0 ? (
                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  {copy.noStressImpact}
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {stressTestResult.impactedHoldings.map((holding) => (
                    <div
                      key={`${holding.ticker}-${holding.beforeValue}`}
                      className="rounded-xl border border-white/10 bg-black/20 p-3"
                    >
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="font-medium text-zinc-100">
                            {holding.ticker}
                            {holding.name ? ` · ${holding.name}` : ""}
                          </div>
                          <div className="text-xs text-zinc-500">
                            {copy.appliedShock}: {formatNumber(holding.shockPct)}%
                          </div>
                        </div>
                        <div className="text-sm font-medium text-rose-200">
                          {formatNumber(holding.delta)}
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3">
                        <MetricCard label={copy.beforeValue} value={holding.beforeValue} />
                        <MetricCard label={copy.afterValue} value={holding.afterValue} />
                        <MetricCard label={copy.estimatedImpact} value={holding.delta} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
