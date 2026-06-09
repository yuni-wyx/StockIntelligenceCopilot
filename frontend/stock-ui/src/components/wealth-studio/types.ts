import type { HoldingInput } from "@/lib/portfolioApi";

export type ScenarioForm = {
  sellTicker: string;
  sellShares: string;
  sellPercentage: string;
  buyTicker: string;
  buyAmount: string;
  buyName: string;
  question: string;
};

export type ComparisonScenarioKind =
  | "sell_percentage"
  | "buy_amount"
  | "reduce_concentration"
  | "add_position";

export type ComparisonScenarioDraft = {
  id: string;
  name: string;
  kind: ComparisonScenarioKind;
  ticker: string;
  percentage: string;
  amount: string;
  question: string;
};

export type ComparisonPayloadScenario = {
  name: string;
  actions: Array<{
    action: "sell" | "buy" | "hold_cash";
    ticker: string;
    shares?: number;
    percentage?: number;
    amount?: number;
  }>;
  user_question?: string;
};

export type HoldingValidationField =
  | "ticker"
  | "shares"
  | "avg_cost"
  | "current_price"
  | "current_value";

export type NumericHoldingField = "avg_cost" | "current_price" | "current_value" | "shares";

export type EditableHolding = Omit<HoldingInput, NumericHoldingField> & {
  _rowId: string;
  avg_cost?: string;
  current_price?: string;
  current_value?: string;
  shares?: string;
};

export type HoldingDerivedMetrics = {
  costBasis?: number;
  currentValue?: number;
  unrealizedGainLoss?: number;
  returnPct?: number;
};

export type HoldingValidationMessage = {
  rowIndex: number;
  field: HoldingValidationField;
  message: string;
};

export type WealthStudioOperation =
  | "analyze"
  | "save"
  | "load"
  | "scenario"
  | "compare"
  | "coach";

export type HoldingsValidationState = {
  messages: HoldingValidationMessage[];
  fieldKeys: Set<string>;
  hasErrors: boolean;
};
