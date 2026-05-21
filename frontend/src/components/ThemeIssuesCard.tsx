import { BarChart3 } from "lucide-react";
import { useMemo } from "react";

import { buildThemeIssuesFooterLine } from "../lib/themeIssues";
import { severityForRank } from "../lib/severity";
import { CardFooter } from "./CardFooter";
import type { ThemeIssueCount } from "./SentimentCard";
import { SeverityChip } from "./SeverityChip";

type Props = {
  themeIssueCounts?: ThemeIssueCount[];
  topThemes?: { theme_name: string; summary: string }[];
};

export function ThemeIssuesCard({ themeIssueCounts = [], topThemes = [] }: Props) {
  const footerLine = useMemo(
    () => buildThemeIssuesFooterLine(themeIssueCounts, topThemes),
    [themeIssueCounts, topThemes],
  );

  return (
    <section className="glass-panel glass-panel-interactive flex h-full min-h-0 flex-col p-4 sm:min-h-[280px] sm:p-6">
      <div className="mb-3 flex shrink-0 items-center gap-2 text-sm font-medium text-on-surface-variant">
        <span className="glass-icon-well !h-8 !w-8">
          <BarChart3 className="h-4 w-4 text-primary" aria-hidden />
        </span>
        Issues raised by theme
      </div>
      <p className="shrink-0 text-xs font-semibold uppercase tracking-widest text-on-surface-variant/80">
        Analysis corpus
      </p>

      <div className="flex min-h-0 flex-1 flex-col">
        {themeIssueCounts.length > 0 ? (
          <ul className="mt-4 min-h-0 flex-1 space-y-2">
            {themeIssueCounts.map((row, index) => (
              <li
                key={row.linked_final_theme_id ?? row.theme_name}
                className="glass-inset flex items-center justify-between gap-3 px-3 py-2.5"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <SeverityChip severity={severityForRank(index)} />
                  <span className="truncate text-sm text-on-surface">{row.theme_name}</span>
                </div>
                <span className="shrink-0 text-lg font-semibold tabular-nums text-on-surface">
                  {row.issue_count.toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 flex-1 text-sm text-on-surface-variant/80">
            No theme issue counts available for this run.
          </p>
        )}
      </div>

      <CardFooter>{footerLine}</CardFooter>
    </section>
  );
}
