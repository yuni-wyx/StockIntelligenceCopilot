"use client";

import type { ScenarioComparisonResponse, ScenarioResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import {
  EmptyState,
  Field,
  MetricCard,
  formatNumber,
  inputClassName,
  textareaClassName,
} from "./shared";
import type {
  ComparisonScenarioDraft,
  ComparisonScenarioKind,
  ScenarioForm,
} from "./types";

export function ScenarioSimulatorSection({
  copy,
  loading,
  normalizedHoldingsCount,
  scenarioForm,
  onScenarioFormChange,
  onRunScenario,
  scenario,
}: {
  copy: WealthStudioCopy;
  loading: boolean;
  normalizedHoldingsCount: number;
  scenarioForm: ScenarioForm;
  onScenarioFormChange: (updater: (prev: ScenarioForm) => ScenarioForm) => void;
  onRunScenario: () => void;
  scenario: ScenarioResponse | null;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
      <h2 className="text-xl font-semibold">{copy.scenarioSimulator}</h2>
      <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.scenarioSimulatorHelper}</p>
      <div className="mt-4 space-y-4">
        <Field label={copy.sellTicker}>
          <input
            value={scenarioForm.sellTicker}
            onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, sellTicker: e.target.value }))}
            placeholder="00878"
            className={inputClassName}
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={copy.sellShares}>
            <input
              value={scenarioForm.sellShares}
              onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, sellShares: e.target.value }))}
              inputMode="decimal"
              placeholder="Optional"
              className={inputClassName}
            />
          </Field>
          <Field label={copy.sellPercent}>
            <input
              value={scenarioForm.sellPercentage}
              onChange={(e) =>
                onScenarioFormChange((prev) => ({
                  ...prev,
                  sellPercentage: e.target.value,
                }))
              }
              inputMode="decimal"
              placeholder="50"
              className={inputClassName}
            />
          </Field>
        </div>
        <Field label={copy.buyTicker}>
          <input
            value={scenarioForm.buyTicker}
            onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, buyTicker: e.target.value }))}
            placeholder="2330"
            className={inputClassName}
          />
        </Field>
        <Field label={copy.buyAmount}>
          <input
            value={scenarioForm.buyAmount}
            onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, buyAmount: e.target.value }))}
            inputMode="decimal"
            placeholder="35000"
            className={inputClassName}
          />
        </Field>
        <Field label={copy.buyName}>
          <input
            value={scenarioForm.buyName}
            onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, buyName: e.target.value }))}
            placeholder="Optional fund or company name"
            className={inputClassName}
          />
        </Field>
        <Field label={copy.scenarioQuestion}>
          <textarea
            value={scenarioForm.question}
            onChange={(e) => onScenarioFormChange((prev) => ({ ...prev, question: e.target.value }))}
            rows={5}
            placeholder="What do you want to know?"
            className={textareaClassName}
          />
        </Field>
        <button
          onClick={onRunScenario}
          disabled={loading || normalizedHoldingsCount === 0}
          className="w-full rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
        >
          {copy.runScenario}
        </button>
      </div>

      <ScenarioResultSection copy={copy} scenario={scenario} />
    </section>
  );
}

function ScenarioResultSection({
  copy,
  scenario,
}: {
  copy: WealthStudioCopy;
  scenario: ScenarioResponse | null;
}) {
  return (
    <div className="mt-6">
      <h2 className="text-xl font-semibold">{copy.scenarioResult}</h2>
      {!scenario ? (
        <EmptyState title={copy.noScenarioTitle} body={copy.noScenarioBody} />
      ) : (
        <div className="mt-4 space-y-4">
          <p className="text-sm leading-6 text-zinc-300">{scenario.recommendation}</p>
          <div className="grid gap-3">
            <MetricCard label={copy.beforeValue} value={scenario.before.total_current_value} />
            <MetricCard label={copy.afterValue} value={scenario.after.total_current_value} />
            <MetricCard label={copy.dividendChange} value={scenario.dividend_change} />
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <h3 className="font-semibold">{copy.riskTradeoff}</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-300">{scenario.risk_change_summary}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
            <h3 className="font-semibold">{copy.caveats}</h3>
            {scenario.caveats.length === 0 ? (
              <p className="mt-4 text-sm text-zinc-400">{copy.noCaveats}</p>
            ) : (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
                {scenario.caveats.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ScenarioComparisonSection({
  copy,
  loading,
  comparisonScenarios,
  comparisonValidation,
  compareJson,
  onCompareJsonChange,
  onAddComparisonScenario,
  onRemoveComparisonScenario,
  onUpdateComparisonScenario,
  onRunScenarioComparison,
  comparison,
  scenarioKindOptions,
  scenarioKindLabel,
  scenarioKindHelper,
}: {
  copy: WealthStudioCopy;
  loading: boolean;
  comparisonScenarios: ComparisonScenarioDraft[];
  comparisonValidation: string[];
  compareJson: string;
  onCompareJsonChange: (value: string) => void;
  onAddComparisonScenario: () => void;
  onRemoveComparisonScenario: (id: string) => void;
  onUpdateComparisonScenario: (
    id: string,
    field: keyof ComparisonScenarioDraft,
    value: string,
  ) => void;
  onRunScenarioComparison: () => void;
  comparison: ScenarioComparisonResponse | null;
  scenarioKindOptions: Array<{ value: ComparisonScenarioKind }>;
  scenarioKindLabel: (kind: ComparisonScenarioKind, copy: WealthStudioCopy) => string;
  scenarioKindHelper: (kind: ComparisonScenarioKind, copy: WealthStudioCopy) => string;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
      <h2 className="text-xl font-semibold">{copy.scenarioComparison}</h2>
      <p className="mt-1 text-sm leading-6 text-zinc-400">{copy.scenarioComparisonHelper}</p>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-zinc-400">
          {comparisonScenarios.length > 0
            ? `${comparisonScenarios.length} ${
                comparisonScenarios.length === 1
                  ? copy.structuredScenarioReady
                  : copy.structuredScenariosReady
              }`
            : copy.noStructuredScenarios}
        </div>
        <button
          onClick={onAddComparisonScenario}
          className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-100"
        >
          {copy.addScenario}
        </button>
      </div>

      {comparisonScenarios.length === 0 ? (
        <EmptyState title={copy.noComparisonTitle} body={copy.noComparisonBody} />
      ) : (
        <div className="mt-4 space-y-4">
          {comparisonScenarios.map((scenarioItem, index) => (
            <StructuredScenarioCard
              key={scenarioItem.id}
              copy={copy}
              index={index}
              scenarioItem={scenarioItem}
              onRemoveComparisonScenario={onRemoveComparisonScenario}
              onUpdateComparisonScenario={onUpdateComparisonScenario}
              scenarioKindOptions={scenarioKindOptions}
              scenarioKindLabel={scenarioKindLabel}
              scenarioKindHelper={scenarioKindHelper}
            />
          ))}
        </div>
      )}

      {comparisonValidation.length > 0 ? (
        <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
          <h3 className="text-sm font-semibold text-amber-100">{copy.validationScenarioTitle}</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-100/85">
            {comparisonValidation.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <button
          onClick={onRunScenarioComparison}
          disabled={loading}
          className="rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
        >
          {copy.runScenarioComparison}
        </button>
        <span className="text-sm text-zinc-500">
          {comparisonScenarios.length === 0 ? copy.advancedJsonHint : copy.structuredPayloadHint}
        </span>
      </div>

      <details className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
          {copy.advancedJsonEditor}
        </summary>
        <p className="mt-2 text-sm leading-6 text-zinc-500">{copy.advancedJsonHelper}</p>
        <textarea
          value={compareJson}
          onChange={(e) => onCompareJsonChange(e.target.value)}
          rows={10}
          className="mt-4 min-h-64 w-full resize-y rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-sm leading-6 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50"
        />
      </details>

      {comparison ? <ScenarioComparisonResultsTable comparison={comparison} copy={copy} /> : null}
    </section>
  );
}

function StructuredScenarioCard({
  copy,
  index,
  scenarioItem,
  onRemoveComparisonScenario,
  onUpdateComparisonScenario,
  scenarioKindOptions,
  scenarioKindLabel,
  scenarioKindHelper,
}: {
  copy: WealthStudioCopy;
  index: number;
  scenarioItem: ComparisonScenarioDraft;
  onRemoveComparisonScenario: (id: string) => void;
  onUpdateComparisonScenario: (
    id: string,
    field: keyof ComparisonScenarioDraft,
    value: string,
  ) => void;
  scenarioKindOptions: Array<{ value: ComparisonScenarioKind }>;
  scenarioKindLabel: (kind: ComparisonScenarioKind, copy: WealthStudioCopy) => string;
  scenarioKindHelper: (kind: ComparisonScenarioKind, copy: WealthStudioCopy) => string;
}) {
  const needsPercentage =
    scenarioItem.kind === "sell_percentage" || scenarioItem.kind === "reduce_concentration";

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200/60">
            {copy.scenario} {index + 1}
          </div>
          <h3 className="mt-1 font-semibold">
            {scenarioItem.name.trim() || `Scenario ${index + 1}`}
          </h3>
          <p className="mt-1 text-sm leading-6 text-zinc-400">
            {scenarioKindHelper(scenarioItem.kind, copy)}
          </p>
        </div>
        <button
          onClick={() => onRemoveComparisonScenario(scenarioItem.id)}
          className="rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 transition hover:border-rose-300/50 hover:text-rose-200"
        >
          {copy.remove}
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1.2fr]">
        <Field label={copy.scenarioName}>
          <input
            value={scenarioItem.name}
            onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "name", e.target.value)}
            placeholder={`Scenario ${index + 1}`}
            className={inputClassName}
          />
        </Field>
        <Field label={copy.scenarioType}>
          <select
            value={scenarioItem.kind}
            onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "kind", e.target.value)}
            className={inputClassName}
          >
            {scenarioKindOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {scenarioKindLabel(option.value, copy)}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <Field label={copy.ticker}>
          <input
            value={scenarioItem.ticker}
            onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "ticker", e.target.value)}
            placeholder={needsPercentage ? "00878" : "2330"}
            className={inputClassName}
          />
        </Field>
        {needsPercentage ? (
          <Field label={copy.sellPercentage}>
            <input
              value={scenarioItem.percentage}
              onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "percentage", e.target.value)}
              inputMode="decimal"
              placeholder="50"
              className={inputClassName}
            />
          </Field>
        ) : (
          <Field label={copy.buyAmount}>
            <input
              value={scenarioItem.amount}
              onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "amount", e.target.value)}
              inputMode="decimal"
              placeholder="35000"
              className={inputClassName}
            />
          </Field>
        )}
        <Field label={copy.question}>
          <input
            value={scenarioItem.question}
            onChange={(e) => onUpdateComparisonScenario(scenarioItem.id, "question", e.target.value)}
            placeholder="What tradeoff should we evaluate?"
            className={inputClassName}
          />
        </Field>
      </div>
    </div>
  );
}

function ScenarioComparisonResultsTable({
  comparison,
  copy,
}: {
  comparison: ScenarioComparisonResponse;
  copy: WealthStudioCopy;
}) {
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="min-w-[680px] text-left text-sm">
        <thead className="text-zinc-400">
          <tr>
            {[
              copy.scenario,
              copy.rank,
              copy.scoreDelta,
              copy.dividendDelta,
              copy.techDelta,
              copy.defensiveDelta,
              copy.concentrationDelta,
            ].map((label) => (
              <th key={label} className="px-2 py-2 font-medium">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {comparison.scenarios.map((item) => (
            <tr key={item.name} className="border-t border-white/5">
              <td className="px-2 py-2">{item.name}</td>
              <td className="px-2 py-2">{item.recommendation_rank}</td>
              <td className="px-2 py-2">{item.overall_score_change}</td>
              <td className="px-2 py-2">{formatNumber(item.dividend_change)}</td>
              <td className="px-2 py-2">{formatNumber(item.technology_exposure_change)}%</td>
              <td className="px-2 py-2">{formatNumber(item.defensive_allocation_change)}%</td>
              <td className="px-2 py-2">{formatNumber(item.concentration_change)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
