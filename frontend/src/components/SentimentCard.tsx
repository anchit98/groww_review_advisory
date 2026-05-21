import { TrendingDown } from "lucide-react";
import { useMemo } from "react";

import { buildComparisonNarrative, type WeekComparison } from "../lib/weekComparison";
import { CardFooter } from "./CardFooter";
import { WeekComparisonBlock } from "./WeekComparisonBlock";

export type ThemeIssueCount = {
  theme_name: string;
  linked_final_theme_id?: string;
  issue_count: number;
};

type Props = {
  summary: string;
  themeCount?: number;
  sourceMix?: Record<string, number>;
  totalIssueCount?: number;
  lookbackWeeks?: number;
  weekComparison?: WeekComparison | null;
  weekComparisonLoading?: boolean;
};

/** Negative-leaning corpus heuristic for the animated intensity meter (display only). */
const SENTIMENT_METER_PCT = 72;

export function SentimentCard({
  summary,
  themeCount = 0,
  sourceMix,
  totalIssueCount,
  lookbackWeeks = 8,
  weekComparison,
  weekComparisonLoading,
}: Props) {
  const headline = summary.split(/[.!?]/)[0]?.trim() || summary;

  const corpusTotal = useMemo(() => {
    if (!sourceMix) return null;
    const total = (sourceMix.app_store ?? 0) + (sourceMix.play_store ?? 0);
    return total > 0 ? total : null;
  }, [sourceMix]);

  const footerText = useMemo(() => {
    if (weekComparisonLoading) {
      return "Vs. the prior week — loading comparison…";
    }
    if (weekComparison?.metrics.length) {
      return buildComparisonNarrative(weekComparison);
    }
    const opening = headline.endsWith(".") ? headline : `${headline}.`;
    return `${opening} No prior indexed week is available for comparison.`;
  }, [headline, weekComparison, weekComparisonLoading]);

  return (
    <section className="glass-panel glass-panel-interactive flex h-full min-h-0 flex-col p-4 sm:min-h-[280px] sm:p-6">
      <div className="mb-3 flex shrink-0 items-center gap-2 text-sm font-medium text-on-surface-variant">
        <span className="glass-icon-well sentiment-icon-pulse !h-8 !w-8">
          <TrendingDown className="h-4 w-4 text-error" aria-hidden />
        </span>
        Overall sentiment
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="shrink-0 pt-0.5 sm:max-w-[9rem]">
            <p className="sentiment-glow text-2xl font-semibold tracking-tight text-error">
              Negative
            </p>
            <p className="mt-1 text-[10px] font-medium uppercase tracking-widest text-on-surface-variant/70">
              User voice
            </p>
          </div>

          <div className="min-w-0 flex-1 space-y-2">
            <div>
              <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider text-on-surface-variant/75">
                <span>Intensity</span>
                <span className="tabular-nums text-error/90">{SENTIMENT_METER_PCT}%</span>
              </div>
              <div className="glass-progress-track relative z-[2]">
                <div
                  className="sentiment-intensity-fill"
                  style={{ width: `${SENTIMENT_METER_PCT}%` }}
                  role="progressbar"
                  aria-valuenow={SENTIMENT_METER_PCT}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Sentiment intensity"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatPill label="Themes flagged" value={String(themeCount)} />
              {corpusTotal != null ? (
                <StatPill label="Reviews analyzed" value={corpusTotal.toLocaleString()} />
              ) : null}
              {totalIssueCount != null && totalIssueCount > 0 ? (
                <StatPill label="Issue mentions" value={totalIssueCount.toLocaleString()} />
              ) : (
                <StatPill label="Lookback" value={`${lookbackWeeks}w`} />
              )}
            </div>
          </div>
        </div>

        <WeekComparisonBlock
          comparison={weekComparison ?? null}
          loading={weekComparisonLoading}
        />
      </div>

      <CardFooter>{footerText}</CardFooter>
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-inset sentiment-stat px-2 py-1">
      <p className="text-[10px] uppercase tracking-wide text-on-surface-variant/65">{label}</p>
      <p className="text-xs font-semibold tabular-nums text-on-surface">{value}</p>
    </div>
  );
}
