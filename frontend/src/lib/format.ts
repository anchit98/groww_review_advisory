export function truncateHash(hash: string, length = 16): string {
  if (hash.length <= length) return hash;
  return `${hash.slice(0, length)}…`;
}

export function shortActionTitle(action: string, max = 72): string {
  if (action.length <= max) return action;
  const slice = action.slice(0, max);
  const lastSpace = slice.lastIndexOf(" ");
  return `${(lastSpace > 40 ? slice.slice(0, lastSpace) : slice).trim()}…`;
}

/** Split prose into a fixed number of display lines (balanced by word count). */
export function splitIntoLines(text: string, lineCount: number): string[] {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (!words.length) {
    return Array.from({ length: lineCount }, () => "");
  }

  const perLine = Math.max(1, Math.ceil(words.length / lineCount));
  const lines: string[] = [];

  for (let index = 0; index < lineCount; index += 1) {
    const start = index * perLine;
    const chunk = words.slice(start, start + perLine).join(" ");
    lines.push(chunk);
  }

  return lines;
}

export function formatReportingLabel(window?: {
  start_date?: string;
  end_date?: string;
}): string {
  if (!window?.start_date || !window?.end_date) return "Reporting period unavailable";
  return `${window.start_date} to ${window.end_date}`;
}

export function statusTone(status?: string): "ok" | "warn" | "error" | "muted" {
  const value = (status ?? "").toLowerCase();
  if (value.includes("completed") && !value.includes("warning")) return "ok";
  if (value.includes("partial") || value.includes("warning")) return "warn";
  if (value.includes("fail") || value.includes("error")) return "error";
  return "muted";
}
