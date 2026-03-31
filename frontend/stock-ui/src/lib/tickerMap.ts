export const TW_STOCK_MAP: Record<string, string> = {
  "2330": "2330.TW",
  "2330.tw": "2330.TW",
  "台積電": "2330.TW",
  "tsmc": "2330.TW",
  "taiwan semiconductor": "2330.TW",

  "2317": "2317.TW",
  "2317.tw": "2317.TW",
  "鴻海": "2317.TW",
  "foxconn": "2317.TW",
  "hon hai": "2317.TW",

  "2454": "2454.TW",
  "2454.tw": "2454.TW",
  "聯發科": "2454.TW",
  "mediatek": "2454.TW",
};

export const TW_DISPLAY_NAMES: Record<string, string> = {
  "2330.TW": "台積電",
  "2317.TW": "鴻海",
  "2454.TW": "聯發科",
};

export function normalizeTicker(input: string): string {
  if (!input) return "";

  const raw = input.trim();
  const lower = raw.toLowerCase();

  if (TW_STOCK_MAP[raw]) return TW_STOCK_MAP[raw];
  if (TW_STOCK_MAP[lower]) return TW_STOCK_MAP[lower];

  if (/^\d{4}\.TW$/i.test(raw)) {
    return `${raw.slice(0, 4)}.TW`;
  }

  if (/^\d{4}$/.test(raw)) {
    return `${raw}.TW`;
  }

  return raw.toUpperCase();
}

export function detectTickerMarket(input: string): "TW" | "US" | "" {
  const canonical = normalizeTicker(input);
  if (!canonical) return "";
  return canonical.endsWith(".TW") ? "TW" : "US";
}

export function marketLabel(input: string): string {
  const market = detectTickerMarket(input);
  if (!market) return "";
  return market === "TW" ? "TW Market" : "US Market";
}

export function tickerDisplayName(input: string): string {
  const canonical = normalizeTicker(input);
  return TW_DISPLAY_NAMES[canonical] ?? canonical;
}
