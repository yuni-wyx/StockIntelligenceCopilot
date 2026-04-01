const API_BASE = "https://stock-intelligence-copilot-168709263927.us-central1.run.app"
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/$/, "") || "http://localhost:8000";

export function buildApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }

  return `${API_BASE_URL}${path}`;
}
