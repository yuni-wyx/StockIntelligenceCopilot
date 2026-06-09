import type { HoldingInput } from "@/lib/portfolioApi";
import { normalizeTicker } from "@/lib/tickerMap";
import type { EditableHolding, HoldingDerivedMetrics } from "./types";

export function createRowId() {
  return `holding-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function numericInputValue(value: number | string | null | undefined): string | undefined {
  if (value === null || value === undefined) return undefined;
  return String(value);
}

export function toEditableHolding(
  holding: HoldingInput,
  rowId = createRowId(),
): EditableHolding {
  return {
    ...holding,
    _rowId: rowId,
    avg_cost: numericInputValue(holding.avg_cost),
    current_price: numericInputValue(holding.current_price),
    current_value: numericInputValue(holding.current_value),
    shares: numericInputValue(holding.shares),
  };
}

export function parseOptionalNumber(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === "") {
    return undefined;
  }
  return Number(value);
}

export function payloadNumber(value: string | undefined): number | undefined {
  const parsed = parseOptionalNumber(value);
  return parsed === undefined || Number.isNaN(parsed) ? undefined : parsed;
}

export function toApiHolding(holding: EditableHolding): HoldingInput {
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

export function normalizeHoldings(holdings: EditableHolding[]): HoldingInput[] {
  return holdings
    .filter((holding) => holding.ticker?.trim())
    .map((holding) => ({
      ...toApiHolding(holding),
      ticker: normalizeTicker(holding.ticker),
    }));
}

export function calculateEditableHoldingMetrics(
  holding: EditableHolding,
): HoldingDerivedMetrics {
  const shares = parseOptionalNumber(holding.shares);
  const avgCost = parseOptionalNumber(holding.avg_cost);
  const currentPrice = parseOptionalNumber(holding.current_price);
  const manualCurrentValue = parseOptionalNumber(holding.current_value);
  const costBasis =
    shares !== undefined &&
    avgCost !== undefined &&
    !Number.isNaN(shares) &&
    !Number.isNaN(avgCost)
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
