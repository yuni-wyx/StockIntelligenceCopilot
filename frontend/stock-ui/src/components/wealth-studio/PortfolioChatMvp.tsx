"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import { previewPortfolioImport, type HoldingInput, type PortfolioChatResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";
import type { PortfolioAnalysisResponse } from "@/lib/portfolioApi";

export type PortfolioChatMvpState =
  | "NO_PORTFOLIO"
  | "ASK_HOLDINGS"
  | "CONFIRM_HOLDINGS"
  | "PORTFOLIO_SAVED"
  | "CHAT_READY";

export type PortfolioChatMessage = {
  id: string;
  role: "assistant" | "user";
  body: string;
};

type Props = {
  copy: WealthStudioCopy;
  state: PortfolioChatMvpState;
  messages: PortfolioChatMessage[];
  inputValue: string;
  pendingHoldings: HoldingInput[];
  savedHoldings: HoldingInput[];
  analysis: PortfolioAnalysisResponse | null;
  wizardStep: string | null;
  lastUpdated?: string | null;
  loading: boolean;
  error?: string | null;
  chatResponse?: PortfolioChatResponse | null;
  starterPrompts: string[];
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onSavePending: () => void;
  onEditPending: () => void;
  onAddAnotherHolding: () => void;
  onSaveTable: (holdings: HoldingInput[]) => Promise<void>;
  onStartOver: () => void;
  onReplacePortfolio: () => void;
  onUsePrompt: (prompt: string) => void;
};

function formatHolding(holding: HoldingInput): string {
  const shares =
    holding.shares === undefined || holding.shares === null
      ? "-"
      : holding.shares.toLocaleString();
  const avgCost =
    holding.avg_cost === undefined || holding.avg_cost === null
      ? "-"
      : holding.avg_cost.toLocaleString();
  return `${holding.name || holding.ticker}: ${shares} shares, avg cost ${avgCost}`;
}

function formatHoldingZh(holding: HoldingInput): string {
  const shares =
    holding.shares === undefined || holding.shares === null
      ? "-"
      : holding.shares.toLocaleString();
  const avgCost =
    holding.avg_cost === undefined || holding.avg_cost === null
      ? "-"
      : holding.avg_cost.toLocaleString();
  return `${holding.name || holding.ticker}：${shares} 股，平均成本 ${avgCost}`;
}

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-200 [animation-delay:-0.24s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-200 [animation-delay:-0.12s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-amber-200" />
    </span>
  );
}

function formatMetric(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function formatMoney(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function metricTone(value: number | null | undefined) {
  return value !== undefined && value !== null && value >= 0 ? "text-emerald-300" : "text-rose-300";
}

function PortfolioOverview({
  copy,
  analysis,
  hasSavedPortfolio,
}: {
  copy: WealthStudioCopy;
  analysis: PortfolioAnalysisResponse | null;
  hasSavedPortfolio: boolean;
}) {
  const topHolding = analysis?.holdings
    ?.slice()
    .sort((a, b) => (b.portfolio_weight_pct ?? 0) - (a.portfolio_weight_pct ?? 0))[0];
  const winner = analysis?.holdings
    ?.slice()
    .sort((a, b) => (b.return_pct ?? -Infinity) - (a.return_pct ?? -Infinity))[0];
  const riskFlag = analysis?.risk_flags?.[0];

  if (!hasSavedPortfolio) {
    return (
      <section className="rounded-3xl border border-amber-200/20 bg-[radial-gradient(circle_at_top_right,rgba(251,191,36,0.12),transparent_45%),rgba(24,22,18,0.8)] p-6 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">Portfolio overview</p>
        <h2 className="mt-3 max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">See what is happening in your portfolio.</h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">Save your holdings once, then get the day’s most important review items without searching through every panel.</p>
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-white/10 bg-zinc-950/75 p-5 shadow-2xl shadow-black/20 sm:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">Portfolio overview</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">{formatMoney(analysis?.total_current_value)}</h2>
            <p className="mt-1 text-sm text-zinc-500">{copy.currentValue} · TWD</p>
          </div>
          <p className={`text-sm font-semibold ${metricTone(analysis?.total_unrealized_gain_loss)}`}>
            {formatMoney(analysis?.total_unrealized_gain_loss)} ({formatMetric(analysis?.total_return_pct, "%")}) total return
          </p>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            ["Invested", formatMoney(analysis?.total_cost_basis), "Cost basis"],
            ["Total return", formatMoney(analysis?.total_unrealized_gain_loss), formatMetric(analysis?.total_return_pct, "%")],
            ["Today", "—", "Daily price data unavailable"],
          ].map(([label, value, helper]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-black/25 p-4">
              <p className="text-xs text-zinc-500">{label}</p>
              <p className="mt-2 text-xl font-semibold text-zinc-100">{value}</p>
              <p className="mt-1 text-xs text-zinc-500">{helper}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-amber-200/20 bg-amber-200/[0.06] p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">What needs your attention</p>
            <h2 className="mt-2 text-xl font-semibold text-zinc-100">Your next review items</h2>
          </div>
          <span className="rounded-full border border-amber-200/20 px-3 py-1 text-xs text-amber-100">{analysis?.risk_flags?.length ?? 0} signals</span>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-semibold text-zinc-100">{topHolding?.ticker ?? "—"} concentration</p>
            <p className="mt-2 text-sm leading-6 text-zinc-400">{topHolding ? `${formatMetric(topHolding.portfolio_weight_pct, "%")} of portfolio value` : "Position weight is unavailable."}</p>
            <button type="button" onClick={() => document.getElementById("portfolio-holdings")?.scrollIntoView({ behavior: "smooth" })} className="mt-3 text-xs font-semibold text-amber-200 hover:text-amber-100">View position →</button>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-semibold text-zinc-100">{winner?.ticker ?? "—"} biggest winner</p>
            <p className={`mt-2 text-sm leading-6 ${metricTone(winner?.return_pct)}`}>{winner ? `${formatMetric(winner.return_pct, "%")} since purchase` : "Return data is unavailable."}</p>
            <button type="button" onClick={() => document.getElementById("portfolio-holdings")?.scrollIntoView({ behavior: "smooth" })} className="mt-3 text-xs font-semibold text-amber-200 hover:text-amber-100">View position →</button>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-semibold text-zinc-100">Review risk flags</p>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-zinc-400">{riskFlag ?? "No risk flags were returned."}</p>
            <button type="button" onClick={() => document.getElementById("portfolio-chat")?.scrollIntoView({ behavior: "smooth" })} className="mt-3 text-xs font-semibold text-amber-200 hover:text-amber-100">Analyze portfolio →</button>
          </div>
        </div>
      </section>
    </div>
  );
}

const PORTFOLIO_CHART_COLORS = [
  "#fbbf24",
  "#34d399",
  "#60a5fa",
  "#c084fc",
  "#fb7185",
  "#22d3ee",
  "#f97316",
  "#a3e635",
];

function PortfolioVisualizations({
  copy,
  analysis,
}: {
  copy: WealthStudioCopy;
  analysis: PortfolioAnalysisResponse | null;
}) {
  if (!analysis || analysis.holdings.length === 0) return null;

  const isChinese = copy.portfolioCopilotTitle === "投資組合助手";
  const totalValue = analysis.total_current_value ?? 0;
  const holdings = analysis.holdings.map((holding, index) => ({
    ...holding,
    value: holding.current_value ?? 0,
    cost: holding.cost_basis ?? 0,
    gain: holding.unrealized_gain_loss ?? 0,
    weight: holding.portfolio_weight_pct ?? (totalValue > 0 ? ((holding.current_value ?? 0) / totalValue) * 100 : 0),
    color: PORTFOLIO_CHART_COLORS[index % PORTFOLIO_CHART_COLORS.length],
  }));
  const maxValue = Math.max(...holdings.map((holding) => Math.max(holding.value, holding.cost)), 1);
  const maxAbsGain = Math.max(...holdings.map((holding) => Math.abs(holding.gain)), 1);
  const allocationStops = holdings.reduce<{ stops: string[]; cursor: number }>(
    (result, holding) => {
      const start = result.cursor;
      const end = start + Math.max(holding.weight, 0);
      result.stops.push(`${holding.color} ${start}% ${end}%`);
      result.cursor = end;
      return result;
    },
    { stops: [], cursor: 0 },
  ).stops;
  const sortedGains = holdings.slice().sort((a, b) => Math.abs(b.gain) - Math.abs(a.gain));

  return (
    <section aria-labelledby="portfolio-visualizations" className="space-y-4">
      <div className="flex items-end justify-between gap-3 px-1">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">Portfolio signals</p>
          <h2 id="portfolio-visualizations" className="mt-2 text-2xl font-semibold text-zinc-100">{isChinese ? "看懂你的持股" : "Understand your holdings"}</h2>
        </div>
        <p className="hidden text-xs text-zinc-500 sm:block">{isChinese ? "以現有持股資料即時計算" : "Calculated from current holdings"}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <article className="rounded-3xl border border-white/10 bg-zinc-950/70 p-5 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-zinc-100">{isChinese ? "持股配置" : "Allocation"}</h3>
              <p className="mt-1 text-xs leading-5 text-zinc-500">{isChinese ? "每一塊代表目前現值占比" : "Each slice represents current portfolio value"}</p>
            </div>
            <span className="rounded-full border border-amber-200/20 px-2.5 py-1 text-[11px] text-amber-100">{holdings.length} holdings</span>
          </div>
          <div className="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:items-center">
            <div
              className="relative h-40 w-40 shrink-0 rounded-full"
              role="img"
              aria-label={isChinese ? "持股配置圓環圖" : "Portfolio allocation donut chart"}
              style={{ background: `conic-gradient(${allocationStops.join(", ")})` }}
            >
              <div className="absolute inset-[18px] flex flex-col items-center justify-center rounded-full bg-[#11100e] text-center">
                <span className="text-lg font-semibold text-zinc-100">{formatMoney(totalValue)}</span>
                <span className="mt-1 text-[10px] uppercase tracking-[0.16em] text-zinc-500">TWD value</span>
              </div>
            </div>
            <div className="grid w-full grid-cols-1 gap-2 text-xs sm:grid-cols-2">
              {holdings.map((holding) => (
                <div key={holding.ticker} className="flex min-w-0 items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: holding.color }} />
                  <span className="truncate text-zinc-300">{holding.ticker}</span>
                  <span className="ml-auto shrink-0 tabular-nums text-zinc-500">{formatMetric(holding.weight, "%")}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded-3xl border border-white/10 bg-zinc-950/70 p-5 sm:p-6">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">{isChinese ? "個股損益" : "Position P&L"}</h3>
            <p className="mt-1 text-xs leading-5 text-zinc-500">{isChinese ? "按損益絕對金額排序，快速找到主要影響" : "Sorted by absolute gain or loss"}</p>
          </div>
          <div className="mt-5 space-y-3">
            {sortedGains.map((holding) => (
              <div key={holding.ticker} className="grid grid-cols-[4.5rem_minmax(0,1fr)_4.5rem] items-center gap-3 text-xs">
                <span className="truncate font-medium text-zinc-300">{holding.ticker}</span>
                <div className="h-2 rounded-full bg-white/[0.06]" aria-hidden="true">
                  <div className={`h-2 rounded-full ${holding.gain >= 0 ? "bg-emerald-300" : "bg-rose-300"}`} style={{ width: `${Math.max((Math.abs(holding.gain) / maxAbsGain) * 100, 3)}%` }} />
                </div>
                <span className={`text-right tabular-nums ${metricTone(holding.gain)}`}>
                  {holding.gain >= 0 ? "+" : ""}{formatMoney(holding.gain)}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-4 text-[11px] text-zinc-500">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-300" />{isChinese ? "獲利" : "Gain"}</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-300" />{isChinese ? "虧損" : "Loss"}</span>
          </div>
        </article>
      </div>

      <article className="rounded-3xl border border-white/10 bg-zinc-950/70 p-5 sm:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">{isChinese ? "成本與現值" : "Cost vs current value"}</h3>
            <p className="mt-1 text-xs leading-5 text-zinc-500">{isChinese ? "比較每檔持股投入的成本與目前價值" : "Compare invested cost with current value"}</p>
          </div>
          <div className="flex gap-4 text-[11px] text-zinc-500">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-zinc-500" />{isChinese ? "成本" : "Cost"}</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-200" />{isChinese ? "現值" : "Value"}</span>
          </div>
        </div>
        <div className="mt-5 space-y-3">
          {holdings.map((holding) => (
            <div key={holding.ticker} className="grid grid-cols-[4.5rem_minmax(0,1fr)_5rem] items-center gap-3 text-xs">
              <span className="truncate font-medium text-zinc-300">{holding.ticker}</span>
              <div className="space-y-1.5">
                <div className="h-2 rounded-full bg-white/[0.06]"><div className="h-2 rounded-full bg-zinc-500" style={{ width: `${Math.max((holding.cost / maxValue) * 100, holding.cost > 0 ? 2 : 0)}%` }} /></div>
                <div className="h-2 rounded-full bg-white/[0.06]"><div className="h-2 rounded-full bg-amber-200" style={{ width: `${Math.max((holding.value / maxValue) * 100, holding.value > 0 ? 2 : 0)}%` }} /></div>
              </div>
              <span className={`text-right tabular-nums ${metricTone(holding.gain)}`}>{formatMetric(holding.return_pct, "%")}</span>
            </div>
          ))}
        </div>
        <div className="mt-5 flex justify-between text-[11px] text-zinc-500"><span>{isChinese ? "上排：成本／下排：現值" : "Top: cost / bottom: value"}</span><span>{isChinese ? "右側為報酬率" : "Return on right"}</span></div>
      </article>
    </section>
  );
}

function HoldingsTable({ copy, analysis }: { copy: WealthStudioCopy; analysis: PortfolioAnalysisResponse | null }) {
  if (!analysis) return null;
  return (
    <section id="portfolio-holdings" className="rounded-3xl border border-white/10 bg-zinc-950/70 p-5 sm:p-6">
      <div className="flex items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">Your positions</p><h2 className="mt-2 text-2xl font-semibold">{copy.holdingsSection}</h2></div><span className="text-xs text-zinc-500">{analysis.holdings.length} positions</span></div>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="text-xs uppercase tracking-wide text-zinc-500"><tr>{["Stock", "Position", "Return", "Weight", "Action"].map((label) => <th key={label} className="px-3 py-3 font-medium">{label}</th>)}</tr></thead><tbody>{analysis.holdings.map((holding) => <tr key={holding.ticker} className="border-t border-white/5"><td className="px-3 py-4"><div className="font-semibold text-zinc-100">{holding.ticker}</div><div className="mt-1 text-xs text-zinc-500">{holding.name ?? holding.theme ?? "Equity"}</div></td><td className="px-3 py-4 text-zinc-200">{formatMoney(holding.current_value)}</td><td className={`px-3 py-4 font-semibold ${metricTone(holding.return_pct)}`}>{formatMetric(holding.return_pct, "%")}</td><td className="px-3 py-4 text-zinc-300">{formatMetric(holding.portfolio_weight_pct, "%")}</td><td className="px-3 py-4"><button type="button" onClick={() => document.getElementById("portfolio-chat")?.scrollIntoView({ behavior: "smooth" })} className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-zinc-300 transition hover:border-amber-200/40 hover:text-amber-100">{holding.return_pct !== undefined && (holding.return_pct ?? 0) < 0 ? "Why did it move?" : "Research"}</button></td></tr>)}</tbody></table></div>
    </section>
  );
}

type EditableTableRow = Record<"ticker" | "name" | "shares" | "buy_price" | "buy_date" | "current_price" | "sell_price" | "sell_date" | "category" | "notes", string>;
const TABLE_FIELDS: Array<keyof EditableTableRow> = ["ticker", "name", "shares", "buy_price", "buy_date", "current_price", "sell_price", "sell_date", "category", "notes"];
const TABLE_LABELS: Record<keyof EditableTableRow, string> = {
  ticker: "Ticker", name: "Name", shares: "Shares", buy_price: "Buy price", buy_date: "Buy date",
  current_price: "Current price", sell_price: "Sell price", sell_date: "Sell date", category: "Category", notes: "Notes",
};

function emptyTableRow(): EditableTableRow {
  return { ticker: "", name: "", shares: "", buy_price: "", buy_date: "", current_price: "", sell_price: "", sell_date: "", category: "", notes: "" };
}

function holdingToTableRow(holding: HoldingInput): EditableTableRow {
  const value = (field: keyof EditableTableRow) => {
    const source: Record<string, unknown> = holding;
    return source[field] === undefined || source[field] === null ? "" : String(source[field]);
  };
  return Object.fromEntries(TABLE_FIELDS.map((field) => [field, value(field)])) as EditableTableRow;
}

function HoldingsEditorModal({
  initialHoldings,
  isChinese,
  onClose,
  onSave,
}: {
  initialHoldings: HoldingInput[];
  isChinese: boolean;
  onClose: () => void;
  onSave: (holdings: HoldingInput[]) => Promise<void>;
}) {
  const [rows, setRows] = useState<EditableTableRow[]>(() => (initialHoldings.length ? initialHoldings.map(holdingToTableRow) : [emptyTableRow()]));
  const [saveError, setSaveError] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  function updateCell(rowIndex: number, field: keyof EditableTableRow, value: string) {
    setRows((current) => current.map((row, index) => index === rowIndex ? { ...row, [field]: value } : row));
  }

  function focusNext(rowIndex: number, field: keyof EditableTableRow) {
    const fieldIndex = TABLE_FIELDS.indexOf(field);
    const next = fieldIndex === TABLE_FIELDS.length - 1
      ? document.querySelector<HTMLInputElement>(`[data-table-cell="${rowIndex + 1}-${TABLE_FIELDS[0]}"]`)
      : document.querySelector<HTMLInputElement>(`[data-table-cell="${rowIndex}-${TABLE_FIELDS[fieldIndex + 1]}"]`);
    if (next) next.focus();
    else if (fieldIndex === TABLE_FIELDS.length - 1) setRows((current) => [...current, emptyTableRow()]);
  }

  function saveRows() {
    const holdings: HoldingInput[] = rows
      .filter((row) => row.ticker.trim() || row.name.trim())
      .map((row) => {
        const number = (value: string) => value.trim() ? Number(value.replace(/,/g, "")) : undefined;
        return {
          ticker: row.ticker.trim() || row.name.trim(),
          name: row.name.trim() || undefined,
          shares: number(row.shares),
          avg_cost: number(row.buy_price),
          buy_price: number(row.buy_price),
          buy_date: row.buy_date.trim() || undefined,
          current_price: number(row.current_price),
          sell_price: number(row.sell_price),
          sell_date: row.sell_date.trim() || undefined,
          current_value: number(row.sell_price) ?? (number(row.current_price) !== undefined && number(row.shares) !== undefined ? number(row.current_price)! * number(row.shares)! : undefined),
          category: row.category.trim() || undefined,
          notes: row.notes.trim() || undefined,
        };
      });
    if (holdings.length === 0 || holdings.some((holding) => !holding.ticker || !holding.shares || holding.shares <= 0)) {
      setSaveError(isChinese ? "請至少輸入股票代號／名稱與大於 0 的股數。" : "Enter a ticker or name and shares greater than 0 for each row.");
      return;
    }
    setSaveError(null);
    void onSave(holdings).catch((error) => {
      setSaveError(
        error instanceof Error
          ? error.message
          : isChinese
            ? "儲存失敗，請確認 backend 正在運作。"
            : "Save failed. Please check that the backend is running.",
      );
    });
  }

  async function importFile(file: File | null) {
    if (!file) return;
    setImportStatus(isChinese ? "正在讀取檔案..." : "Reading file...");
    setSaveError(null);
    try {
      const preview = await previewPortfolioImport(file);
      if (preview.holdings.length > 0) {
        setRows(preview.holdings.map(holdingToTableRow));
      }
      const issueCount = preview.errors.length + preview.warnings.length;
      setImportStatus(
        isChinese
          ? `已匯入 ${preview.holdings.length} 筆${issueCount ? `；${issueCount} 筆需要檢查` : ""}`
          : `Imported ${preview.holdings.length} rows${issueCount ? `; ${issueCount} need review` : ""}`,
      );
    } catch (error) {
      setImportStatus(null);
      setSaveError(error instanceof Error ? error.message : isChinese ? "檔案匯入失敗。" : "File import failed.");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal="true" aria-label={isChinese ? "編輯投資組合" : "Edit portfolio"}>
      <div className="flex max-h-[90vh] w-full max-w-7xl flex-col rounded-3xl border border-white/15 bg-[#151310] shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-white/10 p-5 sm:p-6">
          <div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">Portfolio editor</p><h2 className="mt-2 text-2xl font-semibold">{isChinese ? "編輯投資組合" : "Edit portfolio"}</h2><p className="mt-2 text-sm text-zinc-400">{isChinese ? "一次輸入多筆持股；按 Enter 可移到下一格。" : "Add multiple positions at once; press Enter to move to the next cell."}</p><label className="mt-4 inline-flex cursor-pointer items-center rounded-xl border border-dashed border-amber-200/35 px-3 py-2 text-sm text-amber-100 hover:bg-amber-200/10"><span>{isChinese ? "上傳 CSV / XLSX" : "Upload CSV / XLSX"}</span><input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="hidden" onChange={(event) => void importFile(event.target.files?.[0] ?? null)} /></label>{importStatus ? <span className="ml-3 text-xs text-zinc-400">{importStatus}</span> : null}</div>
          <button type="button" onClick={onClose} className="rounded-full border border-white/10 px-3 py-1 text-sm text-zinc-300 hover:text-white">×</button>
        </div>
        <div className="overflow-auto p-5 sm:p-6"><table className="min-w-[1180px] w-full text-left text-xs"><thead className="sticky top-0 bg-[#151310] text-zinc-500"><tr>{TABLE_FIELDS.map((field) => <th key={field} className="px-2 py-2 font-medium">{TABLE_LABELS[field]}</th>)}<th className="px-2 py-2"> </th></tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex} className="border-t border-white/10">{TABLE_FIELDS.map((field) => <td key={field} className="p-1"><input data-table-cell={`${rowIndex}-${field}`} type={field.endsWith("date") ? "date" : "text"} value={row[field]} onChange={(event) => updateCell(rowIndex, field, event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); focusNext(rowIndex, field); } }} className="w-full rounded-lg border border-white/10 bg-black/25 px-2 py-2 text-zinc-100 outline-none focus:border-amber-200/50" /></td>)}<td className="p-1"><button type="button" onClick={() => setRows((current) => current.filter((_, index) => index !== rowIndex))} className="rounded-lg px-2 py-2 text-rose-300 hover:bg-rose-400/10">×</button></td></tr>)}</tbody></table><button type="button" onClick={() => setRows((current) => [...current, emptyTableRow()])} className="mt-4 rounded-xl border border-dashed border-white/20 px-4 py-2 text-sm text-zinc-300 hover:border-amber-200/40 hover:text-amber-100">＋ {isChinese ? "新增一列" : "Add row"}</button>{saveError ? <p className="mt-4 rounded-xl border border-rose-300/25 bg-rose-400/10 p-3 text-sm text-rose-200">{saveError}</p> : null}</div>
        <div className="flex justify-end gap-3 border-t border-white/10 p-5 sm:p-6"><button type="button" onClick={onClose} className="rounded-xl border border-white/10 px-4 py-2 text-sm text-zinc-300">{isChinese ? "取消" : "Cancel"}</button><button type="button" onClick={saveRows} className="rounded-xl bg-white px-5 py-2 text-sm font-semibold text-black hover:bg-amber-100">{isChinese ? "儲存投資組合" : "Save portfolio"}</button></div>
      </div>
    </div>
  );
}

function ChatAvatar({ role }: { role: PortfolioChatMessage["role"] }) {
  const isUser = role === "user";
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
        isUser
          ? "bg-white text-zinc-950"
          : "border border-amber-200/35 bg-amber-200/10 text-amber-100"
      }`}
    >
      {isUser ? "You" : "AI"}
    </div>
  );
}

function ChatBubble({ message }: { message: PortfolioChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? <ChatAvatar role={message.role} /> : null}
      <div
        className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
          isUser
            ? "rounded-br-md bg-white text-zinc-950"
            : "rounded-bl-md border border-white/10 bg-[#171512] text-zinc-200"
        }`}
      >
        <MarkdownMessage body={message.body} />
      </div>
      {isUser ? <ChatAvatar role={message.role} /> : null}
    </div>
  );
}

function renderInlineMarkdown(value: string): ReactNode[] {
  return value.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`} className="font-semibold text-amber-100">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`} className="rounded bg-white/10 px-1.5 py-0.5 text-[0.9em] text-cyan-200">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={`${part}-${index}`}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function MarkdownMessage({ body }: { body: string }) {
  const lines = body.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const orderedItems: string[] = [];
    while (index < lines.length) {
      const match = lines[index].match(/^\s*\d+[.)]\s+(.+)$/);
      if (!match && !lines[index].trim() && lines[index + 1]?.match(/^\s*\d+[.)]\s+(.+)$/)) {
        index += 1;
        continue;
      }
      if (!match) break;
      orderedItems.push(match[1]);
      index += 1;
    }
    if (orderedItems.length > 0) {
      blocks.push(
        <ol key={`ordered-${index}`} className="my-2 list-decimal space-y-1 pl-5 marker:text-amber-200/70">
          {orderedItems.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{renderInlineMarkdown(item)}</li>)}
        </ol>,
      );
      continue;
    }

    const bulletItems: string[] = [];
    while (index < lines.length) {
      const match = lines[index].match(/^\s*[-*]\s+(.+)$/);
      if (!match && !lines[index].trim() && lines[index + 1]?.match(/^\s*[-*]\s+(.+)$/)) {
        index += 1;
        continue;
      }
      if (!match) break;
      bulletItems.push(match[1]);
      index += 1;
    }
    if (bulletItems.length > 0) {
      blocks.push(
        <ul key={`bullets-${index}`} className="my-2 list-disc space-y-1 pl-5 marker:text-amber-200/70">
          {bulletItems.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{renderInlineMarkdown(item)}</li>)}
        </ul>,
      );
      continue;
    }

    if (line.startsWith("### ") || line.startsWith("## ") || line.startsWith("# ")) {
      const heading = line.replace(/^###?\s+|^#\s+/, "");
      blocks.push(<p key={`heading-${index}`} className="mt-3 font-semibold text-amber-100">{renderInlineMarkdown(heading)}</p>);
      index += 1;
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !/^\s*\d+[.)]\s+/.test(lines[index]) && !/^\s*[-*]\s+/.test(lines[index]) && !/^#{1,3}\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(<p key={`paragraph-${index}`} className="my-2">{paragraph.map((item, itemIndex) => <span key={`${item}-${itemIndex}`}>{item}{itemIndex < paragraph.length - 1 ? <br /> : null}</span>)}</p>);
  }

  return <div className="[&>p:first-child]:mt-0 [&>p:last-child]:mb-0">{blocks}</div>;
}

function ThinkingBubble({ isChinese }: { isChinese: boolean }) {
  const steps = isChinese
    ? ["讀取投資組合記憶", "檢查現價覆蓋率", "整理回答"]
    : ["Reading portfolio memory", "Checking price coverage", "Preparing answer"];

  return (
    <div className="flex justify-start gap-3">
      <ChatAvatar role="assistant" />
      <div className="max-w-[82%] rounded-2xl rounded-bl-md border border-amber-200/20 bg-amber-200/10 px-4 py-3 text-sm text-amber-50 shadow-sm">
        <div className="flex items-center gap-3 font-medium">
          <span>{isChinese ? "正在思考" : "Thinking"}</span>
          <ThinkingDots />
        </div>
        <div className="mt-3 space-y-1.5 text-xs leading-5 text-amber-50/75">
          {steps.map((step) => (
            <div key={step} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-200/70" />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PortfolioChatLoadingShell() {
  return (
    <main className="min-h-screen bg-[#0d0c0a] px-4 py-6 text-white sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col gap-5">
        <header className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <div className="h-3 w-32 rounded-full bg-white/10" />
            <div className="h-10 w-64 max-w-full rounded-full bg-white/10" />
            <div className="h-4 w-80 max-w-full rounded-full bg-white/10" />
          </div>
          <div className="h-16 w-52 rounded-lg border border-white/10 bg-black/25" />
        </header>
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <div className="min-h-[34rem] rounded-2xl border border-white/10 bg-zinc-950/65 p-4">
            <div className="space-y-4">
              <div className="h-4 w-40 rounded-full bg-white/10" />
              <div className="h-20 rounded-lg bg-white/5" />
              <div className="h-20 rounded-lg bg-white/5" />
              <div className="h-24 rounded-lg bg-white/5" />
            </div>
          </div>
          <aside className="space-y-4">
            <div className="h-32 rounded-2xl border border-white/10 bg-zinc-950/65" />
            <div className="h-40 rounded-2xl border border-white/10 bg-zinc-950/65" />
          </aside>
        </section>
      </div>
    </main>
  );
}

export function PortfolioChatMvp({
  copy,
  state,
  messages,
  inputValue,
  pendingHoldings,
  savedHoldings,
  analysis,
  wizardStep,
  lastUpdated,
  loading,
  error,
  chatResponse,
  starterPrompts,
  onInputChange,
  onSubmit,
  onSavePending,
  onEditPending,
  onAddAnotherHolding,
  onSaveTable,
  onStartOver,
  onReplacePortfolio,
  onUsePrompt,
}: Props) {
  const hasSavedPortfolio = savedHoldings.length > 0;
  const canSubmit = inputValue.trim().length > 0 && !loading;
  const isChinese = copy.portfolioCopilotTitle === "投資組合助手";
  const holdingFormatter = isChinese ? formatHoldingZh : formatHolding;
  const [editorMode, setEditorMode] = useState<"new" | "edit" | null>(null);
  const wizardPlaceholder = wizardStep
    ? isChinese
      ? "請在這裡輸入上一個問題的答案..."
      : "Enter your answer to the question above..."
    : hasSavedPortfolio
      ? copy.askAboutPortfolioPlaceholder
      : copy.holdingsOnboardingPlaceholder;

  return (
    <main className="min-h-screen bg-[#0d0c0a] px-4 py-6 text-white sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col gap-5">
        <header className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/copilot?mode=research"
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-zinc-300 transition hover:border-amber-200/40 hover:text-amber-100"
              >
                {isChinese ? "← 研究模式" : "← Research Mode"}
              </Link>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-amber-200/60">
                {copy.eyebrow}
              </p>
            </div>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">
              {copy.portfolioCopilotTitle}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">
              {copy.portfolioCopilotSubtitle}
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 sm:items-end">
            <LanguageToggle />
            <div className="rounded-lg border border-white/10 bg-black/25 px-4 py-3">
              <div className="text-xs uppercase tracking-[0.14em] text-zinc-500">
                {hasSavedPortfolio ? copy.savedPortfolio : copy.noPortfolioSavedYet}
              </div>
              <div className="mt-1 text-sm font-medium text-zinc-100">
                {hasSavedPortfolio
                  ? `${savedHoldings.length} ${copy.holdingsCount}`
                  : copy.tellMeAboutYourHoldings}
              </div>
              {lastUpdated ? (
                <div className="mt-1 text-xs text-zinc-500">
                  {copy.lastUpdated}: {lastUpdated}
                </div>
              ) : null}
            </div>
            <button type="button" onClick={() => setEditorMode("new")} className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-black hover:bg-amber-100">
              {isChinese ? "新增投資組合" : "New portfolio"}
            </button>
          </div>
        </header>

        <div className="space-y-5">
          <PortfolioOverview copy={copy} analysis={analysis} hasSavedPortfolio={hasSavedPortfolio} />
          <PortfolioVisualizations copy={copy} analysis={analysis} />
          <HoldingsTable copy={copy} analysis={analysis} />
        </div>

        <section id="portfolio-chat" className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <div className="flex min-h-[34rem] flex-col overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/70 shadow-2xl shadow-black/25">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-black/20 px-4 py-3">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.7)]" />
                  <span>{copy.portfolioMemoryStatus}</span>
                </div>
                <div className="mt-0.5 text-xs text-zinc-500">
                  {hasSavedPortfolio
                    ? copy.portfolioMemoryReady
                    : copy.noPortfolioSavedYet}
                </div>
              </div>
              <span className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-zinc-200">
                {state.replaceAll("_", " ")}
              </span>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent)] px-4 py-5">
              {messages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}

              {!hasSavedPortfolio && !wizardStep && state !== "CONFIRM_HOLDINGS" ? (
                <div className="ml-11 max-w-md rounded-2xl border border-amber-200/20 bg-amber-200/[0.06] p-4 shadow-sm">
                  <p className="text-sm leading-6 text-zinc-300">
                    {isChinese
                      ? "你可以直接輸入持股，也可以一次上傳 CSV／XLSX。"
                      : "Enter a holding here, or upload a CSV/XLSX file to add several positions at once."}
                  </p>
                  <button
                    type="button"
                    onClick={() => setEditorMode("new")}
                    disabled={loading}
                    className="mt-3 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                  >
                    {isChinese ? "＋ 新增持股" : "+ Add holdings"}
                  </button>
                </div>
              ) : null}

              {loading ? <ThinkingBubble isChinese={isChinese} /> : null}

              {state === "CONFIRM_HOLDINGS" ? (
                <div className="ml-11 rounded-2xl border border-amber-300/25 bg-amber-300/5 p-4 shadow-sm">
                  <div className="text-sm font-semibold text-amber-100">
                    {copy.confirmHoldingsTitle}
                  </div>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-50/90">
                    {pendingHoldings.map((holding) => (
                      <li key={`${holding.ticker}-${holding.shares}`}>
                        {holdingFormatter(holding)}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      onClick={onSavePending}
                      disabled={loading}
                      className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50"
                    >
                      {copy.savePortfolioMemory}
                    </button>
                    <button
                      type="button"
                      onClick={onEditPending}
                      disabled={loading}
                      className="rounded-lg border border-white/10 bg-black/25 px-4 py-2 text-sm text-zinc-200 transition hover:border-white/20"
                    >
                      {copy.editPortfolio}
                    </button>
                    <button
                      type="button"
                      onClick={onAddAnotherHolding}
                      disabled={loading}
                      className="rounded-lg border border-amber-200/25 bg-amber-200/10 px-4 py-2 text-sm text-amber-100 transition hover:border-amber-200/50"
                    >
                      {isChinese ? "新增另一筆持股" : "Add another holding"}
                    </button>
                    <button
                      type="button"
                      onClick={onStartOver}
                      disabled={loading}
                      className="rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-400 transition hover:border-white/20 hover:text-zinc-100"
                    >
                      {copy.startOver}
                    </button>
                  </div>
                </div>
              ) : null}

              {chatResponse ? (
                <details className="ml-11 rounded-2xl border border-white/10 bg-black/25 p-4">
                  <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
                    {copy.portfolioChatEvidenceUsed}
                  </summary>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {chatResponse.evidence_used.map((item) => (
                      <span
                        key={item}
                        className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-zinc-200"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>

            {error ? (
              <div className="mx-4 mb-3 rounded-2xl border border-rose-300/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}

            <div className="border-t border-white/10 bg-black/25 p-4">
              <div className="mb-3 flex flex-wrap gap-2">
                {starterPrompts.slice(0, 3).map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => onUsePrompt(prompt)}
                    disabled={loading}
                    className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-left text-xs leading-5 text-zinc-300 transition hover:border-amber-200/35 hover:text-amber-100 disabled:opacity-50"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
              <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-zinc-950/80 p-2 shadow-inner shadow-black/30 sm:flex-row sm:items-end">
                <textarea
                  value={inputValue}
                  onChange={(event) => onInputChange(event.target.value)}
                  rows={2}
                  placeholder={wizardPlaceholder}
                  className="min-h-16 flex-1 resize-y rounded-xl border border-transparent bg-transparent px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/30"
                />
                <button
                  type="button"
                  onClick={onSubmit}
                  disabled={!canSubmit}
                  className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50 sm:w-36"
                >
                  {loading ? (
                    <span className="inline-flex items-center justify-center gap-2">
                      <ThinkingDots />
                    </span>
                  ) : wizardStep ? (
                    copy.continueCta
                  ) : hasSavedPortfolio ? (
                    copy.askAboutMyPortfolio
                  ) : (
                    copy.continueCta
                  )}
                </button>
              </div>
              <p className="mt-3 text-xs leading-5 text-zinc-500">
                {copy.portfolioChatSafety}: {copy.educationalPortfolioReview}
              </p>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="rounded-lg border border-white/10 bg-zinc-950/65 p-4">
              <div className="text-sm font-semibold text-zinc-100">
                {copy.compactControls}
              </div>
              <div className="mt-3 space-y-2">
                <details className="rounded-lg border border-white/10 bg-black/25 p-3">
                  <summary className="cursor-pointer text-sm text-zinc-200">
                    {copy.viewSavedHoldings}
                  </summary>
                  <ul className="mt-3 space-y-2 text-xs leading-5 text-zinc-400">
                    {savedHoldings.length > 0 ? (
                      savedHoldings.map((holding) => (
                        <li key={`${holding.ticker}-${holding.shares}`}>
                          {holdingFormatter(holding)}
                        </li>
                      ))
                    ) : (
                      <li>{copy.noPortfolioSavedYet}</li>
                    )}
                  </ul>
                </details>
                <button
                  type="button"
                  onClick={() => setEditorMode("edit")}
                  className="w-full rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-left text-sm text-zinc-200 transition hover:border-white/20"
                >
                  {copy.editPortfolio}
                </button>
                <button
                  type="button"
                  onClick={onReplacePortfolio}
                  className="w-full rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-left text-sm text-zinc-200 transition hover:border-white/20"
                >
                  {copy.replacePortfolio}
                </button>
              </div>
            </div>

            {hasSavedPortfolio ? (
              <div className="rounded-lg border border-white/10 bg-zinc-950/65 p-4">
                <div className="text-sm font-semibold text-zinc-100">
                  {copy.starterPrompts}
                </div>
                <div className="mt-3 space-y-2">
                  {starterPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => onUsePrompt(prompt)}
                      className="w-full rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-left text-sm leading-5 text-zinc-200 transition hover:border-white/20"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </aside>
        </section>
      </div>
      {editorMode ? (
        <HoldingsEditorModal
          initialHoldings={editorMode === "edit" ? savedHoldings : []}
          isChinese={isChinese}
          onClose={() => setEditorMode(null)}
          onSave={async (holdings) => {
            await onSaveTable(holdings);
            setEditorMode(null);
          }}
        />
      ) : null}
    </main>
  );
}
