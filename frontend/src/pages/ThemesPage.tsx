import { ActionItemsList } from "../components/ActionItemsList";
import { AsyncPanel } from "../components/AsyncPanel";
import { PageHeader } from "../components/PageHeader";
import { ThemeSpotlightCard } from "../components/ThemeSpotlightCard";
import { ThemesOverviewStrip } from "../components/ThemesOverviewStrip";
import { useRunContext } from "../context/RunContext";
import { severityForRank } from "../lib/severity";

export function ThemesPage() {
  const { reportingLabel, pulse, pulseLoading, pulseError } = useRunContext();

  const themes = pulse?.top_themes ?? [];
  const actions = pulse?.action_ideas ?? [];

  return (
    <>
      <PageHeader title="Top Themes" reportingLabel={reportingLabel} />
      <AsyncPanel loading={pulseLoading} error={pulseError} empty={!themes.length}>
        <div className="stagger-children space-y-8">
          <ThemesOverviewStrip themeCount={themes.length} actionCount={actions.length} />

          <section>
            <h2 className="section-title mb-1">Customer signal map</h2>
            <p className="mb-4 text-sm text-on-surface-variant/80">
              Top themes ranked by severity — each card highlights what customers are saying this
              week.
            </p>
            <div className="grid grid-cols-1 items-stretch gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {themes.slice(0, 3).map((theme, index) => (
                <ThemeSpotlightCard
                  key={theme.linked_final_theme_id ?? theme.theme_name}
                  rank={index + 1}
                  themeName={theme.theme_name}
                  summary={theme.summary}
                  bulletPoints={theme.bullet_points}
                  severity={severityForRank(index)}
                />
              ))}
            </div>
          </section>

          {actions.length > 0 ? (
            <section>
              <h2 className="section-title mb-1">Action items</h2>
              <p className="mb-4 text-sm text-on-surface-variant/80">
                Recommended moves for this week, tied to the themes above.
              </p>
              <ActionItemsList
                items={actions.slice(0, 3).map((action) => ({ action: action.action }))}
              />
            </section>
          ) : null}
        </div>
      </AsyncPanel>
    </>
  );
}
