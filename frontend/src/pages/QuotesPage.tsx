import { useMemo } from "react";

import { AsyncPanel } from "../components/AsyncPanel";
import { PageHeader } from "../components/PageHeader";
import { QuoteCard } from "../components/QuoteCard";
import { SeverityChip } from "../components/SeverityChip";
import { useRunContext } from "../context/RunContext";
import { useQuoteCandidates } from "../hooks/useQuoteCandidates";
import { severityForRank } from "../lib/severity";
import type { QuoteCandidate } from "../types/quotes";

const QUOTES_PER_THEME = 5;

function groupByTheme(
  quotes: QuoteCandidate[],
  themeOrder: string[],
): { themeName: string; quotes: QuoteCandidate[] }[] {
  const buckets = new Map<string, QuoteCandidate[]>();
  for (const item of quotes) {
    const list = buckets.get(item.theme_name) ?? [];
    list.push(item);
    buckets.set(item.theme_name, list);
  }

  const orderedNames = [
    ...themeOrder.filter((name) => buckets.has(name)),
    ...[...buckets.keys()].filter((name) => !themeOrder.includes(name)),
  ];

  return orderedNames.map((themeName) => ({
    themeName,
    quotes: (buckets.get(themeName) ?? []).slice(0, QUOTES_PER_THEME),
  }));
}

export function QuotesPage() {
  const { runId, reportingLabel, pulse, pulseLoading, pulseError } = useRunContext();

  const {
    data: quoteCandidates,
    loading: quotesLoading,
    error: quotesError,
  } = useQuoteCandidates(runId, QUOTES_PER_THEME);

  const themeOrder = useMemo(
    () => (pulse?.top_themes ?? []).map((t) => t.theme_name),
    [pulse?.top_themes],
  );

  const fallbackQuotes = useMemo<QuoteCandidate[]>(() => {
    if (!pulse?.user_quotes?.length) return [];
    return pulse.user_quotes.map((item, index) => ({
      quote_candidate_id: `fallback-${index}`,
      review_id_hash: item.review_id_hash,
      theme_name: item.theme_name,
      quote_text: item.quote,
    }));
  }, [pulse?.user_quotes]);

  const effectiveQuotes =
    quoteCandidates && quoteCandidates.length > 0 ? quoteCandidates : fallbackQuotes;

  const grouped = useMemo(
    () => groupByTheme(effectiveQuotes, themeOrder),
    [effectiveQuotes, themeOrder],
  );

  const loading = pulseLoading || (quotesLoading && !fallbackQuotes.length);
  const error = pulseError ?? (effectiveQuotes.length ? null : quotesError);
  const empty = !grouped.length || grouped.every((g) => !g.quotes.length);

  return (
    <>
      <PageHeader title="Representative Quotes" reportingLabel={reportingLabel} />
      <AsyncPanel loading={loading} error={error} empty={empty}>
        <div className="stagger-children space-y-10">
          {grouped.map((section, index) => (
            <section key={section.themeName} className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="section-title">{section.themeName}</h2>
                <SeverityChip severity={severityForRank(index)} />
              </div>
              <div className="stagger-children space-y-3">
                {section.quotes.map((item) => (
                  <QuoteCard
                    key={item.quote_candidate_id ?? item.review_id_hash}
                    themeName={item.theme_name}
                    quote={item.quote_text}
                    severity={severityForRank(index)}
                    compact
                    source={item.source}
                    rating={item.rating}
                    reviewDate={item.review_date}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </AsyncPanel>
    </>
  );
}
