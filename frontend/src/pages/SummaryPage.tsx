import { AsyncPanel } from "../components/AsyncPanel";
import { PageHeader } from "../components/PageHeader";
import { SentimentCard } from "../components/SentimentCard";
import { SourceMixCard } from "../components/SourceMixCard";
import { ThemeIssuesCard } from "../components/ThemeIssuesCard";
import { useRunContext } from "../context/RunContext";
import { usePreviousWeekComparison } from "../hooks/usePreviousWeekPulse";
import { useRunList } from "../hooks/useRuns";

export function SummaryPage() {
  const {
    runId,
    reportingLabel,
    sourceMix,
    storeListingRatings,
    pulse,
    pulseLoading,
    pulseError,
  } = useRunContext();

  const { data: runs } = useRunList();
  const { comparison: weekComparison, loading: weekComparisonLoading } =
    usePreviousWeekComparison(runId, runs, pulse, sourceMix);

  return (
    <>
      <PageHeader
        title="Executive Summary"
        reportingLabel={reportingLabel}
        storeRatings={storeListingRatings}
      />
      <AsyncPanel
        loading={pulseLoading}
        error={pulseError}
        empty={!pulse}
        emptyMessage="No weekly pulse is indexed yet. Run the pipeline and sync runs_index.json."
      >
        {pulse ? (
          <div className="stagger-children space-y-8">
            <SourceMixCard sourceMix={sourceMix} />
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-stretch">
              <SentimentCard
                summary={pulse.opening_summary}
                themeCount={pulse.top_themes?.length ?? 0}
                sourceMix={sourceMix}
                totalIssueCount={pulse.theme_issue_counts?.reduce(
                  (sum, row) => sum + row.issue_count,
                  0,
                )}
                weekComparison={weekComparison}
                weekComparisonLoading={weekComparisonLoading}
              />
              <ThemeIssuesCard
                themeIssueCounts={pulse.theme_issue_counts}
                topThemes={pulse.top_themes}
              />
            </div>
          </div>
        ) : null}
      </AsyncPanel>
    </>
  );
}
