import type { HoldingInput } from "@/lib/portfolioApi";
import { normalizeTicker, tickerDisplayName } from "@/lib/tickerMap";

export type ParsedHoldingDraft = HoldingInput & {
  source_text: string;
};

export type ParseHoldingsResult = {
  holdings: ParsedHoldingDraft[];
  warnings: string[];
};

const LOCAL_ALIASES: Record<string, string> = {
  兆利: "3548.TW",
  "3548": "3548.TW",
  中華: "2204.TW",
  "2204": "2204.TW",
  國泰永續高股息: "00878.TW",
  國泰20年美債: "00687B.TW",
};

const CONVERSATIONAL_PREFIX_PATTERN =
  /^(?:我有|我持有|目前有|另外有|還有|以及|和|跟|加上)\s*/;
const SECURITY_PATTERN =
  /([A-Za-z]{1,6}(?:\.[A-Za-z]{1,3})?|\d{4,5}[A-Za-z]?|[\u4e00-\u9fff]{2,12})/;
const SHARES_PATTERN = /([\d,]+(?:\.\d+)?)\s*(?:股|shares?|張)?/i;
const COST_PATTERN =
  /(?:平均成本|平均買在|買在|均價|成本|avg(?:erage)?\s*cost|cost)\s*[:：]?\s*([\d,]+(?:\.\d+)?)/i;

function parseNumber(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value.replace(/,/g, ""));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function normalizeSecurity(raw: string): string {
  const trimmed = raw.trim();
  return LOCAL_ALIASES[trimmed] ?? normalizeTicker(trimmed);
}

function splitCandidateLines(input: string): string[] {
  return input
    .split(/[;\n；。]+|(?:，|,)\s*(?=(?:我有|我持有|目前有|另外有|還有|以及|和|跟|加上)?\s*(?:[A-Za-z]{1,6}(?:\.[A-Za-z]{1,3})?|\d{4,5}[A-Za-z]?|[\u4e00-\u9fff]{2,12})\s*(?:有\s*)?[\d,]+(?:\.\d+)?\s*(?:股|shares?|張))/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function stripConversationalPrefix(line: string): string {
  return line.trim().replace(CONVERSATIONAL_PREFIX_PATTERN, "").trim();
}

function parseHoldingLine(line: string): ParsedHoldingDraft | null {
  const cleanedLine = stripConversationalPrefix(line);
  const security = cleanedLine.match(SECURITY_PATTERN)?.[1];
  if (!security) return null;

  const remainder = cleanedLine.slice(cleanedLine.indexOf(security) + security.length);
  const shares = parseNumber(remainder.match(SHARES_PATTERN)?.[1]);
  const avgCost = parseNumber(cleanedLine.match(COST_PATTERN)?.[1]);

  // Average cost is optional during onboarding. The analysis layer will surface
  // the missing cost basis instead of rejecting an otherwise valid position.
  if (!shares || shares <= 0 || (avgCost !== undefined && avgCost < 0)) {
    return null;
  }

  const ticker = normalizeSecurity(security);
  return {
    ticker,
    name: tickerDisplayName(ticker),
    shares,
    avg_cost: avgCost,
    source_text: cleanedLine,
  };
}

export function parsePortfolioHoldingsText(
  input: string,
  warningLabel = "Some lines could not be parsed.",
): ParseHoldingsResult {
  const lines = splitCandidateLines(input);
  const holdings = lines
    .map(parseHoldingLine)
    .filter((holding): holding is ParsedHoldingDraft => holding !== null);
  const warnings =
    lines.length > holdings.length && lines.length > 0 ? [warningLabel] : [];

  return {
    holdings,
    warnings,
  };
}
