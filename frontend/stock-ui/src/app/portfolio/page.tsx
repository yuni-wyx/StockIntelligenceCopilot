"use client";

import { useEffect, useMemo, useState } from "react";
import {
  PortfolioChatMvp,
  PortfolioChatLoadingShell,
  type PortfolioChatMessage,
  type PortfolioChatMvpState,
} from "@/components/wealth-studio/PortfolioChatMvp";
import { parsePortfolioHoldingsText } from "@/components/wealth-studio/portfolioChatParser";
import { useLanguage } from "@/context/LanguageContext";
import {
  askAboutPortfolio,
  deleteCurrentPortfolio,
  loadCurrentPortfolio,
  savePortfolio,
  type HoldingInput,
  type PortfolioChatResponse,
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
  }, [hydrated, ws]);

  function resetChatResults() {
    setChatResponse(null);
    setError(null);
  }

  function appendMessages(nextMessages: PortfolioChatMessage[]) {
    setMessages((prev) => [...prev, ...nextMessages]);
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
              `${holding.name || holding.ticker}: ${holding.shares?.toLocaleString()} ${ws.shares}, ${ws.avgCost} ${holding.avg_cost?.toLocaleString()}`,
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

  function handleEditPending() {
    const source = pendingHoldings.length > 0 ? pendingHoldings : savedHoldings;
    setInputValue(
      source
        .map(
          (holding) =>
            `${holding.name || holding.ticker} ${holding.shares ?? ""} ${ws.shares} ${ws.avgCost} ${holding.avg_cost ?? ""}`,
        )
        .join("；"),
    );
    setPendingHoldings([]);
    setState("ASK_HOLDINGS");
    resetChatResults();
  }

  function handleStartOver() {
    setInputValue("");
    setPendingHoldings([]);
    setState(savedHoldings.length > 0 ? "CHAT_READY" : "ASK_HOLDINGS");
    resetChatResults();
    appendMessages([makeMessage("assistant", ws.portfolioOnboardingQuestion)]);
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
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      chatResponse={chatResponse}
      starterPrompts={starterPrompts}
      onInputChange={setInputValue}
      onSubmit={handleSubmit}
      onSavePending={() => void handleSavePending()}
      onEditPending={handleEditPending}
      onStartOver={handleStartOver}
      onReplacePortfolio={() => void handleReplacePortfolio()}
      onUsePrompt={handleUsePrompt}
    />
  );
}
