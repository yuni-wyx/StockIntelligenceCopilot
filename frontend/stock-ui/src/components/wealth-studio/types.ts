import type { HoldingInput } from "@/lib/portfolioApi";
import type { PortfolioAnalysisResponse } from "@/lib/portfolioApi";

export type PortfolioHoldingContribution = {
  ticker: string;
  name?: string | null;
  weight_pct?: number | null;
  current_value?: number | null;
  unrealized_gain_loss?: number | null;
  return_pct?: number | null;
  contribution_value?: number | null;
  contribution_pct?: number | null;
  explanation?: string | null;
};

export type PortfolioConcentrationSnapshot = {
  top_holding_weight_pct?: number | null;
  top_3_weight_pct?: number | null;
  top_5_weight_pct?: number | null;
  top_tickers?: PortfolioHoldingContribution[];
  theme_exposure_pct?: Record<string, number>;
  sector_exposure_pct?: Record<string, number>;
  market_exposure_pct?: Record<string, number>;
  flags?: string[];
};

export type PortfolioIncomeQualitySnapshot = {
  estimated_annual_dividend?: number | null;
  estimated_monthly_dividend?: number | null;
  top_dividend_contributors?: PortfolioHoldingContribution[];
  dividend_concentration_pct?: number | null;
  holdings_missing_dividend_data?: string[];
  caveats?: string[];
};

export type PortfolioRiskAttributionSnapshot = {
  top_downside_weighted_holdings?: PortfolioHoldingContribution[];
  top_unrealized_losers?: PortfolioHoldingContribution[];
  top_unrealized_winners?: PortfolioHoldingContribution[];
  top_stress_test_contributors?: PortfolioHoldingContribution[];
  flags?: string[];
};

export type PortfolioReviewItem = {
  title: string;
  reason: string;
  evidence_keys?: string[];
  severity?: "low" | "medium" | "high";
};

export type PortfolioIntelligenceSnapshot = {
  risk_attribution?: PortfolioRiskAttributionSnapshot;
  concentration?: PortfolioConcentrationSnapshot;
  income_quality?: PortfolioIncomeQualitySnapshot;
  suggested_review_items?: PortfolioReviewItem[];
};

export type PortfolioAnalysisWithIntelligence = PortfolioAnalysisResponse & {
  portfolio_intelligence?: PortfolioIntelligenceSnapshot | null;
};

export type ScenarioForm = {
  sellTicker: string;
  sellShares: string;
  sellPercentage: string;
  buyTicker: string;
  buyAmount: string;
  buyName: string;
  question: string;
};

export type StressTestPreset =
  | "broad_market_20"
  | "technology_selloff_15"
  | "taiwan_market_15"
  | "bond_rate_sensitive_10"
  | "custom_ticker";

export type StressTestForm = {
  preset: StressTestPreset;
  customTicker: string;
  customShockPct: string;
};

export type StressTestHoldingImpact = {
  ticker: string;
  name?: string;
  beforeValue: number;
  afterValue: number;
  delta: number;
  deltaPct: number;
  shockPct: number;
};

export type StressTestResult = {
  preset: StressTestPreset;
  beforeValue: number;
  afterValue: number;
  delta: number;
  deltaPct: number;
  impactedHoldings: StressTestHoldingImpact[];
  explanation: string;
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

export type PortfolioChatQuestionChip = {
  id: string;
  label: string;
};
