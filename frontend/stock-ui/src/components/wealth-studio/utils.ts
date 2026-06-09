import { normalizeTicker } from "@/lib/tickerMap";
import type { HoldingInput } from "@/lib/portfolioApi";
import type {
  ComparisonPayloadScenario,
  ComparisonScenarioDraft,
  ComparisonScenarioKind,
  ScenarioForm,
} from "./types";

export const DEFAULT_COMPARE_JSON = JSON.stringify(
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

export const scenarioKindOptions: Array<{
  value: ComparisonScenarioKind;
}> = [
  { value: "sell_percentage" },
  { value: "buy_amount" },
  { value: "reduce_concentration" },
  { value: "add_position" },
];

export function scenarioKindLabel(
  kind: ComparisonScenarioKind,
  copy: {
    sellPercentageScenario: string;
    buyAmountScenario: string;
    reduceConcentrationScenario: string;
    addPositionScenario: string;
  },
) {
  return {
    sell_percentage: copy.sellPercentageScenario,
    buy_amount: copy.buyAmountScenario,
    reduce_concentration: copy.reduceConcentrationScenario,
    add_position: copy.addPositionScenario,
  }[kind];
}

export function scenarioKindHelper(
  kind: ComparisonScenarioKind,
  copy: {
    sellPercentageScenarioHelper: string;
    buyAmountScenarioHelper: string;
    reduceConcentrationScenarioHelper: string;
    addPositionScenarioHelper: string;
  },
) {
  return {
    sell_percentage: copy.sellPercentageScenarioHelper,
    buy_amount: copy.buyAmountScenarioHelper,
    reduce_concentration: copy.reduceConcentrationScenarioHelper,
    add_position: copy.addPositionScenarioHelper,
  }[kind];
}

export function createComparisonScenarioDraft(index: number): ComparisonScenarioDraft {
  return {
    id: `scenario-${Date.now()}-${index}`,
    name: `Scenario ${index + 1}`,
    kind: "sell_percentage",
    ticker: "",
    percentage: "50",
    amount: "",
    question: "How does this change portfolio risk and concentration?",
  };
}

export function createPortfolioPayload(
  holdings: HoldingInput[],
  riskProfile: string,
  goal: string,
) {
  return {
    holdings,
    risk_profile: riskProfile,
    goal,
    base_currency: "TWD",
  };
}

export function buildScenarioActions(scenarioForm: ScenarioForm) {
  const actions = [];
  if (scenarioForm.sellTicker.trim()) {
    actions.push({
      action: "sell" as const,
      ticker: normalizeTicker(scenarioForm.sellTicker),
      shares: scenarioForm.sellShares ? Number(scenarioForm.sellShares) : undefined,
      percentage: scenarioForm.sellPercentage ? Number(scenarioForm.sellPercentage) : undefined,
    });
  }
  if (scenarioForm.buyTicker.trim()) {
    actions.push({
      action: "buy" as const,
      ticker: normalizeTicker(scenarioForm.buyTicker),
      amount: scenarioForm.buyAmount ? Number(scenarioForm.buyAmount) : undefined,
    });
  }
  return actions;
}

export function normalizeComparisonPayload(
  scenarios: ComparisonPayloadScenario[],
) {
  return scenarios.map((scenarioItem) => ({
    ...scenarioItem,
    actions: scenarioItem.actions.map((action) => ({
      ...action,
      ticker: normalizeTicker(action.ticker),
    })),
  }));
}
