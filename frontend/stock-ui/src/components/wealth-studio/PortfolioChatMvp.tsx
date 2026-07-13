"use client";

import Link from "next/link";
import { LanguageToggle } from "@/components/LanguageToggle";
import type { HoldingInput, PortfolioChatResponse } from "@/lib/portfolioApi";
import type { WealthStudioCopy } from "@/i18n/messages";

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
  lastUpdated?: string | null;
  loading: boolean;
  error?: string | null;
  chatResponse?: PortfolioChatResponse | null;
  starterPrompts: string[];
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onSavePending: () => void;
  onEditPending: () => void;
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
          <div className="min-h-[34rem] rounded-lg border border-white/10 bg-zinc-950/65 p-4">
            <div className="space-y-4">
              <div className="h-4 w-40 rounded-full bg-white/10" />
              <div className="h-20 rounded-lg bg-white/5" />
              <div className="h-20 rounded-lg bg-white/5" />
              <div className="h-24 rounded-lg bg-white/5" />
            </div>
          </div>
          <aside className="space-y-4">
            <div className="h-32 rounded-lg border border-white/10 bg-zinc-950/65" />
            <div className="h-40 rounded-lg border border-white/10 bg-zinc-950/65" />
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
  lastUpdated,
  loading,
  error,
  chatResponse,
  starterPrompts,
  onInputChange,
  onSubmit,
  onSavePending,
  onEditPending,
  onStartOver,
  onReplacePortfolio,
  onUsePrompt,
}: Props) {
  const hasSavedPortfolio = savedHoldings.length > 0;
  const canSubmit = inputValue.trim().length > 0 && !loading;
  const isChinese = copy.portfolioCopilotTitle === "投資組合助手";
  const holdingFormatter = isChinese ? formatHoldingZh : formatHolding;

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
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <div className="flex min-h-[34rem] flex-col rounded-lg border border-white/10 bg-zinc-950/65">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-zinc-100">
                  {copy.portfolioMemoryStatus}
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

            <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] whitespace-pre-line rounded-lg px-4 py-3 text-sm leading-6 ${
                      message.role === "user"
                        ? "bg-white text-black"
                        : "border border-white/10 bg-black/30 text-zinc-200"
                    }`}
                  >
                    {message.body}
                  </div>
                </div>
              ))}

              {state === "CONFIRM_HOLDINGS" ? (
                <div className="rounded-lg border border-amber-300/25 bg-amber-300/5 p-4">
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
                <details className="rounded-lg border border-white/10 bg-black/25 p-4">
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
              <div className="mx-4 mb-3 rounded-lg border border-rose-300/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}

            <div className="border-t border-white/10 p-4">
              <div className="flex flex-col gap-3 sm:flex-row">
                <textarea
                  value={inputValue}
                  onChange={(event) => onInputChange(event.target.value)}
                  rows={3}
                  placeholder={
                    hasSavedPortfolio
                      ? copy.askAboutPortfolioPlaceholder
                      : copy.holdingsOnboardingPlaceholder
                  }
                  className="min-h-24 flex-1 resize-y rounded-lg border border-white/10 bg-black/45 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-amber-200/50"
                />
                <button
                  type="button"
                  onClick={onSubmit}
                  disabled={!canSubmit}
                  className="rounded-lg bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-100 disabled:opacity-50 sm:w-36"
                >
                  {loading ? copy.working : hasSavedPortfolio ? copy.askAboutMyPortfolio : copy.continueCta}
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
                  onClick={onEditPending}
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
    </main>
  );
}
