import type { ThemeIssueCount } from "../components/SentimentCard";

type ThemeSummary = { theme_name: string; summary: string };

function firstSentence(text: string): string {
  const sentence = text.split(/[.!?]/)[0]?.trim() || text.trim();
  return sentence.endsWith(".") ? sentence : `${sentence}.`;
}

/** One-line summary of the highest-volume issue theme for the card footer. */
export function buildThemeIssuesFooterLine(
  counts: ThemeIssueCount[],
  topThemes: ThemeSummary[] = [],
): string {
  if (!counts.length) {
    return "No consolidated theme issues are indexed for this run yet.";
  }

  const summaryByName = new Map(topThemes.map((t) => [t.theme_name, t.summary]));
  const ranked = [...counts].sort((a, b) => b.issue_count - a.issue_count);
  const lead = ranked[0];
  const leadSummary = summaryByName.get(lead.theme_name);

  if (leadSummary) return firstSentence(leadSummary);

  return `${lead.theme_name} drives the most issue-linked reviews (${lead.issue_count.toLocaleString()}).`;
}
