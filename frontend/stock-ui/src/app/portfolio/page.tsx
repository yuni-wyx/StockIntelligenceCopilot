"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLanguage } from "@/context/LanguageContext";
import {
  analyzePortfolio,
  askPortfolioAgent,
  comparePortfolioScenarios,
  listSavedPortfolios,
  loadCurrentPortfolio,
  runPortfolioScenario,
  savePortfolio,
  type HoldingInput,
  type PortfolioAgentResponse,
  type PortfolioAnalysisResponse,
  type ScenarioComparisonResponse,
  type ScenarioResponse,
} from "@/lib/portfolioApi";
import { appendHolding } from "@/lib/portfolioState";
import { normalizeTicker, tickerDisplayName } from "@/lib/tickerMap";

type ScenarioForm = {
  sellTicker: string;
  sellShares: string;
  sellPercentage: string;
  buyTicker: string;
  buyAmount: string;
  buyName: string;
  question: string;
};

type ComparisonScenarioKind =
  | "sell_percentage"
  | "buy_amount"
  | "reduce_concentration"
  | "add_position";

type ComparisonScenarioDraft = {
  id: string;
  name: string;
  kind: ComparisonScenarioKind;
  ticker: string;
  percentage: string;
  amount: string;
  question: string;
};

type ComparisonPayloadScenario = {
  name: string;
  actions: Array<{
    action: "sell" | "buy" | "hold_cash";
    ticker: string;
    shares?: number;
    percentage?: number;
    amount?: number;
  }>;
  user_question?: string;
};

type HoldingValidationField =
  | "ticker"
  | "shares"
  | "avg_cost"
  | "current_price"
  | "current_value";

type NumericHoldingField = "avg_cost" | "current_price" | "current_value" | "shares";

type EditableHolding = Omit<HoldingInput, NumericHoldingField> & {
  _rowId: string;
  avg_cost?: string;
  current_price?: string;
  current_value?: string;
  shares?: string;
};

type HoldingDerivedMetrics = {
  costBasis?: number;
  currentValue?: number;
  unrealizedGainLoss?: number;
  returnPct?: number;
};

type HoldingValidationMessage = {
  rowIndex: number;
  field: HoldingValidationField;
  message: string;
};

type WealthStudioOperation =
  | "analyze"
  | "save"
  | "load"
  | "scenario"
  | "compare"
  | "coach";

const DEFAULT_COMPARE_JSON = JSON.stringify(
  [
    {
      name: "Reduce income ETF, add tech fund",
      actions: [
        { action: "sell", ticker: "00878", percentage: 50 },
        { action: "buy", ticker: "2330", amount: 35000 },
      ],
      user_question: "Does this improve growth without pushing concentration too far?",
    },
  ],
  null,
  2,
);

const inputClassName =
  "min-h-11 w-full min-w-0 rounded-xl border border-white/10 bg-black/45 px-3 py-2 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50";

const invalidInputClassName =
  "min-h-11 w-full min-w-0 rounded-xl border border-amber-300/60 bg-amber-300/10 px-3 py-2 text-sm text-white outline-none transition placeholder:text-amber-100/40 focus:border-amber-200";

const textareaClassName =
  "min-h-36 w-full min-w-0 resize-y rounded-xl border border-white/10 bg-black/45 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50";

const secondaryLinkClassName =
  "rounded-xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-zinc-200 transition hover:border-white/20";

const scenarioKindOptions: Array<{
  value: ComparisonScenarioKind;
}> = [
  { value: "sell_percentage" },
  { value: "buy_amount" },
  { value: "reduce_concentration" },
  { value: "add_position" },
];

function createRowId() {
  return `holding-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function numericInputValue(value: number | string | null | undefined): string | undefined {
  if (value === null || value === undefined) return undefined;
  return String(value);
}

function toEditableHolding(holding: HoldingInput, rowId = createRowId()): EditableHolding {
  return {
    ...holding,
    _rowId: rowId,
    avg_cost: numericInputValue(holding.avg_cost),
    current_price: numericInputValue(holding.current_price),
    current_value: numericInputValue(holding.current_value),
    shares: numericInputValue(holding.shares),
  };
}

function parseOptionalNumber(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === "") {
    return undefined;
  }
  return Number(value);
}

function payloadNumber(value: string | undefined): number | undefined {
  const parsed = parseOptionalNumber(value);
  return parsed === undefined || Number.isNaN(parsed) ? undefined : parsed;
}

function toApiHolding(holding: EditableHolding): HoldingInput {
  return {
    ticker: holding.ticker,
    name: holding.name || undefined,
    avg_cost: payloadNumber(holding.avg_cost),
    current_price: payloadNumber(holding.current_price),
    current_value: payloadNumber(holding.current_value),
    shares: payloadNumber(holding.shares),
    asset_type: holding.asset_type || undefined,
    category: holding.category || undefined,
    notes: holding.notes || undefined,
  };
}

function scenarioKindLabel(
  kind: ComparisonScenarioKind,
  copy: {
    sellPercentageScenario: string;
    buyAmountScenario: string;
    reduceConcentrationScenario: string;
    addPositionScenario: string;
  },
) {
  return {
    sell_percentage: copy.sellPercentageScenario,
    buy_amount: copy.buyAmountScenario,
    reduce_concentration: copy.reduceConcentrationScenario,
    add_position: copy.addPositionScenario,
  }[kind];
}

function scenarioKindHelper(
  kind: ComparisonScenarioKind,
  copy: {
    sellPercentageScenarioHelper: string;
    buyAmountScenarioHelper: string;
    reduceConcentrationScenarioHelper: string;
    addPositionScenarioHelper: string;
  },
) {
  return {
    sell_percentage: copy.sellPercentageScenarioHelper,
    buy_amount: copy.buyAmountScenarioHelper,
    reduce_concentration: copy.reduceConcentrationScenarioHelper,
    add_position: copy.addPositionScenarioHelper,
  }[kind];
}

function calculateEditableHoldingMetrics(holding: EditableHolding): HoldingDerivedMetrics {
  const shares = parseOptionalNumber(holding.shares);
  const avgCost = parseOptionalNumber(holding.avg_cost);
  const currentPrice = parseOptionalNumber(holding.current_price);
  const manualCurrentValue = parseOptionalNumber(holding.current_value);
  const costBasis =
    shares !== undefined && avgCost !== undefined && !Number.isNaN(shares) && !Number.isNaN(avgCost)
      ? shares * avgCost
      : undefined;
  const calculatedCurrentValue =
    shares !== undefined &&
    currentPrice !== undefined &&
    !Number.isNaN(shares) &&
    !Number.isNaN(currentPrice)
      ? shares * currentPrice
      : undefined;
  const currentValue =
    manualCurrentValue !== undefined && !Number.isNaN(manualCurrentValue)
      ? manualCurrentValue
      : calculatedCurrentValue;
  const unrealizedGainLoss =
    currentValue !== undefined && costBasis !== undefined ? currentValue - costBasis : undefined;
  const returnPct =
    unrealizedGainLoss !== undefined && costBasis !== undefined && costBasis > 0
      ? (unrealizedGainLoss / costBasis) * 100
      : undefined;

  return {
    costBasis,
    currentValue,
    unrealizedGainLoss,
    returnPct,
  };
}

export default function PortfolioPage() {
  const { t } = useLanguage();
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
  const [agentResponse, setAgentResponse] = useState<PortfolioAgentResponse | null>(null);
  const [savedPortfolios, setSavedPortfolios] = useState<Array<Record<string, unknown>>>([]);
  const [compareJson, setCompareJson] = useState(DEFAULT_COMPARE_JSON);
  const [comparison, setComparison] = useState<ScenarioComparisonResponse | null>(null);
  const [comparisonScenarios, setComparisonScenarios] = useState<ComparisonScenarioDraft[]>([]);
  const [comparisonValidation, setComparisonValidation] = useState<string[]>([]);
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
    "Should I sell part of 00878 and buy Allianz Taiwan Technology Fund?",
  );

  const normalizedHoldings = useMemo(
    () =>
      holdings
        .filter((holding) => holding.ticker?.trim())
        .map((holding) => ({
          ...toApiHolding(holding),
          ticker: normalizeTicker(holding.ticker),
        })),
    [holdings],
  );

  const holdingsValidation = useMemo(() => {
    const messages: HoldingValidationMessage[] = [];
    const fieldKeys = new Set<string>();

    holdings.forEach((holding, index) => {
      const rowLabel = holding.ticker?.trim()
        ? normalizeTicker(holding.ticker)
        : `Holding ${index + 1}`;

      if (!holding.ticker?.trim()) {
        messages.push({
          rowIndex: index,
          field: "ticker",
          message: `${rowLabel}: ${ws.tickerRequired}`,
        });
        fieldKeys.add(`${index}:ticker`);
      }

      const shares = parseOptionalNumber(holding.shares);
      const avgCost = parseOptionalNumber(holding.avg_cost);
      const currentPrice = parseOptionalNumber(holding.current_price);
      const currentValue = parseOptionalNumber(holding.current_value);

      if (shares === undefined || Number.isNaN(shares)) {
        messages.push({
          rowIndex: index,
          field: "shares",
          message: `${rowLabel}: ${ws.sharesRequired}`,
        });
        fieldKeys.add(`${index}:shares`);
      } else if (shares <= 0) {
        messages.push({
          rowIndex: index,
          field: "shares",
          message: `${rowLabel}: ${ws.sharesPositive}`,
        });
        fieldKeys.add(`${index}:shares`);
      }

      if (avgCost !== undefined) {
        if (Number.isNaN(avgCost) || avgCost < 0) {
          messages.push({
            rowIndex: index,
            field: "avg_cost",
            message: `${rowLabel}: ${ws.avgCostNonNegative}`,
          });
          fieldKeys.add(`${index}:avg_cost`);
        }
      }

      if (currentPrice !== undefined) {
        if (Number.isNaN(currentPrice) || currentPrice < 0) {
          messages.push({
            rowIndex: index,
            field: "current_price",
            message: `${rowLabel}: ${ws.currentPriceNonNegative}`,
          });
          fieldKeys.add(`${index}:current_price`);
        }
      }

      if (currentValue !== undefined) {
        if (Number.isNaN(currentValue) || currentValue < 0) {
          messages.push({
            rowIndex: index,
            field: "current_value",
            message: `${rowLabel}: ${ws.currentValueNonNegative}`,
          });
          fieldKeys.add(`${index}:current_value`);
        }
      }
    });

    if (holdings.length === 0) {
      messages.push({
        rowIndex: -1,
        field: "ticker",
        message: ws.noHoldingsBody,
      });
    }

    return {
      messages,
      fieldKeys,
      hasErrors: messages.length > 0,
    };
  }, [holdings, ws]);

  function currentPortfolioPayload() {
    return {
      holdings: normalizedHoldings,
      risk_profile: riskProfile,
      goal,
      base_currency: "TWD",
    };
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
    setComparisonScenarios((prev) => [
      ...prev,
      {
        id: `scenario-${Date.now()}-${prev.length}`,
        name: `Scenario ${prev.length + 1}`,
        kind: "sell_percentage",
        ticker: "",
        percentage: "50",
        amount: "",
        question: "How does this change portfolio risk and concentration?",
      },
    ]);
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
    const errors: string[] = [];
    const scenarios = comparisonScenarios.map((scenarioItem, index) => {
      const scenarioNumber = index + 1;
      const ticker = normalizeTicker(scenarioItem.ticker);
      const name = scenarioItem.name.trim() || `Scenario ${scenarioNumber}`;
      const question = scenarioItem.question.trim();
      const percentage = Number(scenarioItem.percentage);
      const amount = Number(scenarioItem.amount);
      const actionLabel = scenarioKindLabel(scenarioItem.kind, ws);

      if (!ticker) {
        errors.push(`${name}: ${ws.scenarioTickerRequired}`);
      }

      if (
        scenarioItem.kind === "sell_percentage" ||
        scenarioItem.kind === "reduce_concentration"
      ) {
        if (!scenarioItem.percentage.trim() || Number.isNaN(percentage)) {
          errors.push(`${name}: ${ws.scenarioPercentageRequired}`);
        } else if (percentage <= 0 || percentage > 100) {
          errors.push(`${name}: ${ws.scenarioPercentageRange}`);
        }

        return {
          name,
          actions: [
            {
              action: "sell" as const,
              ticker,
              percentage,
            },
          ],
          user_question:
            question ||
            `${actionLabel}: what changes in concentration, income, and downside risk?`,
        };
      }

      if (!scenarioItem.amount.trim() || Number.isNaN(amount)) {
        errors.push(`${name}: ${ws.scenarioAmountRequired}`);
      } else if (amount <= 0) {
        errors.push(`${name}: ${ws.scenarioAmountPositive}`);
      }

      return {
        name,
        actions: [
          {
            action: "buy" as const,
            ticker,
            amount,
          },
        ],
        user_question:
          question ||
          `${actionLabel}: does this improve growth without creating new concentration risk?`,
      };
    });

    return { scenarios, errors };
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
    setAgentResponse(null);
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
      const actions = [];
      if (scenarioForm.sellTicker.trim()) {
        actions.push({
          action: "sell" as const,
          ticker: normalizeTicker(scenarioForm.sellTicker),
          shares: scenarioForm.sellShares ? Number(scenarioForm.sellShares) : undefined,
          percentage: scenarioForm.sellPercentage
            ? Number(scenarioForm.sellPercentage)
            : undefined,
        });
      }
      if (scenarioForm.buyTicker.trim()) {
        actions.push({
          action: "buy" as const,
          ticker: normalizeTicker(scenarioForm.buyTicker),
          amount: scenarioForm.buyAmount ? Number(scenarioForm.buyAmount) : undefined,
        });
      }
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
        scenarios: parsed.map((scenarioItem) => ({
          ...scenarioItem,
          actions: scenarioItem.actions.map((action) => ({
            ...action,
            ticker: normalizeTicker(action.ticker),
          })),
        })),
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

  async function handleAskAgent() {
    setLoading(true);
    setActiveOperation("coach");
    setError(null);
    try {
      const response = await askPortfolioAgent({
        portfolio: currentPortfolioPayload(),
        user_question: agentQuestion,
      });
      setAgentResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedCoach);
    } finally {
      setLoading(false);
      setActiveOperation(null);
    }
  }

  return (
    <div className="min-h-screen bg-[#0d0c0a] px-4 py-6 text-white sm:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-zinc-900/60 p-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-amber-200/70">
              {ws.eyebrow}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              {ws.title}
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-300">
              {ws.subtitle}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LanguageToggle />
            <Link href="/" className={secondaryLinkClassName}>
              {ws.home}
            </Link>
            <Link href="/copilot?mode=research" className={secondaryLinkClassName}>
              {ws.researchMode}
            </Link>
          </div>
        </header>

        <section className="rounded-2xl border border-white/10 bg-zinc-900/50 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold">{ws.firstRunTitle}</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">{ws.firstRunHelper}</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {ws.firstRunSteps.map((step, index) => (
                <div key={step} className="rounded-xl border border-white/10 bg-black/25 p-3">
                  <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
                    {ws.firstRunStepLabel} {index + 1}
                  </div>
                  <div className="mt-1 text-sm font-medium text-zinc-100">{step}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_380px]">
          <main className="min-w-0 space-y-6">
            <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{ws.yourHoldings}</h2>
                  <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
                    {ws.holdingsHelper}
                  </p>
                </div>
                <button
                  onClick={addHolding}
                  className="w-full rounded-xl bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-amber-100 sm:w-auto"
                >
                  {ws.addHolding}
                </button>
              </div>

              {holdingsValidation.hasErrors ? (
                <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
                  <h3 className="text-sm font-semibold text-amber-100">
                    {ws.holdingValidationTitle}
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-amber-100/75">
                    {ws.holdingValidationHelper}
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

              <div className="mt-5 space-y-3">
                {holdings.length === 0 ? (
                  <EmptyState
                    title={ws.noHoldingsTitle}
                    body={ws.noHoldingsBody}
                  />
                ) : null}

                {holdings.map((holding, index) => {
                  const canonicalTicker = normalizeTicker(holding.ticker);
                  const displayName = tickerDisplayName(holding.ticker);
                  const knownDisplayName =
                    holding.ticker.trim() && displayName !== canonicalTicker ? displayName : "";
                  const derivedMetrics = calculateEditableHoldingMetrics(holding);

                  return (
                  <div
                    key={holding._rowId}
                    className="rounded-2xl border border-white/10 bg-black/25 p-4"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:grid-cols-[0.9fr_1.4fr_0.9fr_0.9fr]">
                        <Field label={ws.ticker}>
                          <input
                            value={holding.ticker}
                            onChange={(e) => updateHolding(index, "ticker", e.target.value)}
                            placeholder="00878 or NVDA"
                            className={holdingInputClass(index, "ticker")}
                          />
                          {knownDisplayName ? (
                            <span className="mt-1.5 block text-xs leading-5 text-amber-100/70">
                              {canonicalTicker} → {knownDisplayName}
                            </span>
                          ) : null}
                        </Field>
                        <Field label={ws.name}>
                          <input
                            value={holding.name ?? ""}
                            onChange={(e) => updateHolding(index, "name", e.target.value)}
                            className={inputClassName}
                          />
                        </Field>
                        <Field label={ws.shares}>
                          <input
                            value={holding.shares ?? ""}
                            onChange={(e) => updateHolding(index, "shares", e.target.value)}
                            inputMode="decimal"
                            placeholder="2239"
                            className={holdingInputClass(index, "shares")}
                          />
                        </Field>
                        <Field label={ws.currentPrice}>
                          <input
                            value={holding.current_price ?? ""}
                            onChange={(e) => updateHolding(index, "current_price", e.target.value)}
                            inputMode="decimal"
                            placeholder="0 or higher"
                            className={holdingInputClass(index, "current_price")}
                          />
                        </Field>
                      </div>
                      <button
                        onClick={() => removeHolding(index)}
                        className="rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 transition hover:border-rose-300/50 hover:text-rose-200"
                      >
                        {ws.remove}
                      </button>
                    </div>

                    <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                      <Field label={ws.avgCost}>
                        <input
                          value={holding.avg_cost ?? ""}
                          onChange={(e) => updateHolding(index, "avg_cost", e.target.value)}
                          inputMode="decimal"
                          placeholder="0 or higher"
                          className={holdingInputClass(index, "avg_cost")}
                        />
                      </Field>
                      <Field label={ws.currentValue}>
                        <input
                          value={holding.current_value ?? ""}
                          onChange={(e) => updateHolding(index, "current_value", e.target.value)}
                          inputMode="decimal"
                          placeholder={derivedMetrics.currentValue !== undefined ? formatNumber(derivedMetrics.currentValue) : ""}
                          className={holdingInputClass(index, "current_value")}
                        />
                      </Field>
                      <Field label={ws.assetType} helper={ws.assetTypeHelper}>
                        <input
                          value={holding.asset_type ?? ""}
                          onChange={(e) => updateHolding(index, "asset_type", e.target.value)}
                          placeholder="ETF, stock, fund..."
                          className={inputClassName}
                        />
                      </Field>
                      <Field label={ws.category} helper={ws.categoryHelper}>
                        <input
                          value={holding.category ?? ""}
                          onChange={(e) => updateHolding(index, "category", e.target.value)}
                          placeholder="High Dividend, Tech..."
                          className={inputClassName}
                        />
                      </Field>
                      <Field label={ws.notes}>
                        <input
                          value={holding.notes ?? ""}
                          onChange={(e) => updateHolding(index, "notes", e.target.value)}
                          className={inputClassName}
                        />
                      </Field>
                    </div>
                    <div className="mt-4 grid gap-3 rounded-xl border border-white/10 bg-black/20 p-3 sm:grid-cols-2 xl:grid-cols-4">
                      <MiniMetric label={ws.costBasis} value={derivedMetrics.costBasis} />
                      <MiniMetric label={ws.holdingValue} value={derivedMetrics.currentValue} />
                      <MiniMetric label={ws.unrealizedPL} value={derivedMetrics.unrealizedGainLoss} />
                      <MiniMetric label={ws.returnPct} value={derivedMetrics.returnPct} suffix="%" />
                    </div>
                  </div>
                  );
                })}
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-[0.45fr_1fr]">
                <Field label={ws.riskProfile}>
                  <input
                    value={riskProfile}
                    onChange={(e) => setRiskProfile(e.target.value)}
                    placeholder="Balanced"
                    className={inputClassName}
                  />
                </Field>
                <Field label={ws.goal}>
                  <input
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    placeholder="Preserve income while improving diversification"
                    className={inputClassName}
                  />
                </Field>
              </div>

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <button
                  onClick={handleAnalyze}
                  disabled={loading || holdingsValidation.hasErrors}
                  className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                >
                  {loading ? ws.working : ws.analyzeHoldings}
                </button>
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  {ws.saveWorkspace}
                </button>
                <button
                  onClick={handleLoad}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  {ws.loadSaved}
                </button>
              </div>
            </section>

            {error ? (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {error}
              </div>
            ) : null}

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">{ws.savedWorkspaces}</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                {ws.savedWorkspacesHelper}
              </p>
              {savedPortfolios.length > 0 ? (
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {savedPortfolios.map((portfolio) => (
                    <div
                      key={String(portfolio.name)}
                      className="rounded-2xl border border-white/10 bg-black/30 p-4 text-sm"
                    >
                      <div className="break-words font-medium">{String(portfolio.name)}</div>
                      <div className="mt-2 text-zinc-400">
                        {ws.holdingsCount}: {String(portfolio.holding_count ?? 0)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title={ws.noSavedTitle}
                  body={ws.noSavedBody}
                />
              )}
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{ws.portfolioInsights}</h2>
                  <p className="mt-1 text-sm leading-6 text-zinc-400">
                    {ws.insightsHelper}
                  </p>
                </div>
                {analysis ? (
                  <Badge tone={scoreTone(analysis.overall_score)}>
                    {scoreLabel(analysis.overall_score, ws)}
                  </Badge>
                ) : null}
              </div>

              {activeOperation === "analyze" ? (
                <div className="mt-4 rounded-2xl border border-sky-300/25 bg-sky-300/10 p-5">
                  <h3 className="font-medium text-sky-100">{ws.analyzingTitle}</h3>
                  <p className="mt-2 text-sm leading-6 text-sky-100/75">
                    {ws.analyzingBody}
                  </p>
                </div>
              ) : insightsError ? (
                <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-300/10 p-5">
                  <h3 className="font-medium text-rose-100">{ws.insightsErrorTitle}</h3>
                  <p className="mt-2 break-words text-sm leading-6 text-rose-100/80">
                    {insightsError}
                  </p>
                </div>
              ) : !analysis ? (
                <EmptyState
                  title={ws.noAnalysisTitle}
                  body={ws.noAnalysisBody}
                />
              ) : (
                <div className="mt-5 space-y-6">
                  <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
                    <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">{ws.overallHealth}</h3>
                          <p className="mt-1 text-sm leading-6 text-zinc-400">
                            {ws.overallHealthHelper}
                          </p>
                        </div>
                        <div className="text-left sm:text-right">
                          <div className="text-4xl font-semibold tabular-nums">
                            {formatNumber(analysis.overall_score)}
                          </div>
                          <Badge tone={scoreTone(analysis.overall_score)}>
                            {scoreLabel(analysis.overall_score, ws)}
                          </Badge>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-3 sm:grid-cols-2">
                        <ScoreRow label={ws.diversification} value={analysis.diversification_score} />
                        <ScoreRow label={ws.concentration} value={analysis.concentration_score} />
                        <ScoreRow label={ws.income} value={analysis.income_score} />
                        <ScoreRow label={ws.defensive} value={analysis.defensive_score} />
                        <ScoreRow label={ws.growth} value={analysis.growth_score} />
                      </div>

                      <p className="mt-5 text-sm leading-6 text-zinc-300">
                        {analysis.summary}
                      </p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <InsightStat
                        label={ws.totalValue}
                        value={analysis.total_current_value}
                        helper={ws.totalValueHelper}
                      />
                      <InsightStat
                        label={ws.unrealizedPL}
                        value={analysis.total_unrealized_gain_loss}
                        helper={`${formatNumber(analysis.total_return_pct)}% ${ws.totalReturn}`}
                      />
                      <InsightStat
                        label={ws.annualDividend}
                        value={analysis.estimated_annual_dividend}
                        helper={ws.annualDividendHelper}
                      />
                      <InsightStat
                        label={ws.monthlyDividend}
                        value={analysis.estimated_monthly_dividend}
                        helper={ws.monthlyDividendHelper}
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                    <div className="space-y-4">
                      <InsightPanel
                        title={ws.keyRisks}
                        helper={ws.keyRisksHelper}
                        badge={
                          <Badge tone={analysis.risk_flags.length > 0 ? "warning" : "good"}>
                            {analysis.risk_flags.length > 0 ? ws.review : ws.clear}
                          </Badge>
                        }
                      >
                        <ListContent
                          items={analysis.risk_flags}
                          emptyLabel={ws.noRiskFlags}
                        />
                      </InsightPanel>

                      <InsightPanel
                        title={ws.recommendedNextSteps}
                        helper={ws.nextStepsHelper}
                        badge={<Badge tone="neutral">{analysis.suggestions.length}</Badge>}
                      >
                        <ListContent
                          items={analysis.suggestions}
                          emptyLabel={ws.noSuggestions}
                        />
                        {agentResponse ? (
                          <div className="mt-4 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                            <div>
                              <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
                                {ws.aiCoach}
                              </div>
                              <p className="mt-2 text-sm leading-6 text-zinc-200">
                                {agentResponse.conclusion}
                              </p>
                              <p className="mt-2 text-sm leading-6 text-zinc-400">
                                {agentResponse.current_portfolio_diagnosis}
                              </p>
                            </div>
                            <div className="grid gap-4 xl:grid-cols-2">
                              <ListCard
                                title={ws.coachActions}
                                items={agentResponse.suggested_next_actions}
                                emptyLabel={ws.noCoachActions}
                              />
                              <ListCard
                                title={ws.coachRisks}
                                items={agentResponse.risks}
                                emptyLabel={ws.noCoachRisks}
                              />
                            </div>
                            <div className="grid gap-4 xl:grid-cols-3">
                              <InfoPanel title={ws.bullCase} body={agentResponse.bull_case} />
                              <InfoPanel title={ws.bearCase} body={agentResponse.bear_case} />
                              <InfoPanel title={ws.baseCase} body={agentResponse.base_case} />
                            </div>
                          </div>
                        ) : null}
                      </InsightPanel>
                    </div>

                    <div className="space-y-4">
                      <InsightPanel
                        title={ws.allocationExposure}
                        helper={ws.allocationExposureHelper}
                        badge={<Badge tone="neutral">{ws.exposure}</Badge>}
                      >
                        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                          <ExposureCard title={ws.assetTypeExposure} items={analysis.asset_type_exposure} copy={ws} />
                          <ExposureCard title={ws.categoryExposure} items={analysis.category_exposure} copy={ws} />
                          <ExposureCard title={ws.sectorExposure} items={analysis.sector_exposure} copy={ws} />
                          <ExposureCard title={ws.themeExposure} items={analysis.theme_exposure} copy={ws} />
                          <ExposureCard title={ws.marketExposure} items={analysis.market_exposure} copy={ws} />
                        </div>
                      </InsightPanel>

                      <InsightPanel
                        title={ws.incomeDataQuality}
                        helper={ws.incomeDataQualityHelper}
                        badge={<Badge tone={analysis.missing_data.length > 0 ? "warning" : "good"}>
                          {analysis.missing_data.length > 0 ? ws.checkData : ws.dataOk}
                        </Badge>}
                      >
                        <div className="grid gap-3 sm:grid-cols-2">
                          <InsightStat
                            label={ws.incomeScore}
                            value={analysis.income_score}
                            helper={ws.incomeScoreHelper}
                          />
                          <InsightStat
                            label={ws.totalCost}
                            value={analysis.total_cost_basis}
                            helper={ws.totalCostHelper}
                          />
                        </div>
                        <div className="mt-4">
                          <ListContent
                            items={analysis.missing_data}
                            emptyLabel={ws.noMissingData}
                          />
                        </div>
                      </InsightPanel>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="font-semibold">{ws.newsToMonitor}</h3>
                        <p className="mt-1 text-sm leading-6 text-zinc-400">
                          {ws.newsHelper}
                        </p>
                      </div>
                      <Badge tone={Object.keys(analysis.news_to_monitor).length > 0 ? "neutral" : "good"}>
                        {Object.keys(analysis.news_to_monitor).length} {ws.tickerCount}
                        {Object.keys(analysis.news_to_monitor).length === 1 ? "" : "s"}
                      </Badge>
                    </div>
                    <div className="mt-4 space-y-4">
                      {Object.keys(analysis.news_to_monitor).length === 0 ? (
                        <p className="text-sm text-zinc-400">
                          {ws.noNews}
                        </p>
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

                  <details className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
                      {ws.holdingDetails}
                    </summary>
                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      {ws.holdingDetailsHelper}
                    </p>
                    <div className="mt-4 overflow-x-auto">
                      <table className="min-w-[620px] text-left text-sm">
                        <thead className="text-zinc-400">
                          <tr>
                            {[ws.ticker, ws.weightPct, "P/L", ws.returnPct, ws.annualDiv, ws.theme].map(
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
                              <td className="px-2 py-2">
                                {formatNumber(holding.portfolio_weight_pct)}%
                              </td>
                              <td className="px-2 py-2">
                                {formatNumber(holding.unrealized_gain_loss)}
                              </td>
                              <td className="px-2 py-2">{formatNumber(holding.return_pct)}%</td>
                              <td className="px-2 py-2">
                                {formatNumber(holding.estimated_annual_dividend)}
                              </td>
                              <td className="px-2 py-2">{holding.theme ?? "N/A"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">{ws.scenarioComparison}</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                {ws.scenarioComparisonHelper}
              </p>

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-zinc-400">
                  {comparisonScenarios.length > 0
                    ? `${comparisonScenarios.length} ${
                        comparisonScenarios.length === 1
                          ? ws.structuredScenarioReady
                          : ws.structuredScenariosReady
                      }`
                    : ws.noStructuredScenarios}
                </div>
                <button
                  onClick={addComparisonScenario}
                  className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-100"
                >
                  {ws.addScenario}
                </button>
              </div>

              {comparisonScenarios.length === 0 ? (
                <EmptyState
                  title={ws.noComparisonTitle}
                  body={ws.noComparisonBody}
                />
              ) : (
                <div className="mt-4 space-y-4">
                  {comparisonScenarios.map((scenarioItem, index) => {
                    const needsPercentage =
                      scenarioItem.kind === "sell_percentage" ||
                      scenarioItem.kind === "reduce_concentration";

                    return (
                      <div
                        key={scenarioItem.id}
                        className="rounded-2xl border border-white/10 bg-black/25 p-4"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200/60">
                              {ws.scenario} {index + 1}
                            </div>
                            <h3 className="mt-1 font-semibold">
                              {scenarioItem.name.trim() || `Scenario ${index + 1}`}
                            </h3>
                            <p className="mt-1 text-sm leading-6 text-zinc-400">
                              {scenarioKindHelper(scenarioItem.kind, ws)}
                            </p>
                          </div>
                          <button
                            onClick={() => removeComparisonScenario(scenarioItem.id)}
                            className="rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 transition hover:border-rose-300/50 hover:text-rose-200"
                          >
                            Remove
                          </button>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1.2fr]">
                          <Field label={ws.scenarioName}>
                            <input
                              value={scenarioItem.name}
                              onChange={(e) =>
                                updateComparisonScenario(
                                  scenarioItem.id,
                                  "name",
                                  e.target.value,
                                )
                              }
                              placeholder={`Scenario ${index + 1}`}
                              className={inputClassName}
                            />
                          </Field>
                          <Field label={ws.scenarioType}>
                            <select
                              value={scenarioItem.kind}
                              onChange={(e) =>
                                updateComparisonScenario(
                                  scenarioItem.id,
                                  "kind",
                                  e.target.value,
                                )
                              }
                              className={inputClassName}
                            >
                              {scenarioKindOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {scenarioKindLabel(option.value, ws)}
                                </option>
                              ))}
                            </select>
                          </Field>
                        </div>

                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                          <Field label={ws.ticker}>
                            <input
                              value={scenarioItem.ticker}
                              onChange={(e) =>
                                updateComparisonScenario(
                                  scenarioItem.id,
                                  "ticker",
                                  e.target.value,
                                )
                              }
                              placeholder={needsPercentage ? "00878" : "2330"}
                              className={inputClassName}
                            />
                          </Field>
                          {needsPercentage ? (
                            <Field label={ws.sellPercentage}>
                              <input
                                value={scenarioItem.percentage}
                                onChange={(e) =>
                                  updateComparisonScenario(
                                    scenarioItem.id,
                                    "percentage",
                                    e.target.value,
                                  )
                                }
                                inputMode="decimal"
                                placeholder="50"
                                className={inputClassName}
                              />
                            </Field>
                          ) : (
                            <Field label={ws.buyAmount}>
                              <input
                                value={scenarioItem.amount}
                                onChange={(e) =>
                                  updateComparisonScenario(
                                    scenarioItem.id,
                                    "amount",
                                    e.target.value,
                                  )
                                }
                                inputMode="decimal"
                                placeholder="35000"
                                className={inputClassName}
                              />
                            </Field>
                          )}
                          <Field label={ws.question}>
                            <input
                              value={scenarioItem.question}
                              onChange={(e) =>
                                updateComparisonScenario(
                                  scenarioItem.id,
                                  "question",
                                  e.target.value,
                                )
                              }
                              placeholder="What tradeoff should we evaluate?"
                              className={inputClassName}
                            />
                          </Field>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {comparisonValidation.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
                  <h3 className="text-sm font-semibold text-amber-100">
                    {ws.validationScenarioTitle}
                  </h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-100/85">
                    {comparisonValidation.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
                <button
                  onClick={handleCompareScenarios}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                >
                  {ws.runScenarioComparison}
                </button>
                {comparisonScenarios.length === 0 ? (
                  <span className="text-sm text-zinc-500">
                    {ws.advancedJsonHint}
                  </span>
                ) : (
                  <span className="text-sm text-zinc-500">
                    {ws.structuredPayloadHint}
                  </span>
                )}
              </div>

              <details className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
                  {ws.advancedJsonEditor}
                </summary>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  {ws.advancedJsonHelper}
                </p>
                <textarea
                  value={compareJson}
                  onChange={(e) => setCompareJson(e.target.value)}
                  rows={10}
                  className="mt-4 min-h-64 w-full resize-y rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-sm leading-6 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50"
                />
              </details>

              {comparison ? (
                <div className="mt-6 overflow-x-auto">
                  <table className="min-w-[680px] text-left text-sm">
                    <thead className="text-zinc-400">
                      <tr>
                        {[
                          ws.scenario,
                          ws.rank,
                          ws.scoreDelta,
                          ws.dividendDelta,
                          ws.techDelta,
                          ws.defensiveDelta,
                          ws.concentrationDelta,
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
                          <td className="px-2 py-2">
                            {formatNumber(item.technology_exposure_change)}%
                          </td>
                          <td className="px-2 py-2">
                            {formatNumber(item.defensive_allocation_change)}%
                          </td>
                          <td className="px-2 py-2">
                            {formatNumber(item.concentration_change)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </section>
          </main>

          <aside className="min-w-0 space-y-6 lg:sticky lg:top-6 lg:self-start">
            <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
              <h2 className="text-xl font-semibold">{ws.aiPortfolioCoach}</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                {ws.coachHelper}
              </p>
              <Field label={ws.question} className="mt-4">
                <textarea
                  value={agentQuestion}
                  onChange={(e) => setAgentQuestion(e.target.value)}
                  rows={6}
                  placeholder="Should I sell part of 00878 and buy Allianz Taiwan Technology Fund?"
                  className={textareaClassName}
                />
              </Field>
              <button
                onClick={handleAskAgent}
                disabled={loading}
                className="mt-4 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
              >
                {ws.askCoach}
              </button>
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
              <h2 className="text-xl font-semibold">{ws.scenarioSimulator}</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                {ws.scenarioSimulatorHelper}
              </p>
              <div className="mt-4 space-y-4">
                <Field label={ws.sellTicker}>
                  <input
                    value={scenarioForm.sellTicker}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, sellTicker: e.target.value }))
                    }
                    placeholder="00878"
                    className={inputClassName}
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                  <Field label={ws.sellShares}>
                    <input
                      value={scenarioForm.sellShares}
                      onChange={(e) =>
                        setScenarioForm((prev) => ({ ...prev, sellShares: e.target.value }))
                      }
                      inputMode="decimal"
                      placeholder="Optional"
                      className={inputClassName}
                    />
                  </Field>
                  <Field label={ws.sellPercent}>
                    <input
                      value={scenarioForm.sellPercentage}
                      onChange={(e) =>
                        setScenarioForm((prev) => ({
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
                <Field label={ws.buyTicker}>
                  <input
                    value={scenarioForm.buyTicker}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyTicker: e.target.value }))
                    }
                    placeholder="2330"
                    className={inputClassName}
                  />
                </Field>
                <Field label={ws.buyAmount}>
                  <input
                    value={scenarioForm.buyAmount}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyAmount: e.target.value }))
                    }
                    inputMode="decimal"
                    placeholder="35000"
                    className={inputClassName}
                  />
                </Field>
                <Field label={ws.buyName}>
                  <input
                    value={scenarioForm.buyName}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyName: e.target.value }))
                    }
                    placeholder="Optional fund or company name"
                    className={inputClassName}
                  />
                </Field>
                <Field label={ws.scenarioQuestion}>
                  <textarea
                    value={scenarioForm.question}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, question: e.target.value }))
                    }
                    rows={5}
                    placeholder="What do you want to know?"
                    className={textareaClassName}
                  />
                </Field>
                <button
                  onClick={handleScenario}
                  disabled={loading || normalizedHoldings.length === 0}
                  className="w-full rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                >
                  {ws.runScenario}
                </button>
              </div>
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">{ws.scenarioResult}</h2>
              {!scenario ? (
                <EmptyState
                  title={ws.noScenarioTitle}
                  body={ws.noScenarioBody}
                />
              ) : (
                <div className="mt-4 space-y-4">
                  <p className="text-sm leading-6 text-zinc-300">{scenario.recommendation}</p>
                  <div className="grid gap-3">
                    <MetricCard label={ws.beforeValue} value={scenario.before.total_current_value} />
                    <MetricCard label={ws.afterValue} value={scenario.after.total_current_value} />
                    <MetricCard label={ws.dividendChange} value={scenario.dividend_change} />
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <h3 className="font-semibold">{ws.riskTradeoff}</h3>
                    <p className="mt-2 text-sm leading-6 text-zinc-300">
                      {scenario.risk_change_summary}
                    </p>
                  </div>
                  <ListCard title={ws.caveats} items={scenario.caveats} emptyLabel={ws.noCaveats} />
                </div>
              )}
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
  helper,
  className = "",
}: {
  label: string;
  children: ReactNode;
  helper?: string;
  className?: string;
}) {
  return (
    <label className={`block min-w-0 text-sm ${className}`}>
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </span>
      {children}
      {helper ? (
        <span className="mt-1.5 block text-xs leading-5 text-zinc-600">{helper}</span>
      ) : null}
    </label>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-4 rounded-2xl border border-dashed border-white/10 bg-black/20 p-5">
      <h3 className="font-medium text-zinc-200">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{body}</p>
    </div>
  );
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "good" | "warning" | "danger" | "neutral";
}) {
  const toneClass = {
    good: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
    warning: "border-amber-300/30 bg-amber-300/10 text-amber-100",
    danger: "border-rose-300/30 bg-rose-300/10 text-rose-100",
    neutral: "border-white/10 bg-white/10 text-zinc-200",
  }[tone];

  return (
    <span className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-medium ${toneClass}`}>
      {children}
    </span>
  );
}

function InsightPanel({
  title,
  helper,
  badge,
  children,
}: {
  title: string;
  helper: string;
  badge?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-zinc-400">{helper}</p>
        </div>
        {badge}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function InsightStat({
  label,
  value,
  helper,
}: {
  label: string;
  value: number | null | undefined;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="mt-2 break-words text-2xl font-semibold tabular-nums">
        {formatNumber(value)}
      </div>
      <p className="mt-2 text-xs leading-5 text-zinc-500">{helper}</p>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 break-words text-sm font-medium tabular-nums text-zinc-200">
        {formatNumber(value)}
        {suffix}
      </div>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: number | null | undefined }) {
  const numericValue = typeof value === "number" && !Number.isNaN(value) ? value : 0;

  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-zinc-300">{label}</span>
        <span className="font-medium tabular-nums">{formatNumber(value)}</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-white/10">
        <div
          className="h-2 rounded-full bg-amber-100"
          style={{ width: `${Math.max(0, Math.min(numericValue, 100))}%` }}
        />
      </div>
    </div>
  );
}

function ListContent({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm leading-6 text-zinc-400">{emptyLabel}</p>;
  }

  return (
    <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
      {items.map((item) => (
        <li key={item} className="break-words">
          {item}
        </li>
      ))}
    </ul>
  );
}

function MetricCard({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  suffix?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="mt-2 break-words text-2xl font-semibold tabular-nums">
        {formatNumber(value)}
        {suffix}
      </div>
    </div>
  );
}

function ExposureCard({
  title,
  items,
  copy,
}: {
  title: string;
  items: Record<string, number>;
  copy: {
    noExposure: string;
    showMore: string;
    more: string;
  };
}) {
  const entries = Object.entries(items).sort(([, a], [, b]) => b - a);
  const primaryEntries = entries.slice(0, 3);
  const remainingEntries = entries.slice(3);

  const renderExposure = ([label, pct]: [string, number]) => (
    <div key={label}>
      <div className="flex items-center justify-between text-sm">
        <span className="min-w-0 break-words pr-3">{label}</span>
        <span>{pct.toFixed(2)}%</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-white/10">
        <div
          className="h-2 rounded-full bg-white"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-4 space-y-3">
        {entries.length === 0 ? (
          <p className="text-sm text-zinc-400">{copy.noExposure}</p>
        ) : (
          <>
            {primaryEntries.map(renderExposure)}
            {remainingEntries.length > 0 ? (
              <details className="pt-1">
                <summary className="cursor-pointer text-xs text-zinc-500">
                  {copy.showMore} {remainingEntries.length} {copy.more}
                </summary>
                <div className="mt-3 space-y-3">
                  {remainingEntries.map(renderExposure)}
                </div>
              </details>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function ListCard({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-400">{emptyLabel}</p>
      ) : (
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-300">
          {items.map((item) => (
            <li key={item} className="break-words">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function InfoPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-zinc-300">{body}</p>
    </div>
  );
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
}

function scoreTone(value: number | null | undefined): "good" | "warning" | "danger" | "neutral" {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "neutral";
  }
  if (value >= 75) return "good";
  if (value >= 50) return "warning";
  return "danger";
}

function scoreLabel(
  value: number | null | undefined,
  copy: {
    healthy: string;
    needsReview: string;
    highAttention: string;
    notScored: string;
  },
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return copy.notScored;
  }
  if (value >= 75) return copy.healthy;
  if (value >= 50) return copy.needsReview;
  return copy.highAttention;
}
