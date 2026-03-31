const WATCHLIST_KEY = "stock-copilot-watchlist";

export function getWatchlist(): string[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(WATCHLIST_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveWatchlist(tickers: string[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(WATCHLIST_KEY, JSON.stringify(tickers));
}

export function addToWatchlist(ticker: string): string[] {
  const clean = ticker.toUpperCase().trim();
  const current = getWatchlist();
  if (!clean) return current;
  if (current.includes(clean)) return current;

  const next = [...current, clean];
  saveWatchlist(next);
  return next;
}

export function removeFromWatchlist(ticker: string): string[] {
  const clean = ticker.toUpperCase().trim();
  const next = getWatchlist().filter((t) => t !== clean);
  saveWatchlist(next);
  return next;
}

export function isInWatchlist(ticker: string): boolean {
  return getWatchlist().includes(ticker.toUpperCase().trim());
}