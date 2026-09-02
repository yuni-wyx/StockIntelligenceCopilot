"use client";

import { useEffect, useMemo, useState } from "react";
import {
  PortfolioChatMvp,
  PortfolioChatLoadingShell,
  type PortfolioChatMessage,
  type PortfolioChatMvpState,
} from "@/components/wealth-studio/PortfolioChatMvp";
import { parsePortfolioHoldingsText } from "@/components/wealth-studio/portfolioChatParser";
import { normalizeTicker } from "@/lib/tickerMap";
import { useLanguage } from "@/context/LanguageContext";
import {
  askAboutPortfolio,
  analyzePortfolio,
  deleteCurrentPortfolio,
  loadCurrentPortfolio,
  savePortfolio,
  type HoldingInput,
  type PortfolioChatResponse,
  type PortfolioAnalysisResponse,
} from "@/lib/portfolioApi";

function makeMessage(role: "assistant" | "user", body: string): PortfolioChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    body,
  };
}

function formatUpdatedAt(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
}

type HoldingWizardStep =
  | "ticker"
  | "shares"
  | "buy_price"
  | "buy_date"
  | "sell_decision"
  | "sell_price"
  | "sell_date";

export default function PortfolioPage() {
  const { hydrated, t, locale } = useLanguage();
  const ws = t.wealthStudio;
  const [state, setState] = useState<PortfolioChatMvpState>("NO_PORTFOLIO");
  const [messages, setMessages] = useState<PortfolioChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [pendingHoldings, setPendingHoldings] = useState<HoldingInput[]>([]);
  const [savedHoldings, setSavedHoldings] = useState<HoldingInput[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [chatResponse, setChatResponse] = useState<PortfolioChatResponse | null>(null);
  const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wizardStep, setWizardStep] = useState<HoldingWizardStep | null>(null);
  const [wizardHolding, setWizardHolding] = useState<HoldingInput>({ ticker: "" });

  const starterPrompts = useMemo(
    () => [
      ws.portfolioChatStarterConcentration,
      ws.portfolioChatStarterReview,
      ws.portfolioChatStarterTech,
      ws.portfolioChatStarterIncome,
    ],
    [ws],
  );

  useEffect(() => {
    if (!hydrated) return;

    let cancelled = false;

    async function loadPortfolioMemory() {
      setLoading(true);
      setError(null);
      try {
        const record = await loadCurrentPortfolio();
        if (cancelled) return;
        const portfolio = record.portfolio;
        const holdings = Array.isArray(portfolio?.holdings) ? portfolio.holdings : [];

        if (holdings.length > 0) {
          setSavedHoldings(holdings);
          setLastUpdated(formatUpdatedAt(record.updated_at));
          setState("CHAT_READY");
          void refreshAnalysis(holdings);
          setMessages([
            makeMessage("assistant", ws.portfolioMemoryLoadedMessage),
          ]);
        } else {
          setState("ASK_HOLDINGS");
          setMessages([
            makeMessage("assistant", ws.portfolioOnboardingQuestion),
          ]);
        }
      } catch {
        if (cancelled) return;
        setState("ASK_HOLDINGS");
        setMessages([
          makeMessage("assistant", ws.portfolioOnboardingQuestion),
        ]);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadPortfolioMemory();
    return () => {
      cancelled = true;
    };
    // refreshAnalysis is a stable module-backed operation; ws already gates this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, ws]);

  function resetChatResults() {
    setChatResponse(null);
    setError(null);
  }

  async function refreshAnalysis(holdings: HoldingInput[]) {
    if (holdings.length === 0) {
      setAnalysis(null);
      return;
    }
    try {
      const response = await analyzePortfolio(buildPortfolioPayload(holdings));
      setAnalysis(response);
    } catch {
      setAnalysis(null);
    }
  }

  function appendMessages(nextMessages: PortfolioChatMessage[]) {
    setMessages((prev) => [...prev, ...nextMessages]);
  }

  function startHoldingWizard({ preserveHoldings = false } = {}) {
    const firstQuestion = makeMessage(
      "assistant",
      locale === "zh"
        ? "好，我們一筆一筆建立持股。請先輸入股票代號或名稱。"
        : "Let’s build one position at a time. What is the stock ticker or name?",
    );
    setWizardHolding({ ticker: "" });
    setWizardStep("ticker");
    setInputValue("");
    if (preserveHoldings) {
      appendMessages([firstQuestion]);
    } else {
      setMessages([firstQuestion]);
    }
    resetChatResults();
  }

  function parseWizardNumber(value: string): number | null {
    const match = value.replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
    if (!match) return null;
    const number = Number(match[0]);
    return Number.isFinite(number) ? number : null;
  }

  function validDate(value: string): string | null {
    const trimmed = value.trim();
    const date = new Date(trimmed);
    return trimmed && !Number.isNaN(date.getTime()) ? trimmed : null;
  }

  function wizardQuestion(step: HoldingWizardStep): string {
    if (locale === "zh") {
      return {
        ticker: "請輸入股票代號或名稱。",
        shares: "請問持有幾股？",
        buy_price: "當時買進價格是多少？",
        buy_date: "買入日期是哪一天？（例如 2025-03-01）",
        sell_decision: "這筆持股已經賣出了嗎？請回答「是」或「否」。",
        sell_price: "賣出價格是多少？",
        sell_date: "賣出日期是哪一天？（例如 2026-08-31）",
      }[step];
    }
    return {
      ticker: "What is the stock ticker or name?",
      shares: "How many shares do you hold?",
      buy_price: "What price did you buy it at?",
      buy_date: "What was the buy date? (For example, 2025-03-01)",
      sell_decision: "Have you sold this position? Please answer yes or no.",
      sell_price: "What was the sell price?",
      sell_date: "What was the sell date? (For example, 2026-08-31)",
    }[step];
  }

  function finishWizard(holding: HoldingInput) {
    const buyPrice = holding.buy_price ?? holding.avg_cost;
    const sellPrice = holding.sell_price;
    const enrichedHolding: HoldingInput = {
      ...holding,
      avg_cost: buyPrice,
      current_price: sellPrice,
      current_value: sellPrice !== undefined && holding.shares !== undefined ? sellPrice * holding.shares : undefined,
    };
    const profit = buyPrice !== undefined && sellPrice !== undefined && holding.shares !== undefined
      ? (sellPrice - buyPrice) * holding.shares
      : null;
    const holdingDays = holding.buy_date && holding.sell_date
      ? Math.max(0, Math.round((new Date(holding.sell_date).getTime() - new Date(holding.buy_date).getTime()) / 86400000))
      : null;
    const profitText = profit === null
      ? (locale === "zh" ? "尚未賣出，利潤仍未實現。" : "This position has not been sold, so profit is not realized yet.")
      : locale === "zh"
        ? `已實現利潤：${profit.toLocaleString()}；持有 ${holdingDays ?? "—"} 天。`
        : `Realized profit: ${profit.toLocaleString()}; held for ${holdingDays ?? "—"} days.`;
    setWizardHolding(enrichedHolding);
    setPendingHoldings((previous) => [...previous, enrichedHolding]);
    setWizardStep(null);
    setState("CONFIRM_HOLDINGS");
    appendMessages([
      makeMessage(
        "assistant",
        `${locale === "zh" ? "已整理完成：" : "Position captured:"} ${enrichedHolding.name || enrichedHolding.ticker}, ${enrichedHolding.shares} ${locale === "zh" ? "股" : "shares"}, ${locale === "zh" ? "買進" : "bought at"} ${buyPrice ?? "—"}. ${profitText}`,
      ),
    ]);
  }

  function handleWizardSubmit() {
    if (!wizardStep || !inputValue.trim()) return;
    const answer = inputValue.trim();
    appendMessages([makeMessage("user", answer)]);
    setInputValue("");

    if (wizardStep === "ticker") {
      const ticker = normalizeTicker(answer);
      const holding = { ...wizardHolding, ticker, name: answer };
      setWizardHolding(holding);
      setWizardStep("shares");
      appendMessages([makeMessage("assistant", wizardQuestion("shares"))]);
      return;
    }
    if (wizardStep === "shares" || wizardStep === "buy_price" || wizardStep === "sell_price") {
      const number = parseWizardNumber(answer);
      if (number === null || number <= 0) {
        appendMessages([makeMessage("assistant", locale === "zh" ? "請輸入大於 0 的數字。" : "Please enter a number greater than 0.")]);
        return;
      }
      const field = wizardStep === "shares" ? "shares" : wizardStep;
      const holding = {
        ...wizardHolding,
        [field]: number,
        ...(wizardStep === "buy_price" ? { avg_cost: number } : {}),
      };
      const nextStep = wizardStep === "shares" ? "buy_price" : wizardStep === "buy_price" ? "buy_date" : "sell_date";
      setWizardHolding(holding);
      setWizardStep(nextStep);
      appendMessages([makeMessage("assistant", wizardQuestion(nextStep))]);
      return;
    }
    if (wizardStep === "buy_date" || wizardStep === "sell_date") {
      const date = validDate(answer);
      if (!date) {
        appendMessages([makeMessage("assistant", locale === "zh" ? "日期格式看起來不正確，請用 YYYY-MM-DD。" : "That date is not valid. Please use YYYY-MM-DD.")]);
        return;
      }
      const holding = { ...wizardHolding, [wizardStep]: date };
      const nextStep = wizardStep === "buy_date" ? "sell_decision" : null;
      setWizardHolding(holding);
      if (nextStep) {
        setWizardStep(nextStep);
        appendMessages([makeMessage("assistant", wizardQuestion(nextStep))]);
      } else {
        finishWizard(holding);
      }
      return;
    }
    const sold = /^(是|有|已|yes|y|sold)$/i.test(answer);
    if (sold) {
      setWizardStep("sell_price");
      appendMessages([makeMessage("assistant", wizardQuestion("sell_price"))]);
    } else if (/^(否|沒有|未|no|n|not yet)$/i.test(answer)) {
      finishWizard(wizardHolding);
    } else {
      appendMessages([makeMessage("assistant", wizardQuestion("sell_decision"))]);
    }
  }

  function buildPortfolioPayload(holdings: HoldingInput[]) {
    return {
      holdings,
      risk_profile: "Balanced",
      goal: ws.portfolioCopilotGoal,
      base_currency: "TWD",
    };
  }

  function handleParseHoldings() {
    const parsed = parsePortfolioHoldingsText(
      inputValue,
      ws.holdingsParsePartialWarning,
    );
    appendMessages([makeMessage("user", inputValue)]);
    setInputValue("");
    resetChatResults();

    if (parsed.holdings.length === 0) {
      appendMessages([makeMessage("assistant", ws.holdingsParseFailed)]);
      setState("ASK_HOLDINGS");
      return;
    }

    setPendingHoldings(parsed.holdings);
    setState("CONFIRM_HOLDINGS");
    appendMessages([
      makeMessage(
        "assistant",
        [
          ws.holdingsParsedIntro,
          ...parsed.holdings.map(
            (holding) =>
              `${holding.name || holding.ticker}: ${holding.shares?.toLocaleString()} ${ws.shares}, ${ws.avgCost} ${holding.avg_cost === undefined ? "—" : holding.avg_cost.toLocaleString()}`,
          ),
          parsed.warnings[0] ?? "",
          ws.holdingsConfirmQuestion,
        ]
          .filter(Boolean)
          .join("\n"),
      ),
    ]);
  }

  async function handleAskQuestion(questionOverride?: string) {
    const question = questionOverride ?? inputValue;
    if (!question.trim()) return;

    appendMessages([makeMessage("user", question)]);
    setInputValue("");
    setLoading(true);
    setError(null);
    setChatResponse(null);

    try {
      const response = await askAboutPortfolio({
        question,
        portfolio: buildPortfolioPayload(savedHoldings),
        language: locale === "zh" ? "zh" : "en",
      });
      setChatResponse(response);
      appendMessages([makeMessage("assistant", response.answer)]);
      setState("CHAT_READY");
    } catch (err) {
      const message = err instanceof Error ? err.message : ws.failedCoach;
      setError(message);
      appendMessages([makeMessage("assistant", ws.portfolioChatFailedSafe)]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit() {
    if (wizardStep) {
      handleWizardSubmit();
      return;
    }
    if (savedHoldings.length > 0 && state !== "ASK_HOLDINGS" && state !== "CONFIRM_HOLDINGS") {
      void handleAskQuestion();
      return;
    }
    handleParseHoldings();
  }

  async function handleSavePending() {
    if (pendingHoldings.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      const portfolio = buildPortfolioPayload(pendingHoldings);
      const record = await savePortfolio({
        portfolio,
        name: "current",
        make_current: true,
      });
      setSavedHoldings(pendingHoldings);
      void refreshAnalysis(pendingHoldings);
      setPendingHoldings([]);
      setLastUpdated(formatUpdatedAt(record.updated_at));
      setState("PORTFOLIO_SAVED");
      setChatResponse(null);
      appendMessages([makeMessage("assistant", ws.portfolioMemorySavedMessage)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedSave);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveTable(holdings: HoldingInput[]) {
    setLoading(true);
    setError(null);
    try {
      const record = await savePortfolio({
        portfolio: buildPortfolioPayload(holdings),
        name: "current",
        make_current: true,
      });
      setSavedHoldings(holdings);
      setPendingHoldings([]);
      setLastUpdated(formatUpdatedAt(record.updated_at));
      setState("PORTFOLIO_SAVED");
      setChatResponse(null);
      void refreshAnalysis(holdings);
      appendMessages([makeMessage("assistant", ws.portfolioMemorySavedMessage)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : ws.failedSave);
      throw err;
    } finally {
      setLoading(false);
    }
  }

  function handleEditPending() {
    setPendingHoldings(savedHoldings);
    startHoldingWizard({ preserveHoldings: savedHoldings.length > 0 });
  }

  function handleAddAnotherHolding() {
    startHoldingWizard({ preserveHoldings: true });
  }

  function handleStartOver() {
    setInputValue("");
    setPendingHoldings([]);
    setWizardHolding({ ticker: "" });
    setWizardStep(null);
    setState(savedHoldings.length > 0 ? "CHAT_READY" : "ASK_HOLDINGS");
    resetChatResults();
    startHoldingWizard();
  }

  async function handleReplacePortfolio() {
    setLoading(true);
    setError(null);
    try {
      await deleteCurrentPortfolio();
    } catch {
      // Replacement can still continue locally even if no current workspace existed.
    } finally {
      setSavedHoldings([]);
      setPendingHoldings([]);
      setLastUpdated(null);
      setChatResponse(null);
      setAnalysis(null);
      setWizardStep(null);
      setWizardHolding({ ticker: "" });
      setInputValue("");
      setState("ASK_HOLDINGS");
      setMessages([makeMessage("assistant", ws.portfolioOnboardingQuestion)]);
      setLoading(false);
    }
  }

  function handleUsePrompt(prompt: string) {
    if (savedHoldings.length === 0) {
      setInputValue(prompt);
      return;
    }
    void handleAskQuestion(prompt);
  }

  if (!hydrated) {
    return <PortfolioChatLoadingShell />;
  }

  return (
    <PortfolioChatMvp
      copy={ws}
      state={state}
      messages={messages}
      inputValue={inputValue}
      pendingHoldings={pendingHoldings}
      savedHoldings={savedHoldings}
      analysis={analysis}
      wizardStep={wizardStep}
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      chatResponse={chatResponse}
      starterPrompts={starterPrompts}
      onInputChange={setInputValue}
      onSubmit={handleSubmit}
      onSavePending={() => void handleSavePending()}
      onEditPending={handleEditPending}
      onAddAnotherHolding={handleAddAnotherHolding}
      onSaveTable={handleSaveTable}
      onStartOver={handleStartOver}
      onReplacePortfolio={() => void handleReplacePortfolio()}
      onUsePrompt={handleUsePrompt}
    />
  );
}
