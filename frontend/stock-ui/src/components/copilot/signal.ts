export type SignalBand = "Weak" | "Neutral" | "Strong";
export type SignalConfidence = "Low" | "Medium" | "High";

export type SignalPayload = {
  ticker?: string;
  benchmark?: string;
  horizon_days?: number;
  signal_score?: number;
  signal_band?: SignalBand;
  confidence?: SignalConfidence;
  positive_signals?: string[];
  negative_signals?: string[];
  data_caveats?: string[];
  disclaimer?: string;
  feature_snapshot?: Record<string, unknown>;
};

export type CopilotSignalSource = {
  ticker?: string;
  signal?: SignalPayload;
  fundamental_summary?: string;
  recent_news_summary?: string;
  price_move_summary?: string;
  volume_context?: string;
};

export type SignalViewModel = {
  ticker?: string;
  benchmark: string;
  horizonDays: number;
  signalScore: number;
  signalBand: SignalBand;
  confidence: SignalConfidence;
  positiveSignals: string[];
  negativeSignals: string[];
  dataCaveats: string[];
  disclaimer: string;
  usedFallbackParsing: boolean;
};

const SIGNAL_SUMMARY_RE =
  /Relative signal:\s+benchmark-relative strength versus\s+([A-Z.]+)\s+over\s+(\d+)\s+days is\s+(Weak|Neutral|Strong)\s+\(score\s+([0-9.]+),\s+confidence\s+(Low|Medium|High)\)\./i;

function splitCaveats(raw: string): string[] {
  return raw
    .split(/(?<=\.)\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseSignalSummary(summary: string | undefined) {
  if (!summary) return null;
  const match = summary.match(SIGNAL_SUMMARY_RE);
  if (!match) return null;

  return {
    benchmark: match[1],
    horizonDays: Number(match[2]),
    signalBand: match[3] as SignalBand,
    signalScore: Number(match[4]),
    confidence: match[5] as SignalConfidence,
  };
}

function parseSignalCaveats(text: string | undefined): string[] {
  if (!text) return [];
  const marker = "Signal caveats:";
  const index = text.indexOf(marker);
  if (index < 0) return [];
  return splitCaveats(text.slice(index + marker.length).trim());
}

export function extractSignalViewModel(
  output: CopilotSignalSource | null | undefined,
): SignalViewModel | null {
  if (!output) return null;

  const structured = output.signal;
  if (
    structured?.benchmark &&
    structured.horizon_days !== undefined &&
    structured.signal_score !== undefined &&
    structured.signal_band &&
    structured.confidence
  ) {
    return {
      ticker: structured.ticker ?? output.ticker,
      benchmark: structured.benchmark,
      horizonDays: structured.horizon_days,
      signalScore: structured.signal_score,
      signalBand: structured.signal_band,
      confidence: structured.confidence,
      positiveSignals: structured.positive_signals ?? [],
      negativeSignals: structured.negative_signals ?? [],
      dataCaveats: structured.data_caveats ?? [],
      disclaimer:
        structured.disclaimer ??
        "This signal estimates benchmark-relative strength using transparent market features. It is not a price prediction or financial advice.",
      usedFallbackParsing: false,
    };
  }

  const parsed =
    parseSignalSummary(output.fundamental_summary) ??
    parseSignalSummary(output.price_move_summary);
  if (!parsed) return null;

  const caveats = [
    ...parseSignalCaveats(output.recent_news_summary),
    ...parseSignalCaveats(output.volume_context),
  ];

  return {
    ticker: output.ticker,
    benchmark: parsed.benchmark,
    horizonDays: parsed.horizonDays,
    signalScore: parsed.signalScore,
    signalBand: parsed.signalBand,
    confidence: parsed.confidence,
    positiveSignals: [],
    negativeSignals: [],
    dataCaveats: caveats,
    disclaimer:
      "This signal estimates benchmark-relative strength using transparent market features. It is not a price prediction or financial advice.",
    usedFallbackParsing: true,
  };
}
