"use client";

import type { ScenarioComparisonResponse, ScenarioResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import { PortfolioStressTestSection } from "./PortfolioStressTestSection";
import {
  ScenarioComparisonSection,
  ScenarioSimulatorSection,
} from "./PortfolioScenarioSections";
import type {
  ComparisonScenarioDraft,
  ComparisonScenarioKind,
  ScenarioForm,
  StressTestForm,
  StressTestResult,
} from "./types";

type Props = {
  copy: WealthStudioCopy;
  loading: boolean;
  normalizedHoldingsCount: number;
  scenarioForm: ScenarioForm;
  onScenarioFormChange: (updater: (prev: ScenarioForm) => ScenarioForm) => void;
  onRunScenario: () => void;
  scenario: ScenarioResponse | null;
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
  stressTestForm: StressTestForm;
  stressTestError: string | null;
  stressTestResult: StressTestResult | null;
  onStressTestFormChange: (updater: (prev: StressTestForm) => StressTestForm) => void;
  onRunStressTest: () => void;
};

export function PortfolioScenarioPanel({
  copy,
  loading,
  normalizedHoldingsCount,
  scenarioForm,
  onScenarioFormChange,
  onRunScenario,
  scenario,
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
  stressTestForm,
  stressTestError,
  stressTestResult,
  onStressTestFormChange,
  onRunStressTest,
}: Props) {
  return (
    <details className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
      <summary className="cursor-pointer text-xl font-semibold text-white">
        {copy.advancedScenarioTools}
      </summary>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{copy.advancedScenarioToolsHelper}</p>

      <div className="mt-5 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <PortfolioStressTestSection
          copy={copy}
          loading={loading}
          stressTestForm={stressTestForm}
          stressTestError={stressTestError}
          stressTestResult={stressTestResult}
          onStressTestFormChange={onStressTestFormChange}
          onRunStressTest={onRunStressTest}
        />

        <ScenarioSimulatorSection
          copy={copy}
          loading={loading}
          normalizedHoldingsCount={normalizedHoldingsCount}
          scenarioForm={scenarioForm}
          onScenarioFormChange={onScenarioFormChange}
          onRunScenario={onRunScenario}
          scenario={scenario}
        />
      </div>

      <div className="mt-6">
        <ScenarioComparisonSection
          copy={copy}
          loading={loading}
          comparisonScenarios={comparisonScenarios}
          comparisonValidation={comparisonValidation}
          compareJson={compareJson}
          onCompareJsonChange={onCompareJsonChange}
          onAddComparisonScenario={onAddComparisonScenario}
          onRemoveComparisonScenario={onRemoveComparisonScenario}
          onUpdateComparisonScenario={onUpdateComparisonScenario}
          onRunScenarioComparison={onRunScenarioComparison}
          comparison={comparison}
          scenarioKindOptions={scenarioKindOptions}
          scenarioKindLabel={scenarioKindLabel}
          scenarioKindHelper={scenarioKindHelper}
        />
      </div>
    </details>
  );
}
