import type { ThemeIssueCount, WeeklyPulse } from "../types/pulse";

export type ComparisonMetric = {
  label: string;
  current: number;
  previous: number;
  delta: number;
  /** True when a lower value is better (e.g. issue volume). */
  lowerIsBetter: boolean;
};

export type WeekComparison = {
  previousWeekLabel: string;
  metrics: ComparisonMetric[];
};

export function runIdFromSummary(run: { run_id?: string; week_ending: string }): string {
  return run.run_id ?? run.week_ending;
}

export function findPreviousRunId(
  currentRunId: string,
  runs: { run_id?: string; week_ending: string }[],
): string | null {
  const sorted = [...runs].sort((a, b) => b.week_ending.localeCompare(a.week_ending));
  const idx = sorted.findIndex((r) => runIdFromSummary(r) === currentRunId);
  if (idx < 0 || idx >= sorted.length - 1) return null;
  return runIdFromSummary(sorted[idx + 1]);
}

export function totalIssues(counts?: ThemeIssueCount[]): number {
  return (counts ?? []).reduce((sum, row) => sum + row.issue_count, 0);
}

export function corpusTotal(sourceMix?: Record<string, number>): number | null {
  if (!sourceMix) return null;
  const total = (sourceMix.app_store ?? 0) + (sourceMix.play_store ?? 0);
  return total > 0 ? total : null;
}

export function buildWeekComparison(
  current: {
    pulse: WeeklyPulse;
    sourceMix?: Record<string, number>;
  },
  previous: {
    pulse: WeeklyPulse;
    sourceMix?: Record<string, number>;
    weekLabel: string;
  },
): WeekComparison | null {
  const metrics: ComparisonMetric[] = [];

  const issueCurrent = totalIssues(current.pulse.theme_issue_counts);
  const issuePrevious = totalIssues(previous.pulse.theme_issue_counts);
  if (issueCurrent > 0 || issuePrevious > 0) {
    metrics.push({
      label: "Issue mentions",
      current: issueCurrent,
      previous: issuePrevious,
      delta: issueCurrent - issuePrevious,
      lowerIsBetter: true,
    });
  }

  const corpusCurrent = corpusTotal(current.sourceMix);
  const corpusPrevious = corpusTotal(previous.sourceMix);
  if (corpusCurrent != null && corpusPrevious != null) {
    metrics.push({
      label: "Reviews analyzed",
      current: corpusCurrent,
      previous: corpusPrevious,
      delta: corpusCurrent - corpusPrevious,
      lowerIsBetter: false,
    });
  }

  const themesCurrent = current.pulse.top_themes?.length ?? 0;
  const themesPrevious = previous.pulse.top_themes?.length ?? 0;
  if (themesCurrent > 0 || themesPrevious > 0) {
    metrics.push({
      label: "Themes flagged",
      current: themesCurrent,
      previous: themesPrevious,
      delta: themesCurrent - themesPrevious,
      lowerIsBetter: true,
    });
  }

  if (!metrics.length) return null;

  return {
    previousWeekLabel: previous.weekLabel,
    metrics,
  };
}

export function isImprovement(metric: ComparisonMetric): boolean | null {
  if (metric.delta === 0) return null;
  return metric.lowerIsBetter ? metric.delta < 0 : metric.delta > 0;
}

export function formatDelta(metric: ComparisonMetric): string {
  const sign = metric.delta > 0 ? "+" : "";
  return `${sign}${metric.delta.toLocaleString()}`;
}

function metricChangePhrase(metric: ComparisonMetric): string {
  const label = metric.label.toLowerCase();
  const abs = Math.abs(metric.delta).toLocaleString();
  if (metric.delta === 0) return `${label} held steady`;
  const verb = metric.delta > 0 ? "rose" : "fell";
  return `${label} ${verb} by ${abs}`;
}

function sentimentPressureConclusion(issueMetric: ComparisonMetric | undefined): string {
  if (!issueMetric || issueMetric.delta === 0) return "stable sentiment pressure";
  if (issueMetric.delta > 0) return "slightly higher sentiment pressure";
  return "slightly lower sentiment pressure";
}

/**
 * Short footer line for Overall sentiment, e.g.
 * "Vs. the prior week, issue mentions rose by 4 and reviews analyzed rose by 2,
 * indicating slightly higher sentiment pressure."
 */
export function buildComparisonNarrative(comparison: WeekComparison): string {
  const issue = comparison.metrics.find((m) => m.label === "Issue mentions");
  const corpus = comparison.metrics.find((m) => m.label === "Reviews analyzed");

  const parts: string[] = [];
  if (issue) parts.push(metricChangePhrase(issue));
  if (corpus) parts.push(metricChangePhrase(corpus));

  if (!parts.length) {
    for (const metric of comparison.metrics.slice(0, 2)) {
      parts.push(metricChangePhrase(metric));
    }
  }

  const changes = parts.join(" and ");
  const conclusion = sentimentPressureConclusion(issue);

  return `Vs. the prior week, ${changes}, indicating ${conclusion}.`;
}
