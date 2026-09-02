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
  buy_price?: number;
  buy_date?: string;
  sell_price?: number;
  sell_date?: string;
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
  risk_attribution?: Record<string, number>;
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

export type PortfolioChatContextHolding = {
  ticker: string;
  name?: string | null;
  shares?: number | null;
  avg_cost?: number | null;
  current_price?: number | null;
  current_value?: number | null;
  cost_basis?: number | null;
  unrealized_gain_loss?: number | null;
  return_pct?: number | null;
  weight_pct?: number | null;
};

export type PortfolioChatReviewItem = {
  title: string;
  reason: string;
  evidence_keys?: string[];
  severity?: "low" | "medium" | "high";
};

export type PortfolioChatContext = {
  total_current_value?: number | null;
  total_cost_basis?: number | null;
  total_unrealized_gain_loss?: number | null;
  total_return_pct?: number | null;
  top_holdings: PortfolioChatContextHolding[];
  risk_flags: string[];
  suggested_review_items: PortfolioChatReviewItem[];
  concentration_summary: string;
  income_summary: string;
  holdings: PortfolioChatContextHolding[];
  data_caveats: string[];
};

export type PortfolioChatResponse = {
  answer: string;
  portfolio_context: PortfolioChatContext;
  evidence_used: string[];
  suggested_followups: string[];
  safety_disclaimer: string;
};

export type PortfolioHoldingMonitor = {
  ticker: string;
  name?: string | null;
  weight_pct?: number | null;
  return_pct?: number | null;
  signal_score?: number | null;
  signal_band?: string | null;
  signal_confidence?: string | null;
  news_sentiment?: string | null;
  next_earnings_date?: string | null;
  days_to_next_earnings?: number | null;
  watch_items: string[];
  caveats: string[];
};

export type PortfolioMonitorResponse = {
  generated_at: string;
  workspace_id?: string | null;
  portfolio_summary: string;
  risk_flags: string[];
  top_portfolio_alerts: string[];
  holdings: PortfolioHoldingMonitor[];
  safety_disclaimer: string;
};

export type PortfolioImportIssue = {
  row_number: number;
  message: string;
};

export type PortfolioImportPreviewResponse = {
  holdings: HoldingInput[];
  errors: PortfolioImportIssue[];
  warnings: PortfolioImportIssue[];
  detected_columns: string[];
  imported_count: number;
  total_rows: number;
};

export type InvestorProfile = {
  risk_tolerance?: string | null;
  investment_style?: string | null;
  preferred_sectors: string[];
  time_horizon?: string | null;
  updated_at?: string | null;
};

export type InvestorHistoryEntry = {
  event_type: "research" | "explain" | "trade" | "watchlist";
  tickers: string[];
  raw_query?: string | null;
  created_at: string;
};

export type InvestorMemorySnapshot = {
  profile: InvestorProfile;
  watchlist_history: InvestorHistoryEntry[];
  prior_research_history: InvestorHistoryEntry[];
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

export async function askAboutPortfolio(payload: {
  question: string;
  workspace_id?: string;
  portfolio?: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
  language?: "en" | "zh";
}): Promise<PortfolioChatResponse> {
  const res = await fetch(buildApiUrl("/portfolio/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const fallback = "Failed to get portfolio context response.";
    try {
      const data = (await res.json()) as { error?: string };
      if (data.error) {
        throw new Error(data.error);
      }
      throw new Error(fallback);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(fallback);
    }
  }
  return res.json();
}

export async function getPortfolioMonitor(payload: {
  workspace_id?: string;
  portfolio?: {
    holdings: HoldingInput[];
    risk_profile?: string;
    goal?: string;
    base_currency?: string;
  };
}): Promise<PortfolioMonitorResponse> {
  const res = await fetch(buildApiUrl("/portfolio/monitor"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const fallback = "Failed to load portfolio monitor.";
    try {
      const data = (await res.json()) as { error?: string };
      if (data.error) {
        throw new Error(data.error);
      }
      throw new Error(fallback);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(fallback);
    }
  }
  return res.json();
}

export async function previewPortfolioImport(
  file: File,
): Promise<PortfolioImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(buildApiUrl("/portfolio/import/preview"), {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const fallback = "Failed to preview CSV import.";
    try {
      const data = (await res.json()) as { error?: string };
      if (data.error) {
        throw new Error(data.error);
      }
      throw new Error(fallback);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(fallback);
    }
  }
  return res.json();
}

export async function getInvestorProfile(): Promise<InvestorProfile> {
  const res = await fetch(buildApiUrl("/investor/profile"));
  if (!res.ok) {
    throw new Error("Failed to load investor profile.");
  }
  return res.json();
}

export async function updateInvestorProfile(
  payload: Omit<InvestorProfile, "updated_at">,
): Promise<InvestorProfile> {
  const res = await fetch(buildApiUrl("/investor/profile"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("Failed to update investor profile.");
  }
  return res.json();
}

export async function getInvestorMemory(): Promise<InvestorMemorySnapshot> {
  const res = await fetch(buildApiUrl("/investor/memory"));
  if (!res.ok) {
    throw new Error("Failed to load investor memory.");
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
  try {
    const res = await fetch(buildApiUrl("/portfolio/save"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = "";
      try {
        const data = (await res.json()) as { detail?: string; error?: string };
        detail = data.detail || data.error || "";
      } catch {
        // Keep the HTTP status when the server does not return JSON.
      }
      throw new Error(`Failed to save portfolio (${res.status})${detail ? `: ${detail}` : "."}`);
    }
    return res.json();
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("Failed to save portfolio (")) {
      throw error;
    }
    throw new Error(
      `Failed to save portfolio: ${error instanceof Error ? error.message : "network request failed"}`,
    );
  }
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

export async function deleteCurrentPortfolio(): Promise<{ deleted: boolean }> {
  const res = await fetch(buildApiUrl("/portfolio/current"), {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("Failed to clear current portfolio.");
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
