const BACKEND_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL?.trim().replace(/\/$/, "") || "http://localhost:8000";

export function buildApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }

  return `${BACKEND_BASE_URL}/api${path}`;
}
