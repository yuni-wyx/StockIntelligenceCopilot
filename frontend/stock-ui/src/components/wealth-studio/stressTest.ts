import { normalizeTicker } from "@/lib/tickerMap";
import { calculateEditableHoldingMetrics } from "./transforms";
import type {
  EditableHolding,
  StressTestForm,
  StressTestHoldingImpact,
  StressTestPreset,
  StressTestResult,
} from "./types";

export const stressTestPresets: StressTestPreset[] = [
  "broad_market_20",
  "technology_selloff_15",
  "taiwan_market_15",
  "bond_rate_sensitive_10",
  "custom_ticker",
];

type StressTestMessages = {
  stressTestNoValidHoldings: string;
  stressTestCustomTickerRequired: string;
  stressTestShockRequired: string;
  stressTestShockRange: string;
  stressTestBroadMarketExplanation: string;
  stressTestTechnologyExplanation: string;
  stressTestTaiwanExplanation: string;
  stressTestBondExplanation: string;
  stressTestCustomExplanation: string;
  stressTestNoMatchingHoldings: string;
};

type ValidationResult =
  | { ok: true; shockPct: number; customTicker?: string }
  | { ok: false; error: string };

function holdingCurrentValue(holding: EditableHolding): number | undefined {
  return calculateEditableHoldingMetrics(holding).currentValue;
}

function normalizeHoldingText(holding: EditableHolding): string {
  return [
    holding.ticker,
    holding.name,
    holding.asset_type,
    holding.category,
    holding.notes,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isTaiwanHolding(holding: EditableHolding): boolean {
  const ticker = normalizeTicker(holding.ticker);
  return /^[0-9]{4,6}(\.TW)?$/i.test(ticker) || ticker.endsWith(".TW");
}

function hasKeyword(holding: EditableHolding, keywords: string[]): boolean {
  const text = normalizeHoldingText(holding);
  return keywords.some((keyword) => {
    if (/[\u4e00-\u9fff]/.test(keyword)) {
      return text.includes(keyword);
    }

    const regex = new RegExp(`\\b${escapeRegex(keyword)}\\b`, "i");
    return regex.test(text);
  });
}

function isTechnologyHolding(holding: EditableHolding): boolean {
  return hasKeyword(holding, [
    "tech",
    "technology",
    "artificial intelligence",
    "semiconductor",
    "electronics",
    "chip",
    "chips",
    "software",
    "cloud",
    "server",
    "internet",
    "科技",
    "技術",
    "半導體",
    "電子",
    "晶片",
    "伺服器",
    "雲端",
    "人工智慧",
  ]);
}

function isBondRateSensitiveHolding(holding: EditableHolding): boolean {
  return hasKeyword(holding, [
    "bond",
    "bonds",
    "treasury",
    "fixed income",
    "duration",
    "rate",
    "income",
    "債",
    "債券",
    "公債",
    "美債",
    "利率",
  ]);
}

function validateStressTest(
  holdings: EditableHolding[],
  form: StressTestForm,
  messages: StressTestMessages,
): ValidationResult {
  const hasValidHolding = holdings.some((holding) => {
    const currentValue = holdingCurrentValue(holding);
    return holding.ticker.trim() && currentValue !== undefined && currentValue > 0;
  });

  if (!hasValidHolding) {
    return { ok: false, error: messages.stressTestNoValidHoldings };
  }

  if (form.preset !== "custom_ticker") {
    return { ok: true, shockPct: presetShockPct(form.preset) };
  }

  if (!form.customTicker.trim()) {
    return { ok: false, error: messages.stressTestCustomTickerRequired };
  }

  if (!form.customShockPct.trim()) {
    return { ok: false, error: messages.stressTestShockRequired };
  }

  const shockPct = Number(form.customShockPct);
  if (Number.isNaN(shockPct) || shockPct < -100 || shockPct > 100) {
    return { ok: false, error: messages.stressTestShockRange };
  }

  return {
    ok: true,
    shockPct,
    customTicker: normalizeTicker(form.customTicker),
  };
}

function presetShockPct(preset: StressTestPreset): number {
  switch (preset) {
    case "broad_market_20":
      return -20;
    case "technology_selloff_15":
      return -15;
    case "taiwan_market_15":
      return -15;
    case "bond_rate_sensitive_10":
      return -10;
    case "custom_ticker":
      return 0;
  }
}

function matchesPreset(
  holding: EditableHolding,
  preset: StressTestPreset,
  customTicker?: string,
): boolean {
  switch (preset) {
    case "broad_market_20":
      return true;
    case "technology_selloff_15":
      return isTechnologyHolding(holding);
    case "taiwan_market_15":
      return isTaiwanHolding(holding);
    case "bond_rate_sensitive_10":
      return isBondRateSensitiveHolding(holding);
    case "custom_ticker":
      return normalizeTicker(holding.ticker) === customTicker;
  }
}

function buildExplanation(
  preset: StressTestPreset,
  impactedCount: number,
  messages: StressTestMessages,
  customTicker?: string,
): string {
  if (impactedCount === 0) {
    return messages.stressTestNoMatchingHoldings;
  }

  switch (preset) {
    case "broad_market_20":
      return messages.stressTestBroadMarketExplanation;
    case "technology_selloff_15":
      return messages.stressTestTechnologyExplanation;
    case "taiwan_market_15":
      return messages.stressTestTaiwanExplanation;
    case "bond_rate_sensitive_10":
      return messages.stressTestBondExplanation;
    case "custom_ticker":
      return messages.stressTestCustomExplanation.replace("{ticker}", customTicker ?? "");
  }
}

export function runPortfolioStressTest(
  holdings: EditableHolding[],
  form: StressTestForm,
  messages: StressTestMessages,
): { result: StressTestResult | null; error: string | null } {
  const validation = validateStressTest(holdings, form, messages);
  if (!validation.ok) {
    return { result: null, error: validation.error };
  }

  const impactedHoldings: StressTestHoldingImpact[] = [];
  let beforeValue = 0;
  let afterValue = 0;

  for (const holding of holdings) {
    const ticker = holding.ticker.trim();
    const currentValue = holdingCurrentValue(holding);
    if (!ticker || currentValue === undefined || currentValue <= 0) {
      continue;
    }

    const matched = matchesPreset(holding, form.preset, validation.customTicker);
    const shockPct = matched ? validation.shockPct : 0;
    const adjustedValue = currentValue * (1 + shockPct / 100);

    beforeValue += currentValue;
    afterValue += adjustedValue;

    if (matched) {
      impactedHoldings.push({
        ticker: normalizeTicker(holding.ticker),
        name: holding.name,
        beforeValue: currentValue,
        afterValue: adjustedValue,
        delta: adjustedValue - currentValue,
        deltaPct: shockPct,
        shockPct,
      });
    }
  }

  const delta = afterValue - beforeValue;
  const deltaPct = beforeValue > 0 ? (delta / beforeValue) * 100 : 0;

  return {
    error: null,
    result: {
      preset: form.preset,
      beforeValue,
      afterValue,
      delta,
      deltaPct,
      impactedHoldings: impactedHoldings
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
        .slice(0, 5),
      explanation: buildExplanation(
        form.preset,
        impactedHoldings.length,
        messages,
        validation.customTicker,
      ),
    },
  };
}
