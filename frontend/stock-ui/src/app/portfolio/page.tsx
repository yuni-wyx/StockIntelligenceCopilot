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

const textareaClassName =
  "min-h-36 w-full min-w-0 resize-y rounded-xl border border-white/10 bg-black/45 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50";

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
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null);
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [agentResponse, setAgentResponse] = useState<PortfolioAgentResponse | null>(null);
  const [savedPortfolios, setSavedPortfolios] = useState<Array<Record<string, unknown>>>([]);
  const [compareJson, setCompareJson] = useState(DEFAULT_COMPARE_JSON);
  const [comparison, setComparison] = useState<ScenarioComparisonResponse | null>(null);
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

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    setScenario(null);
    setAgentResponse(null);
    try {
      const result = await analyzePortfolio(currentPortfolioPayload());
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze portfolio.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setLoading(true);
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
    }
  }

  async function handleLoad() {
    setLoading(true);
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
    }
  }

  async function handleScenario() {
    setLoading(true);
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
    }
  }

  async function handleCompareScenarios() {
    setLoading(true);
    setError(null);
    try {
      const parsed = JSON.parse(compareJson) as Array<{
        name: string;
        actions: Array<{
          action: "sell" | "buy" | "hold_cash";
          ticker: string;
          shares?: number;
          percentage?: number;
          amount?: number;
        }>;
        user_question?: string;
      }>;
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
    }
  }

  async function handleAskAgent() {
    setLoading(true);
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
                  </p>
                </div>
                <button
                  onClick={addHolding}
                  className="w-full rounded-xl bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-amber-100 sm:w-auto"
                >
                  Add Holding
                </button>
              </div>

              <div className="mt-5 space-y-3">
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
                            className={inputClassName}
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
                            className={inputClassName}
                          />
                        </Field>
                        <Field label="Current Price">
                          <input
                            value={holding.current_price ?? ""}
                            onChange={(e) => updateHolding(index, "current_price", e.target.value)}
                            className={inputClassName}
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
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Current Value">
                        <input
                          value={holding.current_value ?? ""}
                          onChange={(e) => updateHolding(index, "current_value", e.target.value)}
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Asset Type">
                        <input
                          value={holding.asset_type ?? ""}
                          onChange={(e) => updateHolding(index, "asset_type", e.target.value)}
                          className={inputClassName}
                        />
                      </Field>
                      <Field label="Category">
                        <input
                          value={holding.category ?? ""}
                          onChange={(e) => updateHolding(index, "category", e.target.value)}
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
                  disabled={loading}
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
              <h2 className="text-xl font-semibold">Portfolio Insights</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Health scoring, exposure views, risk flags, missing data, and suggested next steps.
              </p>

              {!analysis ? (
                <EmptyState
                  title="No analysis yet"
                  body="Run Analyze Holdings to turn your positions into portfolio-level insights."
                />
              ) : (
                <div className="mt-5 space-y-6">
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard label="Health Score" value={analysis.overall_score} />
                    <MetricCard label="Total Value" value={analysis.total_current_value} />
                    <MetricCard label="Unrealized P/L" value={analysis.total_unrealized_gain_loss} />
                    <MetricCard label="Return %" value={analysis.total_return_pct} suffix="%" />
                    <MetricCard label="Total Cost" value={analysis.total_cost_basis} />
                    <MetricCard label="Annual Dividend" value={analysis.estimated_annual_dividend} />
                    <MetricCard label="Monthly Dividend" value={analysis.estimated_monthly_dividend} />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                    <MetricCard label="Diversification" value={analysis.diversification_score} />
                    <MetricCard label="Concentration" value={analysis.concentration_score} />
                    <MetricCard label="Income" value={analysis.income_score} />
                    <MetricCard label="Defensive" value={analysis.defensive_score} />
                    <MetricCard label="Growth" value={analysis.growth_score} />
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <h3 className="font-semibold">Summary</h3>
                    <p className="mt-3 text-sm leading-6 text-zinc-300">{analysis.summary}</p>

                    <div className="mt-5 overflow-x-auto">
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
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="space-y-4">
                      <ExposureCard title="Asset Type Exposure" items={analysis.asset_type_exposure} />
                      <ExposureCard title="Category Exposure" items={analysis.category_exposure} />
                      <ExposureCard title="Sector Exposure" items={analysis.sector_exposure} />
                    </div>
                    <div className="space-y-4">
                      <ExposureCard title="Theme Exposure" items={analysis.theme_exposure} />
                      <ExposureCard title="Market Exposure" items={analysis.market_exposure} />
                      <ListCard
                        title="Missing Data"
                        items={analysis.missing_data}
                        emptyLabel="No material data gaps were detected."
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <ListCard
                      title="Risk Flags"
                      items={analysis.risk_flags}
                      emptyLabel="No major risk flags detected."
                    />
                    <ListCard
                      title="Suggestions"
                      items={analysis.suggestions}
                      emptyLabel="No suggestions available."
                    />
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <h3 className="font-semibold">News To Monitor</h3>
                    <div className="mt-4 space-y-4">
                      {Object.keys(analysis.news_to_monitor).length === 0 ? (
                        <p className="text-sm text-zinc-400">
                          No news headlines were captured for the current holdings.
                        </p>
                      ) : (
                        Object.entries(analysis.news_to_monitor).map(([ticker, headlines]) => (
                          <div key={ticker}>
                            <h4 className="font-medium text-white">{ticker}</h4>
                            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-zinc-300">
                              {headlines.map((headline) => (
                                <li key={headline}>{headline}</li>
                              ))}
                            </ul>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>

            {agentResponse ? (
              <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
                <h2 className="text-xl font-semibold">AI Portfolio Coach Recommendation</h2>
                <p className="mt-3 text-sm leading-6 text-zinc-200">{agentResponse.conclusion}</p>
                <p className="mt-3 text-sm leading-6 text-zinc-300">
                  {agentResponse.current_portfolio_diagnosis}
                </p>
                <div className="mt-4 grid gap-4 xl:grid-cols-2">
                  <ListCard
                    title="Suggested Next Actions"
                    items={agentResponse.suggested_next_actions}
                    emptyLabel="No suggested actions."
                  />
                  <ListCard title="Risks" items={agentResponse.risks} emptyLabel="No risks listed." />
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-3">
                  <InfoPanel title="Bull Case" body={agentResponse.bull_case} />
                  <InfoPanel title="Bear Case" body={agentResponse.bear_case} />
                  <InfoPanel title="Base Case" body={agentResponse.base_case} />
                </div>
              </section>
            ) : null}

            <section className="rounded-2xl border border-white/10 bg-zinc-900/60 p-5">
              <h2 className="text-xl font-semibold">Scenario Comparison</h2>
              <p className="mt-1 text-sm leading-6 text-zinc-400">
                Compare multiple named scenarios with the same backend contract.
                The JSON editor remains available for power users.
              </p>
              <textarea
                value={compareJson}
                onChange={(e) => setCompareJson(e.target.value)}
                rows={10}
                className="mt-4 min-h-64 w-full resize-y rounded-xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-sm leading-6 text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50"
              />
              <button
                onClick={handleCompareScenarios}
                disabled={loading}
                className="mt-4 rounded-xl border border-white/10 bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
              >
                Compare Scenarios
              </button>

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
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block min-w-0 text-sm ${className}`}>
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </span>
      {children}
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
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-4 space-y-3">
        {Object.keys(items).length === 0 ? (
          <p className="text-sm text-zinc-400">No exposure data available.</p>
        ) : (
          Object.entries(items).map(([label, pct]) => (
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
          ))
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
