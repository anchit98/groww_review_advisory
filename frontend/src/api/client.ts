const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
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
