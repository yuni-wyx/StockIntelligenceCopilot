import { normalizeTicker } from "@/lib/tickerMap";
import { parseOptionalNumber } from "./transforms";
import type {
  ComparisonPayloadScenario,
  ComparisonScenarioDraft,
  EditableHolding,
  HoldingValidationMessage,
  HoldingsValidationState,
} from "./types";
import type { WealthStudioCopy } from "@/i18n/messages";

export function validateHoldings(
  holdings: EditableHolding[],
  copy: Pick<
    WealthStudioCopy,
    | "tickerRequired"
    | "sharesRequired"
    | "sharesPositive"
    | "avgCostNonNegative"
    | "currentPriceNonNegative"
    | "currentValueNonNegative"
    | "noHoldingsBody"
  >,
): HoldingsValidationState {
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
        message: `${rowLabel}: ${copy.tickerRequired}`,
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
        message: `${rowLabel}: ${copy.sharesRequired}`,
      });
      fieldKeys.add(`${index}:shares`);
    } else if (shares <= 0) {
      messages.push({
        rowIndex: index,
        field: "shares",
        message: `${rowLabel}: ${copy.sharesPositive}`,
      });
      fieldKeys.add(`${index}:shares`);
    }

    if (avgCost !== undefined && (Number.isNaN(avgCost) || avgCost < 0)) {
      messages.push({
        rowIndex: index,
        field: "avg_cost",
        message: `${rowLabel}: ${copy.avgCostNonNegative}`,
      });
      fieldKeys.add(`${index}:avg_cost`);
    }

    if (currentPrice !== undefined && (Number.isNaN(currentPrice) || currentPrice < 0)) {
      messages.push({
        rowIndex: index,
        field: "current_price",
        message: `${rowLabel}: ${copy.currentPriceNonNegative}`,
      });
      fieldKeys.add(`${index}:current_price`);
    }

    if (currentValue !== undefined && (Number.isNaN(currentValue) || currentValue < 0)) {
      messages.push({
        rowIndex: index,
        field: "current_value",
        message: `${rowLabel}: ${copy.currentValueNonNegative}`,
      });
      fieldKeys.add(`${index}:current_value`);
    }
  });

  if (holdings.length === 0) {
    messages.push({
      rowIndex: -1,
      field: "ticker",
      message: copy.noHoldingsBody,
    });
  }

  return {
    messages,
    fieldKeys,
    hasErrors: messages.length > 0,
  };
}

export function buildStructuredComparisonScenarios(
  comparisonScenarios: ComparisonScenarioDraft[],
  copy: Pick<
    WealthStudioCopy,
    | "scenarioTickerRequired"
    | "scenarioPercentageRequired"
    | "scenarioPercentageRange"
    | "scenarioAmountRequired"
    | "scenarioAmountPositive"
    | "sellPercentageScenario"
    | "buyAmountScenario"
    | "reduceConcentrationScenario"
    | "addPositionScenario"
  >,
  getActionLabel: (
    kind: ComparisonScenarioDraft["kind"],
    copy: Pick<
      WealthStudioCopy,
      | "sellPercentageScenario"
      | "buyAmountScenario"
      | "reduceConcentrationScenario"
      | "addPositionScenario"
    >,
  ) => string,
): {
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
    const actionLabel = getActionLabel(scenarioItem.kind, copy);

    if (!ticker) {
      errors.push(`${name}: ${copy.scenarioTickerRequired}`);
    }

    if (
      scenarioItem.kind === "sell_percentage" ||
      scenarioItem.kind === "reduce_concentration"
    ) {
      if (!scenarioItem.percentage.trim() || Number.isNaN(percentage)) {
        errors.push(`${name}: ${copy.scenarioPercentageRequired}`);
      } else if (percentage <= 0 || percentage > 100) {
        errors.push(`${name}: ${copy.scenarioPercentageRange}`);
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
      errors.push(`${name}: ${copy.scenarioAmountRequired}`);
    } else if (amount <= 0) {
      errors.push(`${name}: ${copy.scenarioAmountPositive}`);
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
