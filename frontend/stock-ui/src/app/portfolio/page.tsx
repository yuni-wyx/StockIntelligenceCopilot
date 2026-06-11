"use client";

import { useMemo, useState } from "react";
import { PortfolioCoachPanel } from "@/components/wealth-studio/PortfolioCoachPanel";
import { PortfolioHoldingsEditor } from "@/components/wealth-studio/PortfolioHoldingsEditor";
import { PortfolioMonitorPanel } from "@/components/wealth-studio/PortfolioMonitorPanel";
import { PortfolioSnapshotPanel } from "@/components/wealth-studio/PortfolioSnapshotPanel";
import { PortfolioScenarioPanel } from "@/components/wealth-studio/PortfolioScenarioPanel";
import { SavedWorkspacesPanel } from "@/components/wealth-studio/SavedWorkspacesPanel";
import { SectionIntro, invalidInputClassName, inputClassName } from "@/components/wealth-studio/shared";
import type {
  ComparisonPayloadScenario,
  ComparisonScenarioDraft,
  EditableHolding,
  HoldingValidationField,
  ScenarioForm,
  StressTestForm,
  StressTestResult,
  WealthStudioOperation,
} from "@/components/wealth-studio/types";
import { runPortfolioStressTest } from "@/components/wealth-studio/stressTest";
import {
  calculateEditableHoldingMetrics,
  normalizeHoldings,
  parseOptionalNumber,
  toEditableHolding,
} from "@/components/wealth-studio/transforms";
import {
  DEFAULT_COMPARE_JSON,
  buildScenarioActions,
  createComparisonScenarioDraft,
  createPortfolioPayload,
  normalizeComparisonPayload,
  scenarioKindHelper,
  scenarioKindLabel,
  scenarioKindOptions,
} from "@/components/wealth-studio/utils";
import {
  buildStructuredComparisonScenarios as buildStructuredComparisonPayload,
  validateHoldings,
} from "@/components/wealth-studio/validation";
import { WealthStudioGuide } from "@/components/wealth-studio/WealthStudioGuide";
import { WealthStudioHeader } from "@/components/wealth-studio/WealthStudioHeader";
import { useLanguage } from "@/context/LanguageContext";
import {
  analyzePortfolio,
  askAboutPortfolio,
  comparePortfolioScenarios,
  listSavedPortfolios,
  loadCurrentPortfolio,
  previewPortfolioImport,
  getPortfolioMonitor,
  runPortfolioScenario,
  savePortfolio,
  type HoldingInput,
  type PortfolioImportPreviewResponse,
  type PortfolioAnalysisResponse,
  type PortfolioChatResponse,
  type PortfolioMonitorResponse,
  type ScenarioComparisonResponse,
  type ScenarioResponse,
} from "@/lib/portfolioApi";
import { appendHolding } from "@/lib/portfolioState";
import { detectTickerMarket, normalizeTicker, tickerDisplayName } from "@/lib/tickerMap";

export default function PortfolioPage() {
  const { t, locale } = useLanguage();
  const ws = t.wealthStudio;
  const [holdings, setHoldings] = useState<EditableHolding[]>(() => [
    toEditableHolding(
      {
        ticker: "00878",
        name: "國泰永續高股息",
        avg_cost: 21.76,
        current_price: 32.06,
        shares: 2239,
        asset_type: "ETF",
        category: "High Dividend",
      },
      "holding-initial-00878",
    ),
  ]);
  const [riskProfile, setRiskProfile] = useState("Balanced");
  const [goal, setGoal] = useState(
    "Preserve income while improving diversification",
  );
  const [loading, setLoading] = useState(false);
  const [activeOperation, setActiveOperation] = useState<WealthStudioOperation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null);
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [portfolioChatResponse, setPortfolioChatResponse] =
    useState<PortfolioChatResponse | null>(null);
  const [portfolioMonitorResponse, setPortfolioMonitorResponse] =
    useState<PortfolioMonitorResponse | null>(null);
  const [importPreview, setImportPreview] = useState<PortfolioImportPreviewResponse | null>(null);
  const [importFileName, setImportFileName] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [monitorError, setMonitorError] = useState<string | null>(null);
  const [savedPortfolios, setSavedPortfolios] = useState<Array<Record<string, unknown>>>([]);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
  const [compareJson, setCompareJson] = useState(DEFAULT_COMPARE_JSON);
  const [comparison, setComparison] = useState<ScenarioComparisonResponse | null>(null);
  const [comparisonScenarios, setComparisonScenarios] = useState<ComparisonScenarioDraft[]>([]);
  const [comparisonValidation, setComparisonValidation] = useState<string[]>([]);
  const [stressTestForm, setStressTestForm] = useState<StressTestForm>({
    preset: "broad_market_20",
    customTicker: "",
    customShockPct: "-20",
  });
  const [stressTestError, setStressTestError] = useState<string | null>(null);
  const [stressTestResult, setStressTestResult] = useState<StressTestResult | null>(null);
  const [scenarioForm, setScenarioForm] = useState<ScenarioForm>({
    sellTicker: "",
    sellShares: "",
    sellPercentage: "50",
    buyTicker: "",
    buyAmount: "",
    buyName: "",
    question: "Should I reduce one position and redeploy into a new fund?",
  });
  const [agentQuestion, setAgentQuestion] = useState(
    "Which holdings should I review first if my portfolio feels too concentrated?",
  );

  const normalizedHoldings = useMemo(() => normalizeHoldings(holdings), [holdings]);
  const portfolioQuestionChips = useMemo(
    () => [
      { id: "concentration", label: ws.portfolioChatStarterConcentration },
      { id: "review", label: ws.portfolioChatStarterReview },
      { id: "income", label: ws.portfolioChatStarterIncome },
      { id: "tech", label: ws.portfolioChatStarterTech },
    ],
    [ws],
  );
  const importOnboardingSummary = useMemo(() => {
    if (!importFileName || normalizedHoldings.length === 0) {
      return null;
    }

    const holdingsWithValue = holdings.map((holding) => {
      const derived = calculateEditableHoldingMetrics(holding);
      return {
        holding,
        currentValue:
          derived.currentValue ??
          parseOptionalNumber(holding.current_value) ??
          0,
      };
    });
    const largest = [...holdingsWithValue].sort(
      (left, right) => right.currentValue - left.currentValue,
    )[0];
    const totalValue = holdingsWithValue.reduce(
      (sum, item) => sum + item.currentValue,
      0,
    );
    const largestWeight =
      totalValue > 0 && largest ? (largest.currentValue / totalValue) * 100 : 0;
    const missingPriceOrValue = holdings.some((holding) => {
      const currentPrice = parseOptionalNumber(holding.current_price);
      const currentValue = parseOptionalNumber(holding.current_value);
      return currentPrice === undefined && currentValue === undefined;
    });
    const detectedMarkets = Array.from(
      new Set(
        normalizedHoldings
          .map((holding) => detectTickerMarket(holding.ticker))
          .filter(Boolean),
      ),
    );

    return {
      fileName: importFileName,
      importedCount: normalizedHoldings.length,
      totalPositions: normalizedHoldings.length,
      detectedMarkets,
      warningsCount: importPreview?.warnings.length ?? 0,
      largestHoldingLabel: largest
        ? tickerDisplayName(largest.holding.ticker || largest.holding.name || "")
        : ws.noHoldingsTitle,
      largestHoldingValue: largest?.currentValue,
      concentrationWarning:
        largestWeight >= 25 ? ws.importConcentrationWarning : undefined,
      missingDataWarning:
        missingPriceOrValue || (importPreview?.warnings.length ?? 0) > 0
          ? ws.importMissingDataWarning
          : undefined,
      dividendDataAvailability: ws.importDividendAvailability,
    };
  }, [holdings, importFileName, importPreview, normalizedHoldings, ws]);
  const topReviewItem = analysis?.portfolio_intelligence?.suggested_review_items?.[0]
    ? `${ws.review}: ${analysis.portfolio_intelligence.suggested_review_items[0].title}`
    : null;
  const topConcentrationFlag = analysis?.portfolio_intelligence?.concentration?.flags?.[0]
    ? `${ws.concentrationAnalysis}: ${analysis.portfolio_intelligence.concentration.flags[0]}`
    : null;

  const holdingsValidation = useMemo(
    () =>
      validateHoldings(holdings, {
        tickerRequired: ws.tickerRequired,
        sharesRequired: ws.sharesRequired,
        sharesPositive: ws.sharesPositive,
        avgCostNonNegative: ws.avgCostNonNegative,
        currentPriceNonNegative: ws.currentPriceNonNegative,
        currentValueNonNegative: ws.currentValueNonNegative,
        noHoldingsBody: ws.noHoldingsBody,
      }),
    [holdings, ws],
  );

  function currentPortfolioPayload() {
    return createPortfolioPayload(normalizedHoldings, riskProfile, goal);
  }

  function resetDerivedViews() {
    setAnalysis(null);
    setScenario(null);
    setComparison(null);
    setStressTestResult(null);
    setPortfolioChatResponse(null);
    setPortfolioMonitorResponse(null);
    setInsightsError(null);
    setMonitorError(null);
  }

  function updateHolding(index: number, field: keyof EditableHolding, value: string) {
    setHoldings((prev) =>
      prev.map((holding, currentIndex) => {
        if (currentIndex !== index) return holding;
        return {
          ...holding,
          [field]: value,
        };
      }),
    );
  }

  function addHolding() {
    setHoldings((prev) => [...prev, toEditableHolding(appendHolding([])[0])]);
  }

  function removeHolding(index: number) {
    setHoldings((prev) => prev.filter((_, currentIndex) => currentIndex !== index));
  }

  function holdingInputClass(index: number, field: HoldingValidationField) {
    return holdingsValidation.fieldKeys.has(`${index}:${field}`)
      ? invalidInputClassName
      : inputClassName;
  }

  function addComparisonScenario() {
    setComparisonValidation([]);
    setComparisonScenarios((prev) => [...prev, createComparisonScenarioDraft(prev.length)]);
  }

  function removeComparisonScenario(id: string) {
    setComparisonValidation([]);
    setComparisonScenarios((prev) => prev.filter((scenarioItem) => scenarioItem.id !== id));
  }

  function updateComparisonScenario(
    id: string,
    field: keyof ComparisonScenarioDraft,
    value: string,
  ) {
    setComparisonValidation([]);
    setComparisonScenarios((prev) =>
      prev.map((scenarioItem) =>
        scenarioItem.id === id
          ? {
              ...scenarioItem,
              [field]: value,
            }
          : scenarioItem,
      ),
    );
  }

  function buildStructuredComparisonScenarios(): {
    scenarios: ComparisonPayloadScenario[];
    errors: string[];
  } {
    return buildStructuredComparisonPayload(comparisonScenarios, ws, scenarioKindLabel);
  }

  async function handleAnalyze() {
    if (holdingsValidation.hasErrors) {
      setError(ws.analyzeValidationError);
      return;
    }

    setLoading(true);
    setActiveOperation("analyze");
    setError(null);
    setInsightsError(null);
    setScenario(null);
    setPortfolioChatResponse(null);
    try {
      const result = await analyzePortfolio(currentPortfolioPayload());
      setAnalysis(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : ws.failedAnalyze;
      setError(message);
      setInsightsError(message);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handleSave() {
    setLoading(true);
    setActiveOperation("save");
    setError(null);
    try {
      await savePortfolio({
        portfolio: currentPortfolioPayload(),
        name: "current",
        make_current: true,
      });
      setCurrentWorkspaceId("current");
      const listed = await listSavedPortfolios();
      setSavedPortfolios(listed.portfolios);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedSave);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handleLoad() {
    setLoading(true);
    setActiveOperation("load");
    setError(null);
    try {
      const record = await loadCurrentPortfolio();
      if (!record.portfolio) {
        setError(ws.noSavedCurrent);
        return;
      }
      setHoldings((record.portfolio.holdings ?? []).map((holding: HoldingInput) => toEditableHolding(holding)));
      setRiskProfile(record.portfolio.risk_profile ?? "Balanced");
      setGoal(record.portfolio.goal ?? "");
      resetDerivedViews();
      setCurrentWorkspaceId("current");
      const listed = await listSavedPortfolios();
      setSavedPortfolios(listed.portfolios);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedLoad);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handleScenario() {
    setLoading(true);
    setActiveOperation("scenario");
    setError(null);
    try {
      const actions = buildScenarioActions(scenarioForm);
      const result = await runPortfolioScenario({
        portfolio: currentPortfolioPayload(),
        actions,
        target_ticker: scenarioForm.buyTicker
          ? normalizeTicker(scenarioForm.buyTicker)
          : undefined,
        target_name: scenarioForm.buyName || undefined,
        user_question: scenarioForm.question || undefined,
      });
      setScenario(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedScenario);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handleCompareScenarios() {
    setLoading(true);
    setActiveOperation("compare");
    setError(null);
    setComparisonValidation([]);
    try {
      let parsed: ComparisonPayloadScenario[];

      if (comparisonScenarios.length > 0) {
        const structured = buildStructuredComparisonScenarios();
        if (structured.errors.length > 0) {
          setComparisonValidation(structured.errors);
          return;
        }
        parsed = structured.scenarios;
      } else {
        parsed = JSON.parse(compareJson) as ComparisonPayloadScenario[];
      }

      const payload = {
        portfolio: currentPortfolioPayload(),
        scenarios: normalizeComparisonPayload(parsed),
      };
      const result = await comparePortfolioScenarios(payload);
      setComparison(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : ws.failedCompare,
      );
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handleAskAgent(questionOverride?: string) {
    const nextQuestion = questionOverride ?? agentQuestion;
    const hasDirectPortfolio = normalizedHoldings.length > 0;
    const workspaceId = hasDirectPortfolio ? undefined : currentWorkspaceId;

    if (!hasDirectPortfolio && !workspaceId) {
      setError(ws.portfolioChatAddHoldingsFirst);
      return;
    }

    setLoading(true);
    setActiveOperation("coach");
    setError(null);
    if (questionOverride) {
      setAgentQuestion(questionOverride);
    }
    try {
      const response = await askAboutPortfolio({
        question: nextQuestion,
        portfolio: hasDirectPortfolio ? currentPortfolioPayload() : undefined,
        workspace_id: workspaceId || undefined,
        language: locale === "zh" ? "zh" : "en",
      });
      setPortfolioChatResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedCoach);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handlePortfolioMonitor() {
    const hasDirectPortfolio = normalizedHoldings.length > 0;
    const workspaceId = hasDirectPortfolio ? undefined : currentWorkspaceId;

    if (!hasDirectPortfolio && !workspaceId) {
      setMonitorError(ws.portfolioMonitorAddHoldingsFirst);
      return;
    }

    setLoading(true);
    setActiveOperation("monitor");
    setError(null);
    setMonitorError(null);
    try {
      const response = await getPortfolioMonitor({
        portfolio: hasDirectPortfolio ? currentPortfolioPayload() : undefined,
        workspace_id: workspaceId || undefined,
      });
      setPortfolioMonitorResponse(response);
    } catch (err) {
      setMonitorError(err instanceof Error ? err.message : ws.portfolioMonitorAddHoldingsFirst);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  async function handlePreviewImportFile(file: File | null) {
    if (!file) {
      return;
    }

    setLoading(true);
    setActiveOperation("import_preview");
    setError(null);
    setImportError(null);
    try {
      const preview = await previewPortfolioImport(file);
      setImportPreview(preview);
      setImportFileName(file.name);
      if (preview.imported_count === 0) {
        setImportError(ws.csvNoValidRows);
      }
    } catch (err) {
      setImportPreview(null);
      setImportFileName(file.name);
      setImportError(err instanceof Error ? err.message : ws.csvImportFailed);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  function handleApplyImportPreview() {
    if (!importPreview || importPreview.holdings.length === 0) {
      setImportError(ws.csvNoValidRows);
      return;
    }

    setHoldings(
      importPreview.holdings.map((holding, index) =>
        toEditableHolding(holding, `holding-import-${index}`),
      ),
    );
    resetDerivedViews();
    setCurrentWorkspaceId(null);
    setImportPreview(null);
    setImportFileName(null);
    setImportError(null);
  }

  function handleImportCoachShortcut() {
    const question = ws.portfolioChatStarterReview;
    setAgentQuestion(question);
    void handleAskAgent(question);
  }

  function handleRunStressTest() {
    const { result, error: validationError } = runPortfolioStressTest(holdings, stressTestForm, {
      stressTestNoValidHoldings: ws.stressTestNoValidHoldings,
      stressTestCustomTickerRequired: ws.stressTestCustomTickerRequired,
      stressTestShockRequired: ws.stressTestShockRequired,
      stressTestShockRange: ws.stressTestShockRange,
      stressTestBroadMarketExplanation: ws.stressTestBroadMarketExplanation,
      stressTestTechnologyExplanation: ws.stressTestTechnologyExplanation,
      stressTestTaiwanExplanation: ws.stressTestTaiwanExplanation,
      stressTestBondExplanation: ws.stressTestBondExplanation,
      stressTestCustomExplanation: ws.stressTestCustomExplanation,
      stressTestNoMatchingHoldings: ws.stressTestNoMatchingHoldings,
    });

    setStressTestError(validationError);
    setStressTestResult(result);
  }

  function handleStressTestFormChange(updater: (prev: StressTestForm) => StressTestForm) {
    setStressTestError(null);
    setStressTestForm(updater);
  }

  return (
    <div className="min-h-screen bg-[#0d0c0a] px-4 py-6 text-white sm:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <WealthStudioHeader copy={ws} />
        <WealthStudioGuide copy={ws} />

        <SectionIntro title={ws.holdingsSection} helper={ws.holdingsHelper} />
        <PortfolioHoldingsEditor
          copy={ws}
          holdings={holdings}
          holdingsValidation={holdingsValidation}
          riskProfile={riskProfile}
          goal={goal}
          loading={loading}
          onAddHolding={addHolding}
          onRemoveHolding={removeHolding}
          onUpdateHolding={updateHolding}
          onRiskProfileChange={setRiskProfile}
          onGoalChange={setGoal}
          onAnalyze={handleAnalyze}
          onSave={handleSave}
          onLoad={handleLoad}
          onPreviewImportFile={(file) => void handlePreviewImportFile(file)}
          onApplyImportPreview={handleApplyImportPreview}
          onRunImportAnalyze={() => void handleAnalyze()}
          onRunImportCoach={handleImportCoachShortcut}
          onRunImportStressTest={handleRunStressTest}
          calculateHoldingMetrics={calculateEditableHoldingMetrics}
          holdingInputClass={holdingInputClass}
          importPreview={importPreview}
          importFileName={importFileName}
          importError={importError}
          importOnboardingSummary={importOnboardingSummary}
          topReviewItem={topReviewItem}
          topConcentrationFlag={topConcentrationFlag}
        />

        {error ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        ) : null}

        <SectionIntro title={ws.analysisSection} helper={ws.insightsHelper} />
        <PortfolioSnapshotPanel
          copy={ws}
          analysis={analysis}
          activeOperation={activeOperation}
          insightsError={insightsError}
        />

        <SectionIntro title={ws.ideasSection} helper={ws.ideasSectionHelper} />
        <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
          <div className="space-y-6">
            <PortfolioCoachPanel
              copy={ws}
              loading={loading}
              question={agentQuestion}
              onQuestionChange={setAgentQuestion}
              onAsk={() => void handleAskAgent()}
              onAskQuestion={(value) => void handleAskAgent(value)}
              response={portfolioChatResponse}
              starterQuestions={portfolioQuestionChips}
            />
            <PortfolioMonitorPanel
              copy={ws}
              loading={loading && activeOperation === "monitor"}
              canRun={normalizedHoldings.length > 0 || Boolean(currentWorkspaceId)}
              errorMessage={monitorError}
              response={portfolioMonitorResponse}
              onCheck={() => void handlePortfolioMonitor()}
            />
          </div>
          <div className="space-y-6">
            <SavedWorkspacesPanel copy={ws} savedPortfolios={savedPortfolios} />
            <PortfolioScenarioPanel
              copy={ws}
              loading={loading}
              normalizedHoldingsCount={normalizedHoldings.length}
              scenarioForm={scenarioForm}
              onScenarioFormChange={setScenarioForm}
              onRunScenario={handleScenario}
              scenario={scenario}
              comparisonScenarios={comparisonScenarios}
              comparisonValidation={comparisonValidation}
              compareJson={compareJson}
              onCompareJsonChange={setCompareJson}
              onAddComparisonScenario={addComparisonScenario}
              onRemoveComparisonScenario={removeComparisonScenario}
              onUpdateComparisonScenario={updateComparisonScenario}
              onRunScenarioComparison={handleCompareScenarios}
              comparison={comparison}
              scenarioKindOptions={scenarioKindOptions}
              scenarioKindLabel={scenarioKindLabel}
              scenarioKindHelper={scenarioKindHelper}
              stressTestForm={stressTestForm}
              stressTestError={stressTestError}
              stressTestResult={stressTestResult}
              onStressTestFormChange={handleStressTestFormChange}
              onRunStressTest={handleRunStressTest}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
