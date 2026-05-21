import { Star } from "lucide-react";

import { cn } from "../lib/cn";
import {
  formatRatingCount,
  starFillPercent,
  type StoreListingRatings,
} from "../lib/ratings";

function StoreRatingRow({
  label,
  average,
  count,
}: {
  label: string;
  average: number;
  count: number | null | undefined;
}) {
  const fill = starFillPercent(average);

  return (
    <div className="glass-inset px-4 py-3 transition-transform duration-300 hover:scale-[1.01]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-on-surface">{label}</p>
        <p className="text-lg font-semibold tabular-nums text-on-surface">{average.toFixed(1)}</p>
      </div>
      <div
        className="mb-2 flex items-center gap-0.5"
        aria-label={`${average.toFixed(1)} out of 5 stars`}
      >
        {Array.from({ length: 5 }).map((_, index) => {
          const threshold = ((index + 1) / 5) * 100;
          const filled = fill >= threshold;
          const partial = fill > index * 20 && fill < threshold;
          return (
            <Star
              key={index}
              className={cn(
                "h-4 w-4 transition-colors duration-300",
                filled
                  ? "fill-tertiary text-tertiary drop-shadow-[0_0_6px_rgba(255,201,160,0.5)]"
                  : partial
                    ? "fill-tertiary/40 text-tertiary"
                    : "text-white/20",
              )}
              aria-hidden
            />
          );
        })}
      </div>
      <p className="text-xs text-on-surface-variant/80">
        {formatRatingCount(count)} public ratings on listing
      </p>
    </div>
  );
}

type Props = {
  ratings: StoreListingRatings | null | undefined;
};

export function StoreRatingsCard({ ratings }: Props) {
  const play = ratings?.stores?.play_store;
  const app = ratings?.stores?.app_store;

  if (!play && !app) {
    return (
      <section className="glass-panel p-5">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-on-surface-variant/80">
          Store listing ratings
        </h3>
        <p className="text-sm text-on-surface-variant">Public store averages unavailable.</p>
      </section>
    );
  }

  return (
    <section className="glass-panel glass-panel-interactive p-5">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-widest text-on-surface-variant/80">
        Store listing ratings
      </h3>
      <p className="mb-4 text-xs text-on-surface-variant/75">
        {ratings?.disclaimer ?? "Overall ratings as shown on each store's public listing."}
      </p>
      <div className="space-y-3">
        {play ? (
          <StoreRatingRow
            label={play.label ?? "Play Store"}
            average={play.average_rating}
            count={play.rating_count}
          />
        ) : null}
        {app ? (
          <StoreRatingRow
            label={app.label ?? "App Store"}
            average={app.average_rating}
            count={app.rating_count}
          />
        ) : null}
      </div>
    </section>
  );
}
