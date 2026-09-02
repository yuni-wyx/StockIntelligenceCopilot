function getBackendBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_BACKEND_BASE_URL?.trim().replace(/\/$/, "");
  if (configured) {
    return configured;
  }
  if (
    process.env.NODE_ENV === "development" ||
    (typeof window !== "undefined" && window.location.hostname === "localhost")
  ) {
    const host =
      typeof window !== "undefined" && window.location.hostname
        ? window.location.hostname
        : "127.0.0.1";
    return `http://${host}:8000`;
  }
  throw new Error(
    "NEXT_PUBLIC_BACKEND_BASE_URL is not configured. Set it to the deployed backend origin.",
  );
}

export function buildApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }

  return `${getBackendBaseUrl()}/api${path}`;
}
