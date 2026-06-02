"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
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
import { normalizeTicker } from "@/lib/tickerMap";

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

type HoldingValidationField = "ticker" | "shares" | "avg_cost" | "current_price";

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

const scenarioKindOptions: Array<{
  value: ComparisonScenarioKind;
  label: string;
  helper: string;
}> = [
  {
    value: "sell_percentage",
    label: "Sell X% of ticker",
    helper: "Model trimming an existing position by percentage.",
  },
  {
    value: "buy_amount",
    label: "Buy $ amount of ticker",
    helper: "Model adding a fixed cash amount to a ticker.",
  },
  {
    value: "reduce_concentration",
    label: "Reduce concentration in ticker",
    helper: "Model reducing an overweight position by percentage.",
  },
  {
    value: "add_position",
    label: "Add new ETF/stock",
    helper: "Model starting a new position with a fixed cash amount.",
  },
];

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<HoldingInput[]>([
    {
      ticker: "00878",
      name: "國泰永續高股息",
      avg_cost: 21.76,
      current_price: 32.06,
      shares: 2239,
      asset_type: "ETF",
      category: "High Dividend",
    },
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
          ...holding,
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
          message: `${rowLabel}: add a ticker before analyzing.`,
        });
        fieldKeys.add(`${index}:ticker`);
      }

      if (holding.shares === undefined || Number.isNaN(holding.shares)) {
        messages.push({
          rowIndex: index,
          field: "shares",
          message: `${rowLabel}: shares are required and must be positive.`,
        });
        fieldKeys.add(`${index}:shares`);
      } else if (holding.shares <= 0) {
        messages.push({
          rowIndex: index,
          field: "shares",
          message: `${rowLabel}: shares must be greater than 0.`,
        });
        fieldKeys.add(`${index}:shares`);
      }

      if (holding.avg_cost !== undefined) {
        if (Number.isNaN(holding.avg_cost) || holding.avg_cost < 0) {
          messages.push({
            rowIndex: index,
            field: "avg_cost",
            message: `${rowLabel}: average cost cannot be negative.`,
          });
          fieldKeys.add(`${index}:avg_cost`);
        }
      }

      if (holding.current_price !== undefined) {
        if (Number.isNaN(holding.current_price) || holding.current_price < 0) {
          messages.push({
            rowIndex: index,
            field: "current_price",
            message: `${rowLabel}: current price cannot be negative.`,
          });
          fieldKeys.add(`${index}:current_price`);
        }
      }
    });

    if (holdings.length === 0) {
      messages.push({
        rowIndex: -1,
        field: "ticker",
        message: "Add at least one holding before running an analysis.",
      });
    }

    return {
      messages,
      fieldKeys,
      hasErrors: messages.length > 0,
    };
  }, [holdings]);

  function currentPortfolioPayload() {
    return {
      holdings: normalizedHoldings,
      risk_profile: riskProfile,
      goal,
      base_currency: "TWD",
    };
  }

  function updateHolding(index: number, field: keyof HoldingInput, value: string) {
    setHoldings((prev) =>
      prev.map((holding, currentIndex) => {
        if (currentIndex !== index) return holding;
        if (["avg_cost", "current_price", "current_value", "shares"].includes(field)) {
          return {
            ...holding,
            [field]: value === "" ? undefined : Number(value),
          };
        }
        return {
          ...holding,
          [field]: value,
        };
      }),
    );
  }

  function addHolding() {
    setHoldings((prev) => appendHolding(prev));
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
      const actionLabel =
        scenarioKindOptions.find((option) => option.value === scenarioItem.kind)?.label ??
        "Scenario";

      if (!ticker) {
        errors.push(`${name}: ticker is required.`);
      }

      if (
        scenarioItem.kind === "sell_percentage" ||
        scenarioItem.kind === "reduce_concentration"
      ) {
        if (!scenarioItem.percentage.trim() || Number.isNaN(percentage)) {
          errors.push(`${name}: percentage is required.`);
        } else if (percentage <= 0 || percentage > 100) {
          errors.push(`${name}: percentage must be between 0 and 100.`);
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
        errors.push(`${name}: amount is required.`);
      } else if (amount <= 0) {
        errors.push(`${name}: amount must be positive.`);
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
      setError("Please fix the highlighted holding details before analyzing.");
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
      const message = err instanceof Error ? err.message : "Failed to analyze portfolio.";
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
      setError(err instanceof Error ? err.message : "Failed to save portfolio.");
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
        setError("No saved current portfolio found.");
        return;
      }
      setHoldings(record.portfolio.holdings ?? []);
      setRiskProfile(record.portfolio.risk_profile ?? "Balanced");
      setGoal(record.portfolio.goal ?? "");
      const listed = await listSavedPortfolios();
      setSavedPortfolios(listed.portfolios);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio.");
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
      setError(err instanceof Error ? err.message : "Failed to run scenario.");
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
        err instanceof Error ? err.message : "Failed to compare portfolio scenarios.",
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
      setError(err instanceof Error ? err.message : "Failed to get agent recommendation.");
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
              Wealth Studio
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Wealth Studio
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-300">
              A calmer workspace for reviewing holdings, saving your local setup,
              asking portfolio questions, and testing reallocation ideas.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/"
              className="rounded-xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-zinc-200 transition hover:border-white/20"
            >
              Home
            </Link>
            <Link
              href="/copilot?mode=research"
              className="rounded-xl border border-white/10 bg-black/30 px-4 py-2 text-sm text-zinc-200 transition hover:border-white/20"
            >
              Research Mode
            </Link>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_380px]">
          <main className="min-w-0 space-y-6">
            <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Your Holdings</h2>
                  <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
                    Add the positions you want the studio to analyze. Keep only
                    the fields you know; missing data will be called out in the insights.
                    Ticker and positive shares are required.
                  </p>
                </div>
                <button
                  onClick={addHolding}
                  className="w-full rounded-xl bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-amber-100 sm:w-auto"
                >
                  Add Holding
                </button>
              </div>

              {holdingsValidation.hasErrors ? (
                <div className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
                  <h3 className="text-sm font-semibold text-amber-100">
                    Check these holding details
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-amber-100/75">
                    Common fixes: add a ticker, enter shares above 0, and keep
                    cost or price at 0 or higher.
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
                    title="No holdings yet"
                    body="Add a holding to start. You only need a ticker, positive shares, and any price or cost details you know."
                  />
                ) : null}

                {holdings.map((holding, index) => (
                  <div
                    key={`${holding.ticker}-${index}`}
                    className="rounded-2xl border border-white/10 bg-black/25 p-4"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:grid-cols-[0.9fr_1.4fr_0.9fr_0.9fr]">
                        <Field label="Ticker">
                          <input
                            value={holding.ticker}
                            onChange={(e) => updateHolding(index, "ticker", e.target.value)}
                            placeholder="00878 or NVDA"
                            className={holdingInputClass(index, "ticker")}
                          />
                        </Field>
                        <Field label="Name">
                          <input
                            value={holding.name ?? ""}
                            onChange={(e) => updateHolding(index, "name", e.target.value)}
                            className={inputClassName}
                          />
                        </Field>
                        <Field label="Shares">
                          <input
                            value={holding.shares ?? ""}
                            onChange={(e) => updateHolding(index, "shares", e.target.value)}
                            placeholder="2239"
                            className={holdingInputClass(index, "shares")}
                          />
                        </Field>
                        <Field label="Current Price">
                          <input
                            value={holding.current_price ?? ""}
                            onChange={(e) => updateHolding(index, "current_price", e.target.value)}
                            placeholder="0 or higher"
                            className={holdingInputClass(index, "current_price")}
                          />
                        </Field>
                      </div>
                      <button
                        onClick={() => removeHolding(index)}
                        className="rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 transition hover:border-rose-300/50 hover:text-rose-200"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                      <Field label="Avg Cost">
                        <input
                          value={holding.avg_cost ?? ""}
                          onChange={(e) => updateHolding(index, "avg_cost", e.target.value)}
                          placeholder="0 or higher"
                          className={holdingInputClass(index, "avg_cost")}
                        />
                      </Field>
                      <Field label="Current Value">
                        <input
                          value={holding.current_value ?? ""}
                          onChange={(e) => updateHolding(index, "current_value", e.target.value)}
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Asset Type" helper="Optional, used for exposure grouping.">
                        <input
                          value={holding.asset_type ?? ""}
                          onChange={(e) => updateHolding(index, "asset_type", e.target.value)}
                          placeholder="ETF, stock, fund..."
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Category" helper="Optional, helps group income, growth, or themes.">
                        <input
                          value={holding.category ?? ""}
                          onChange={(e) => updateHolding(index, "category", e.target.value)}
                          placeholder="High Dividend, Tech..."
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Notes">
                        <input
                          value={holding.notes ?? ""}
                          onChange={(e) => updateHolding(index, "notes", e.target.value)}
                          className={inputClassName}
                        />
                      </Field>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-[0.45fr_1fr]">
                <Field label="Risk Profile">
                  <input
                    value={riskProfile}
                    onChange={(e) => setRiskProfile(e.target.value)}
                    placeholder="Balanced"
                    className={inputClassName}
                  />
                </Field>
                <Field label="Goal">
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
                  {loading ? "Working..." : "Analyze Holdings"}
                </button>
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  Save Workspace
                </button>
                <button
                  onClick={handleLoad}
                  disabled={loading}
                  className="rounded-xl border border-white/10 bg-black/20 px-5 py-3 text-sm text-zinc-200 transition hover:border-white/20 disabled:opacity-50"
                >
                  Load Saved
                </button>
              </div>
            </section>

            {error ? (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {error}
              </div>
            ) : null}

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">Saved Workspaces</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Save this local demo workspace, then reload it when you come back.
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
                        Holdings: {String(portfolio.holding_count ?? 0)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No saved workspace loaded yet"
                  body="Use Save Workspace after entering your holdings, or Load Saved if you already created a local demo portfolio."
                />
              )}
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Portfolio Insights</h2>
                  <p className="mt-1 text-sm leading-6 text-zinc-400">
                    Health, risk, allocation, income, and next-step signals after analysis.
                  </p>
                </div>
                {analysis ? (
                  <Badge tone={scoreTone(analysis.overall_score)}>
                    {scoreLabel(analysis.overall_score)}
                  </Badge>
                ) : null}
              </div>

              {activeOperation === "analyze" ? (
                <div className="mt-4 rounded-2xl border border-sky-300/25 bg-sky-300/10 p-5">
                  <h3 className="font-medium text-sky-100">Analyzing your holdings</h3>
                  <p className="mt-2 text-sm leading-6 text-sky-100/75">
                    Building portfolio health, risk, exposure, and next-step views.
                  </p>
                </div>
              ) : insightsError ? (
                <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-300/10 p-5">
                  <h3 className="font-medium text-rose-100">Insights could not be loaded</h3>
                  <p className="mt-2 break-words text-sm leading-6 text-rose-100/80">
                    {insightsError}
                  </p>
                </div>
              ) : !analysis ? (
                <EmptyState
                  title="No analysis yet"
                  body="Run an analysis to see your portfolio health, risks, and next steps."
                />
              ) : (
                <div className="mt-5 space-y-6">
                  <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
                    <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">Overall Health</h3>
                          <p className="mt-1 text-sm leading-6 text-zinc-400">
                            A heuristic snapshot of balance, concentration, income,
                            defensive exposure, and growth tilt.
                          </p>
                        </div>
                        <div className="text-left sm:text-right">
                          <div className="text-4xl font-semibold tabular-nums">
                            {formatNumber(analysis.overall_score)}
                          </div>
                          <Badge tone={scoreTone(analysis.overall_score)}>
                            {scoreLabel(analysis.overall_score)}
                          </Badge>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-3 sm:grid-cols-2">
                        <ScoreRow label="Diversification" value={analysis.diversification_score} />
                        <ScoreRow label="Concentration" value={analysis.concentration_score} />
                        <ScoreRow label="Income" value={analysis.income_score} />
                        <ScoreRow label="Defensive" value={analysis.defensive_score} />
                        <ScoreRow label="Growth" value={analysis.growth_score} />
                      </div>

                      <p className="mt-5 text-sm leading-6 text-zinc-300">
                        {analysis.summary}
                      </p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <InsightStat
                        label="Total Value"
                        value={analysis.total_current_value}
                        helper="Current value from entered holdings."
                      />
                      <InsightStat
                        label="Unrealized P/L"
                        value={analysis.total_unrealized_gain_loss}
                        helper={`${formatNumber(analysis.total_return_pct)}% total return`}
                      />
                      <InsightStat
                        label="Annual Dividend"
                        value={analysis.estimated_annual_dividend}
                        helper="Estimated income from available data."
                      />
                      <InsightStat
                        label="Monthly Dividend"
                        value={analysis.estimated_monthly_dividend}
                        helper="Monthly equivalent estimate."
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                    <div className="space-y-4">
                      <InsightPanel
                        title="Key Risks"
                        helper="Items to inspect before making changes."
                        badge={
                          <Badge tone={analysis.risk_flags.length > 0 ? "warning" : "good"}>
                            {analysis.risk_flags.length > 0 ? "Review" : "Clear"}
                          </Badge>
                        }
                      >
                        <ListContent
                          items={analysis.risk_flags}
                          emptyLabel="No major risk flags detected."
                        />
                      </InsightPanel>

                      <InsightPanel
                        title="Recommended Next Steps"
                        helper="Actionable ideas from the portfolio analysis and, when available, the AI coach."
                        badge={<Badge tone="neutral">{analysis.suggestions.length}</Badge>}
                      >
                        <ListContent
                          items={analysis.suggestions}
                          emptyLabel="No suggestions available."
                        />
                        {agentResponse ? (
                          <div className="mt-4 space-y-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                            <div>
                              <div className="text-xs font-medium uppercase tracking-[0.14em] text-amber-200/60">
                                AI Coach
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
                                title="Coach Actions"
                                items={agentResponse.suggested_next_actions}
                                emptyLabel="No coach actions listed."
                              />
                              <ListCard
                                title="Coach Risks"
                                items={agentResponse.risks}
                                emptyLabel="No coach risks listed."
                              />
                            </div>
                            <div className="grid gap-4 xl:grid-cols-3">
                              <InfoPanel title="Bull Case" body={agentResponse.bull_case} />
                              <InfoPanel title="Bear Case" body={agentResponse.bear_case} />
                              <InfoPanel title="Base Case" body={agentResponse.base_case} />
                            </div>
                          </div>
                        ) : null}
                      </InsightPanel>
                    </div>

                    <div className="space-y-4">
                      <InsightPanel
                        title="Allocation / Exposure"
                        helper="How holdings group across asset type, category, sector, theme, and market."
                        badge={<Badge tone="neutral">Exposure</Badge>}
                      >
                        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                          <ExposureCard title="Asset Type" items={analysis.asset_type_exposure} />
                          <ExposureCard title="Category" items={analysis.category_exposure} />
                          <ExposureCard title="Sector" items={analysis.sector_exposure} />
                          <ExposureCard title="Theme" items={analysis.theme_exposure} />
                          <ExposureCard title="Market" items={analysis.market_exposure} />
                        </div>
                      </InsightPanel>

                      <InsightPanel
                        title="Income / Data Quality"
                        helper="Dividend estimates are only as complete as the available holding data."
                        badge={<Badge tone={analysis.missing_data.length > 0 ? "warning" : "good"}>
                          {analysis.missing_data.length > 0 ? "Check data" : "Data OK"}
                        </Badge>}
                      >
                        <div className="grid gap-3 sm:grid-cols-2">
                          <InsightStat
                            label="Income Score"
                            value={analysis.income_score}
                            helper="Heuristic income profile."
                          />
                          <InsightStat
                            label="Total Cost"
                            value={analysis.total_cost_basis}
                            helper="Basis from entered rows."
                          />
                        </div>
                        <div className="mt-4">
                          <ListContent
                            items={analysis.missing_data}
                            emptyLabel="No material data gaps were detected."
                          />
                        </div>
                      </InsightPanel>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="font-semibold">News To Monitor</h3>
                        <p className="mt-1 text-sm leading-6 text-zinc-400">
                          Headlines attached to the current holdings, when available.
                        </p>
                      </div>
                      <Badge tone={Object.keys(analysis.news_to_monitor).length > 0 ? "neutral" : "good"}>
                        {Object.keys(analysis.news_to_monitor).length} ticker
                        {Object.keys(analysis.news_to_monitor).length === 1 ? "" : "s"}
                      </Badge>
                    </div>
                    <div className="mt-4 space-y-4">
                      {Object.keys(analysis.news_to_monitor).length === 0 ? (
                        <p className="text-sm text-zinc-400">
                          No news headlines were captured for the current holdings.
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
                      Holding Details
                    </summary>
                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      Position-level weights, gains, dividends, and themes from the same analysis.
                    </p>
                    <div className="mt-4 overflow-x-auto">
                      <table className="min-w-[620px] text-left text-sm">
                        <thead className="text-zinc-400">
                          <tr>
                            {["Ticker", "Weight %", "P/L", "Return %", "Annual Div", "Theme"].map(
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
              <h2 className="text-xl font-semibold">Scenario Comparison</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Build a few clean what-if scenarios, then compare them with the
                same backend scenario contract.
              </p>

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-zinc-400">
                  {comparisonScenarios.length > 0
                    ? `${comparisonScenarios.length} structured scenario${
                        comparisonScenarios.length === 1 ? "" : "s"
                      } ready`
                    : "No structured scenarios added yet"}
                </div>
                <button
                  onClick={addComparisonScenario}
                  className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-100"
                >
                  Add Scenario
                </button>
              </div>

              {comparisonScenarios.length === 0 ? (
                <EmptyState
                  title="No comparison scenarios yet"
                  body="Add a scenario such as selling a percentage of one ticker, buying a cash amount, reducing concentration, or adding a new ETF/stock."
                />
              ) : (
                <div className="mt-4 space-y-4">
                  {comparisonScenarios.map((scenarioItem, index) => {
                    const selectedKind = scenarioKindOptions.find(
                      (option) => option.value === scenarioItem.kind,
                    );
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
                              Scenario {index + 1}
                            </div>
                            <h3 className="mt-1 font-semibold">
                              {scenarioItem.name.trim() || `Scenario ${index + 1}`}
                            </h3>
                            <p className="mt-1 text-sm leading-6 text-zinc-400">
                              {selectedKind?.helper}
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
                          <Field label="Scenario name">
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
                          <Field label="Scenario type">
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
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </Field>
                        </div>

                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                          <Field label="Ticker">
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
                            <Field label="Sell percentage">
                              <input
                                value={scenarioItem.percentage}
                                onChange={(e) =>
                                  updateComparisonScenario(
                                    scenarioItem.id,
                                    "percentage",
                                    e.target.value,
                                  )
                                }
                                placeholder="50"
                                className={inputClassName}
                              />
                            </Field>
                          ) : (
                            <Field label="Buy amount">
                              <input
                                value={scenarioItem.amount}
                                onChange={(e) =>
                                  updateComparisonScenario(
                                    scenarioItem.id,
                                    "amount",
                                    e.target.value,
                                  )
                                }
                                placeholder="35000"
                                className={inputClassName}
                              />
                            </Field>
                          )}
                          <Field label="Question">
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
                    Please fix these scenario details
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
                  Run Scenario Comparison
                </button>
                {comparisonScenarios.length === 0 ? (
                  <span className="text-sm text-zinc-500">
                    Advanced JSON will be used until you add structured scenarios.
                  </span>
                ) : (
                  <span className="text-sm text-zinc-500">
                    Structured scenarios will be converted to the existing API payload.
                  </span>
                )}
              </div>

              <details className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
                  Advanced JSON editor
                </summary>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  Kept for compatibility and power users. It is used only when
                  no structured scenarios are added above.
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
                          "Scenario",
                          "Rank",
                          "Score Δ",
                          "Dividend Δ",
                          "Tech Δ",
                          "Defensive Δ",
                          "Concentration Δ",
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
              <h2 className="text-xl font-semibold">AI Portfolio Coach</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Ask a plain-language question about the portfolio you entered.
              </p>
              <Field label="Question" className="mt-4">
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
                Ask Portfolio Coach
              </button>
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/70 p-5 shadow-2xl shadow-black/20">
              <h2 className="text-xl font-semibold">Scenario Simulator</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Model a simple sell and buy action without changing your saved workspace.
              </p>
              <div className="mt-4 space-y-4">
                <Field label="Sell ticker">
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
                  <Field label="Sell shares">
                    <input
                      value={scenarioForm.sellShares}
                      onChange={(e) =>
                        setScenarioForm((prev) => ({ ...prev, sellShares: e.target.value }))
                      }
                      placeholder="Optional"
                      className={inputClassName}
                    />
                  </Field>
                  <Field label="Sell %">
                    <input
                      value={scenarioForm.sellPercentage}
                      onChange={(e) =>
                        setScenarioForm((prev) => ({
                          ...prev,
                          sellPercentage: e.target.value,
                        }))
                      }
                      placeholder="50"
                      className={inputClassName}
                    />
                  </Field>
                </div>
                <Field label="Buy ticker / fund">
                  <input
                    value={scenarioForm.buyTicker}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyTicker: e.target.value }))
                    }
                    placeholder="2330"
                    className={inputClassName}
                  />
                </Field>
                <Field label="Buy amount">
                  <input
                    value={scenarioForm.buyAmount}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyAmount: e.target.value }))
                    }
                    placeholder="35000"
                    className={inputClassName}
                  />
                </Field>
                <Field label="Buy name">
                  <input
                    value={scenarioForm.buyName}
                    onChange={(e) =>
                      setScenarioForm((prev) => ({ ...prev, buyName: e.target.value }))
                    }
                    placeholder="Optional fund or company name"
                    className={inputClassName}
                  />
                </Field>
                <Field label="Scenario question">
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
                  Run Scenario
                </button>
              </div>
            </section>

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">Scenario Result</h2>
              {!scenario ? (
                <EmptyState
                  title="No scenario result yet"
                  body="Run a scenario to see before/after value, dividend change, and risk tradeoffs."
                />
              ) : (
                <div className="mt-4 space-y-4">
                  <p className="text-sm leading-6 text-zinc-300">{scenario.recommendation}</p>
                  <div className="grid gap-3">
                    <MetricCard label="Before Value" value={scenario.before.total_current_value} />
                    <MetricCard label="After Value" value={scenario.after.total_current_value} />
                    <MetricCard label="Dividend Change" value={scenario.dividend_change} />
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <h3 className="font-semibold">Risk Tradeoff</h3>
                    <p className="mt-2 text-sm leading-6 text-zinc-300">
                      {scenario.risk_change_summary}
                    </p>
                  </div>
                  <ListCard title="Caveats" items={scenario.caveats} emptyLabel="No caveats." />
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
}: {
  title: string;
  items: Record<string, number>;
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
          <p className="text-sm text-zinc-400">No exposure data available.</p>
        ) : (
          <>
            {primaryEntries.map(renderExposure)}
            {remainingEntries.length > 0 ? (
              <details className="pt-1">
                <summary className="cursor-pointer text-xs text-zinc-500">
                  Show {remainingEntries.length} more
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

function scoreLabel(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Not scored";
  }
  if (value >= 75) return "Healthy";
  if (value >= 50) return "Needs review";
  return "High attention";
}
