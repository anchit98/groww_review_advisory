const DEFAULT_RENDER_API = "https://groww-review-advisory-api.onrender.com";

/** Resolve API base URL at build/runtime (Vite inlines import.meta.env). */
export function resolveApiBase(): string {
  const configured = (import.meta.env.VITE_API_URL ?? "").trim().replace(/\/$/, "");
  if (configured) return configured;
  if (import.meta.env.DEV) return "http://127.0.0.1:8000";
  // Production on Vercel: same-origin /api/* is proxied via vercel.json (no CORS, no env required).
  if (typeof window !== "undefined") return "";
  return DEFAULT_RENDER_API;
}

const API_BASE = resolveApiBase();

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url);
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (!contentType.includes("application/json")) {
    const hint = API_BASE
      ? "Check VITE_API_URL points at the Render API (no trailing slash)."
      : "Set VITE_API_URL in Vercel to your Render URL, or redeploy with the /api proxy in vercel.json.";
    throw new Error(`API returned non-JSON. ${hint}`);
  }
  return response.json() as Promise<T>;
}

export function getRuns() {
  return fetchJson<{ runs: import("../types/pulse").RunSummary[]; updated_at?: string }>(
    "/api/runs",
  );
}

export function getLatestRun() {
  return fetchJson<{ run: import("../types/pulse").RunSummary }>("/api/runs/latest");
}

export function getRun(runId: string) {
  return fetchJson<{ run: import("../types/pulse").RunDetail }>(`/api/runs/${runId}`);
}

export function getRunPulse(runId: string) {
  return fetchJson<{
    run_id: string;
    reporting_label: string;
    weekly_pulse: import("../types/pulse").WeeklyPulse;
  }>(`/api/runs/${runId}/pulse`);
}

export function getRunQuotes(runId: string, perTheme = 5) {
  return fetchJson<{
    run_id: string;
    per_theme_limit: number;
    quote_candidates: import("../types/quotes").QuoteCandidate[];
  }>(`/api/runs/${runId}/quotes?per_theme=${perTheme}`);
}
