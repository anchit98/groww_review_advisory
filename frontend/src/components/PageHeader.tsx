import { CalendarDays } from "lucide-react";

import type { StoreListingRatings } from "../lib/ratings";
import { StoreRatingsInline } from "./StoreRatingsInline";

type Props = {
  title: string;
  reportingLabel?: string;
  storeRatings?: StoreListingRatings | null;
};

export function PageHeader({ title, reportingLabel, storeRatings }: Props) {
  const showMetaRow = reportingLabel || storeRatings;

  return (
    <header className="mb-6 space-y-4 sm:mb-8">
      <div>
        <p className="text-sm font-medium text-on-surface-variant/90">Leadership Insights</p>
        <h1 className="mt-1 bg-gradient-to-br from-on-surface via-on-surface to-primary/80 bg-clip-text text-2xl font-semibold tracking-tight text-transparent sm:text-3xl">
          {title}
        </h1>
      </div>
      {showMetaRow ? (
        <div className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          {reportingLabel ? (
            <div className="glass-badge max-w-full">
              <CalendarDays className="h-4 w-4 shrink-0 text-primary" aria-hidden />
              <span className="break-words">{reportingLabel}</span>
            </div>
          ) : null}
          <StoreRatingsInline
            ratings={storeRatings}
            className="w-full sm:ml-auto sm:w-auto sm:justify-end"
          />
        </div>
      ) : null}
    </header>
  );
}
