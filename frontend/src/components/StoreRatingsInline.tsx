import { Star } from "lucide-react";

import { cn } from "../lib/cn";
import type { StoreListingRatings } from "../lib/ratings";

type Props = {
  ratings: StoreListingRatings | null | undefined;
  className?: string;
};

function InlineRating({ label, average }: { label: string; average: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 tabular-nums">
      <span className="text-on-surface-variant/90">{label}</span>
      <span className="font-semibold text-on-surface">{average.toFixed(1)}</span>
      <Star className="h-3.5 w-3.5 fill-tertiary text-tertiary" aria-hidden />
    </span>
  );
}

export function StoreRatingsInline({ ratings, className }: Props) {
  const play = ratings?.stores?.play_store;
  const app = ratings?.stores?.app_store;

  if (!play && !app) return null;

  return (
    <div
      className={cn(
        "glass-badge flex flex-wrap items-center gap-x-3 gap-y-1 sm:ml-auto sm:justify-end",
        className,
      )}
      aria-label="Public store listing ratings"
    >
      {play ? (
        <InlineRating label={play.label ?? "Play Store"} average={play.average_rating} />
      ) : null}
      {play && app ? (
        <span className="hidden text-on-surface-variant/40 sm:inline" aria-hidden>
          ·
        </span>
      ) : null}
      {app ? (
        <InlineRating label={app.label ?? "App Store"} average={app.average_rating} />
      ) : null}
    </div>
  );
}
