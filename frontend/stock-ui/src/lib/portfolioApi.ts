import { buildApiUrl } from "@/lib/apiBase";

export type HoldingInput = {
  ticker: string;
  name?: string;
  avg_cost?: number;
  current_price?: number;
  current_value?: number;
  shares?: number;
  asset_type?: string;
  category?: string;
  notes?: string;
};

export type EvidenceSource = {
  source_id: string;
  source_type: string;
  ticker?: string | null;
  provider?: string | null;
  title?: string | null;
  url?: string | null;
  published_at?: string | null;
  retrieved_at?: string | null;
  confidence?: number;
};

export type ClaimEvidence = {
  claim_id: string;
  output_field: string;
  claim: string;
  evidence_ids: string[];
  confidence_score: number;
  confidence_label: string;
  unsupported: boolean;
  notes: string[];
};

export type UnsupportedClaim = {
  output_field: string;
  claim: string;
  reason: string;
  severity: string;
};

export type PortfolioAnalysisResponse = {
  total_cost_basis?: number | null;
  total_current_value?: number | null;
  total_unrealized_gain_loss?: number | null;
  total_return_pct?: number | null;
  estimated_annual_dividend?: number | null;
  estimated_monthly_dividend?: number | null;
  overall_score?: number;
  diversification_score?: number;
  concentration_score?: number;
  income_score?: number;
  defensive_score?: number;
  growth_score?: number;
  holdings: Array<{
    ticker: string;
    name?: string | null;
    cost_basis?: number | null;
    current_value?: number | null;
    unrealized_gain_loss?: number | null;
    return_pct?: number | null;
    portfolio_weight_pct?: number | null;
    estimated_annual_dividend?: number | null;
    estimated_monthly_dividend?: number | null;
    current_price?: number | null;
    shares?: number | null;
    category?: string | null;
    asset_type?: string | null;
    sector?: string | null;
    theme?: string | null;
    market?: string | null;
    notes?: string | null;
    missing_data?: string[];
  }>;
  asset_type_exposure: Record<string, number>;
  category_exposure: Record<string, number>;
  sector_exposure: Record<string, number>;
  theme_exposure: Record<string, number>;
  market_exposure: Record<string, number>;
  risk_flags: string[];
  summary: string;
  suggestions: string[];
  news_to_monitor: Record<string, string[]>;
  missing_data: string[];
  evidence_provenance?: EvidenceSource[];
  claim_evidence?: ClaimEvidence[];
  unsupported_claims?: UnsupportedClaim[];
  confidence_score?: number;
};

export type ScenarioResponse = {
  before: PortfolioAnalysisResponse;
  after: PortfolioAnalysisResponse;
  dividend_change?: number | null;
  risk_change_summary: string;
  recommendation: string;
  caveats: string[];
};

export type ScenarioComparisonResponse = {
  current: PortfolioAnalysisResponse;
  scenarios: Array<{
    name: string;
    before_value?: number | null;
    after_value?: number | null;
    dividend_change?: number | null;
    technology_exposure_change?: number | null;
    defensive_allocation_change?: number | null;
    concentration_change?: number | null;
    risk_flags_added: string[];
    risk_flags_removed: string[];
    overall_score_change: number;
    recommendation_rank: number;
    recommendation: string;
  }>;
};

export type PortfolioAgentResponse = {
  conclusion: string;
  current_portfolio_diagnosis: string;
  key_numbers: Record<string, unknown>;
  evidence_used: string[];
  bull_case: string;
  bear_case: string;
  base_case: string;
  suggested_next_actions: string[];
  risks: string[];
  missing_data: string[];
};

export async function analyzePortfolio(payload: {
  holdings: HoldingInput[];
  risk_profile?: string;
  goal?: string;
  base_currency?: string;
}): Promise<PortfolioAnalysisResponse> {
  const res = await fetch(buildApiUrl("/portfolio/analyze"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to analyze portfolio.");
  }
  return res.json();
}

export async function runPortfolioScenario(payload: {
  portfolio: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
  actions: Array<{
    action: "sell" | "buy" | "hold_cash";
    ticker: string;
    shares?: number;
    percentage?: number;
    amount?: number;
  }>;
  target_ticker?: string;
  target_name?: string;
  user_question?: string;
}): Promise<ScenarioResponse> {
  const res = await fetch(buildApiUrl("/portfolio/scenario"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to run scenario analysis.");
  }
  return res.json();
}

export async function comparePortfolioScenarios(payload: {
  portfolio: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
  scenarios: Array<{
    name: string;
    actions: Array<{
      action: "sell" | "buy" | "hold_cash";
      ticker: string;
      shares?: number;
      percentage?: number;
      amount?: number;
    }>;
    user_question?: string;
  }>;
}): Promise<ScenarioComparisonResponse> {
  const res = await fetch(buildApiUrl("/portfolio/scenarios/compare"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to compare scenarios.");
  }
  return res.json();
}

export async function askPortfolioAgent(payload: {
  portfolio?: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
  user_question?: string;
  target_ticker_or_fund?: string;
}): Promise<PortfolioAgentResponse> {
  const res = await fetch(buildApiUrl("/portfolio/agent"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to get portfolio agent response.");
  }
  return res.json();
}

export async function savePortfolio(payload: {
  portfolio: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
  name?: string;
  make_current?: boolean;
}) {
  const res = await fetch(buildApiUrl("/portfolio/save"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to save portfolio.");
  }
  return res.json();
}

export async function loadCurrentPortfolio() {
  const res = await fetch(buildApiUrl("/portfolio/current"));
  if (!res.ok) {
    throw new Error("Failed to load current portfolio.");
  }
  return res.json();
}

export async function updateCurrentPortfolio(payload: {
  holdings: HoldingInput[];
  risk_profile?: string;
  goal?: string;
  base_currency?: string;
}) {
  const res = await fetch(buildApiUrl("/portfolio/current"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to update current portfolio.");
  }
  return res.json();
}

export async function listSavedPortfolios() {
  const res = await fetch(buildApiUrl("/portfolio/list"));
  if (!res.ok) {
    throw new Error("Failed to list saved portfolios.");
  }
  return res.json() as Promise<{ portfolios: Array<Record<string, unknown>> }>;
}
