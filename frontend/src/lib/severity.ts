export type Severity = "CRITICAL" | "WARNING" | "CONCERN";

export function severityForRank(rank: number): Severity {
  if (rank === 0) return "CRITICAL";
  if (rank === 1) return "WARNING";
  return "CONCERN";
}

export function quoteTagForRank(rank: number): string {
  const severity = severityForRank(rank);
  return `${severity} THEME`;
}

export function themeIconKey(themeName: string): "support" | "performance" | "fees" | "default" {
  const lower = themeName.toLowerCase();
  if (lower.includes("support") || lower.includes("service")) return "support";
  if (lower.includes("technical") || lower.includes("performance") || lower.includes("crash"))
    return "performance";
  if (lower.includes("broker") || lower.includes("charge") || lower.includes("fee")) return "fees";
  return "default";
}
