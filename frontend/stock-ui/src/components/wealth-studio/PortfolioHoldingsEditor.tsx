"use client";

import type { WealthStudioCopy } from "@/i18n/messages";
import { normalizeTicker, tickerDisplayName } from "@/lib/tickerMap";
import {
  EmptyState,
  Field,
  MiniMetric,
  inputClassName,
} from "./shared";
import type {
  EditableHolding,
  HoldingDerivedMetrics,
  PortfolioImportPreview,
  PortfolioImportOnboardingSummary,
  HoldingValidationField,
  HoldingsValidationState,
} from "./types";

type Props = {
  copy: WealthStudioCopy;
  holdings: EditableHolding[];
  holdingsValidation: HoldingsValidationState;
  riskProfile: string;
  goal: string;
  loading: boolean;
  onAddHolding: () => void;
  onRemoveHolding: (index: number) => void;
  onUpdateHolding: (index: number, field: keyof EditableHolding, value: string) => void;
  onRiskProfileChange: (value: string) => void;
  onGoalChange: (value: string) => void;
  onAnalyze: () => void;
  onSave: () => void;
  onLoad: () => void;
  onPreviewImportFile: (file: File | null) => void;
  onApplyImportPreview: () => void;
  onRunImportAnalyze: () => void;
  onRunImportCoach: () => void;
  onRunImportStressTest: () => void;
  calculateHoldingMetrics: (holding: EditableHolding) => HoldingDerivedMetrics;
  holdingInputClass: (index: number, field: HoldingValidationField) => string;
  importPreview: PortfolioImportPreview | null;
  importFileName: string | null;
  importError: string | null;
  importOnboardingSummary: PortfolioImportOnboardingSummary | null;
  topReviewItem?: string | null;
  topConcentrationFlag?: string | null;
};

export function PortfolioHoldingsEditor({
  copy,
  holdings,
  holdingsValidation,
  riskProfile,
  goal,
  loading,
  onAddHolding,
  onRemoveHolding,
  onUpdateHolding,
  onRiskProfileChange,
  onGoalChange,
  onAnalyze,
  onSave,
  onLoad,
  onPreviewImportFile,
  onApplyImportPreview,
  onRunImportAnalyze,
  onRunImportCoach,
  onRunImportStressTest,
  calculateHoldingMetrics,
  holdingInputClass,
  importPreview,
  importFileName,
  importError,
  importOnboardingSummary,
  topReviewItem,
  topConcentrationFlag,
}: Props) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{copy.yourHoldings}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
            {copy.holdingsHelper}
          </p>
        </div>
        <button
          onClick={onAddHolding}
          className="w-full rounded-xl bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-amber-100 sm:w-auto"
        >
          {copy.addHolding}
        </button>
      </div>

      {holdingsValidation.hasErrors ? (
        <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
          <h3 className="text-sm font-semibold text-amber-100">{copy.holdingValidationTitle}</h3>
          <p className="mt-1 text-sm leading-6 text-amber-100/75">
            {copy.holdingValidationHelper}
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-100/85">
            {holdingsValidation.messages.map((message) => (
              <li key={`${message.rowIndex}-${message.field}-${message.message}`}>
                {message.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">{copy.csvImportTitle}</h3>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
              {copy.csvImportHelper}
            </p>
          </div>
          <label className="cursor-pointer rounded-xl border border-dashed border-white/15 bg-black/20 px-4 py-3 text-sm text-zinc-200 transition hover:border-white/25 hover:bg-black/30">
            <span className="font-medium">{copy.csvSelectFile}</span>
            <span className="mt-1 block text-xs leading-5 text-zinc-500">{copy.csvDropHint}</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(event) => onPreviewImportFile(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        {importError ? (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {importError}
          </div>
        ) : null}

        {importPreview ? (
          <div className="mt-4 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="text-sm font-semibold text-zinc-100">{copy.csvPreviewTitle}</div>
                <p className="mt-1 text-sm leading-6 text-zinc-400">
                  {importFileName ? `${importFileName} · ` : ""}
                  {copy.csvImportReplaces}
                </p>
              </div>
              <button
                onClick={onApplyImportPreview}
                disabled={loading || importPreview.imported_count === 0}
                className="w-full rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50 lg:w-auto"
              >
                {copy.csvApplyImport}
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MiniMetric label={copy.csvImportedCount} value={importPreview.imported_count} />
              <MiniMetric label={copy.csvTotalRows} value={importPreview.total_rows} />
              <MiniMetric label={copy.csvErrorCount} value={importPreview.errors.length} />
              <MiniMetric label={copy.csvWarningCount} value={importPreview.warnings.length} />
            </div>

            {importPreview.detected_columns.length > 0 ? (
              <div>
                <div className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
                  {copy.csvDetectedColumns}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {importPreview.detected_columns.map((column) => (
                    <span
                      key={column}
                      className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs text-zinc-300"
                    >
                      {column}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {importPreview.holdings.length > 0 ? (
              <div className="space-y-2">
                <div className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
                  {copy.csvPreviewRows}
                </div>
                <div className="space-y-2">
                  {importPreview.holdings.slice(0, 5).map((holding, index) => (
                    <div
                      key={`${holding.ticker}-${index}`}
                      className="flex flex-col gap-1 rounded-xl border border-white/10 bg-black/25 p-3 text-sm text-zinc-300 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0">
                        <div className="font-medium text-zinc-100">
                          {normalizeTicker(holding.ticker)}
                          {holding.name ? ` · ${holding.name}` : ""}
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {copy.shares}: {holding.shares ?? "—"} · {copy.currentPrice}:{" "}
                          {holding.current_price ?? "—"} · {copy.avgCost}: {holding.avg_cost ?? "—"}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {importPreview.errors.length > 0 ? (
              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4">
                <div className="text-sm font-semibold text-rose-200">{copy.csvImportErrors}</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-rose-100/90">
                  {importPreview.errors.map((item) => (
                    <li key={`error-${item.row_number}-${item.message}`}>
                      {copy.rowLabel} {item.row_number}: {item.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {importPreview.warnings.length > 0 ? (
              <div className="rounded-2xl border border-amber-300/20 bg-amber-300/5 p-4">
                <div className="text-sm font-semibold text-amber-100">{copy.csvImportWarnings}</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-50/90">
                  {importPreview.warnings.map((item) => (
                    <li key={`warning-${item.row_number}-${item.message}`}>
                      {copy.rowLabel} {item.row_number}: {item.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {importOnboardingSummary ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h3 className="text-base font-semibold text-zinc-100">
                {copy.importOnboardingTitle}
              </h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
                {copy.importOnboardingHelper}
              </p>
            </div>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-300">
              {importOnboardingSummary.fileName || copy.csvImportTitle}
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MiniMetric
              label={copy.csvImportedCount}
              value={importOnboardingSummary.importedCount}
            />
            <MiniMetric
              label={copy.importTotalPositions}
              value={importOnboardingSummary.totalPositions}
            />
            <MiniMetric
              label={copy.csvWarningCount}
              value={importOnboardingSummary.warningsCount}
            />
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-xs text-zinc-500">{copy.importDetectedMarkets}</div>
              <div className="mt-2 text-sm font-medium text-zinc-100">
                {importOnboardingSummary.detectedMarkets.join(", ") || copy.noExposure}
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-sm font-semibold text-zinc-100">{copy.importOnboardingInsights}</div>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-zinc-300">
                <li>
                  {copy.importLargestHolding}: {importOnboardingSummary.largestHoldingLabel}
                  {importOnboardingSummary.largestHoldingValue !== undefined
                    ? ` (${importOnboardingSummary.largestHoldingValue.toFixed(2)})`
                    : ""}
                </li>
                {importOnboardingSummary.concentrationWarning ? (
                  <li>{importOnboardingSummary.concentrationWarning}</li>
                ) : null}
                {importOnboardingSummary.missingDataWarning ? (
                  <li>{importOnboardingSummary.missingDataWarning}</li>
                ) : null}
                <li>{importOnboardingSummary.dividendDataAvailability}</li>
                {topReviewItem ? <li>{topReviewItem}</li> : null}
                {topConcentrationFlag ? <li>{topConcentrationFlag}</li> : null}
              </ul>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="text-sm font-semibold text-zinc-100">{copy.importNextActions}</div>
              <p className="mt-2 text-sm leading-6 text-zinc-400">{copy.importNextActionsHelper}</p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <button
                  onClick={onRunImportAnalyze}
                  disabled={loading}
                  className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                >
                  {copy.analyzeHoldings}
                </button>
                <button
                  onClick={onRunImportCoach}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  {copy.askAboutMyPortfolio}
                </button>
                <button
                  onClick={onRunImportStressTest}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-4 py-2.5 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  {copy.runStressTest}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {holdings.length === 0 ? <EmptyState title={copy.noHoldingsTitle} body={copy.noHoldingsBody} /> : null}

        {holdings.map((holding, index) => {
          const canonicalTicker = normalizeTicker(holding.ticker);
          const displayName = tickerDisplayName(holding.ticker);
          const knownDisplayName =
            holding.ticker.trim() && displayName !== canonicalTicker ? displayName : "";
          const derivedMetrics = calculateHoldingMetrics(holding);

          return (
            <div
              key={holding._rowId}
              className="rounded-2xl border border-white/10 bg-black/25 p-4"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:grid-cols-[0.9fr_1.4fr_0.9fr_0.9fr]">
                  <Field label={copy.ticker}>
                    <input
                      value={holding.ticker}
                      onChange={(e) => onUpdateHolding(index, "ticker", e.target.value)}
                      placeholder="00878 or NVDA"
                      className={holdingInputClass(index, "ticker")}
                    />
                    {knownDisplayName ? (
                      <span className="mt-1.5 block text-xs leading-5 text-amber-100/70">
                        {canonicalTicker} → {knownDisplayName}
                      </span>
                    ) : null}
                  </Field>
                  <Field label={copy.name}>
                    <input
                      value={holding.name ?? ""}
                      onChange={(e) => onUpdateHolding(index, "name", e.target.value)}
                      className={inputClassName}
                    />
                  </Field>
                  <Field label={copy.shares}>
                    <input
                      value={holding.shares ?? ""}
                      onChange={(e) => onUpdateHolding(index, "shares", e.target.value)}
                      inputMode="decimal"
                      placeholder="2239"
                      className={holdingInputClass(index, "shares")}
                    />
                  </Field>
                  <Field label={copy.currentPrice}>
                    <input
                      value={holding.current_price ?? ""}
                      onChange={(e) => onUpdateHolding(index, "current_price", e.target.value)}
                      inputMode="decimal"
                      placeholder="0 or higher"
                      className={holdingInputClass(index, "current_price")}
                    />
                  </Field>
                </div>
                <button
                  onClick={() => onRemoveHolding(index)}
                  className="rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 transition hover:border-rose-300/50 hover:text-rose-200"
                >
                  {copy.remove}
                </button>
              </div>

              <details className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
                <summary className="cursor-pointer text-sm font-medium text-zinc-200">
                  {copy.holdingDetails}
                </summary>
                <p className="mt-2 text-sm leading-6 text-zinc-500">{copy.holdingDetailsHelper}</p>

                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  <Field label={copy.avgCost}>
                    <input
                      value={holding.avg_cost ?? ""}
                      onChange={(e) => onUpdateHolding(index, "avg_cost", e.target.value)}
                      inputMode="decimal"
                      placeholder="0 or higher"
                      className={holdingInputClass(index, "avg_cost")}
                    />
                  </Field>
                  <Field label={copy.currentValue}>
                    <input
                      value={holding.current_value ?? ""}
                      onChange={(e) => onUpdateHolding(index, "current_value", e.target.value)}
                      inputMode="decimal"
                      placeholder={
                        derivedMetrics.currentValue !== undefined
                          ? String(derivedMetrics.currentValue)
                          : ""
                      }
                      className={holdingInputClass(index, "current_value")}
                    />
                  </Field>
                  <Field label={copy.assetType} helper={copy.assetTypeHelper}>
                    <input
                      value={holding.asset_type ?? ""}
                      onChange={(e) => onUpdateHolding(index, "asset_type", e.target.value)}
                      placeholder="ETF, stock, fund..."
                      className={inputClassName}
                    />
                  </Field>
                  <Field label={copy.category} helper={copy.categoryHelper}>
                    <input
                      value={holding.category ?? ""}
                      onChange={(e) => onUpdateHolding(index, "category", e.target.value)}
                      placeholder="High Dividend, Tech..."
                      className={inputClassName}
                    />
                  </Field>
                  <Field label={copy.notes}>
                    <input
                      value={holding.notes ?? ""}
                      onChange={(e) => onUpdateHolding(index, "notes", e.target.value)}
                      className={inputClassName}
                    />
                  </Field>
                </div>

                <div className="mt-4 grid gap-3 rounded-xl border border-white/10 bg-black/20 p-3 sm:grid-cols-2 xl:grid-cols-4">
                  <MiniMetric label={copy.costBasis} value={derivedMetrics.costBasis} />
                  <MiniMetric label={copy.holdingValue} value={derivedMetrics.currentValue} />
                  <MiniMetric label={copy.unrealizedPL} value={derivedMetrics.unrealizedGainLoss} />
                  <MiniMetric label={copy.returnPct} value={derivedMetrics.returnPct} suffix="%" />
                </div>
              </details>
            </div>
          );
        })}
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-[0.45fr_1fr]">
        <Field label={copy.riskProfile}>
          <input
            value={riskProfile}
            onChange={(e) => onRiskProfileChange(e.target.value)}
            placeholder="Balanced"
            className={inputClassName}
          />
        </Field>
        <Field label={copy.goal}>
          <input
            value={goal}
            onChange={(e) => onGoalChange(e.target.value)}
            placeholder="Preserve income while improving diversification"
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <button
          onClick={onAnalyze}
          disabled={loading || holdingsValidation.hasErrors}
          className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
        >
          {loading ? copy.working : copy.analyzeHoldings}
        </button>
        <button
          onClick={onSave}
          disabled={loading}
          className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
        >
          {copy.saveWorkspace}
        </button>
        <button
          onClick={onLoad}
          disabled={loading}
          className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
        >
          {copy.loadSaved}
        </button>
      </div>
    </section>
  );
}
