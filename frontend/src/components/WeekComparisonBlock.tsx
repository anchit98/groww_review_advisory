import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import {
  formatDelta,
  isImprovement,
  type WeekComparison,
} from "../lib/weekComparison";
import { cn } from "../lib/cn";

type Props = {
  comparison: WeekComparison | null;
  loading?: boolean;
};

export function WeekComparisonBlock({ comparison, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-inset mt-3 px-3 py-2.5">
        <p className="glass-shimmer text-[10px] uppercase tracking-wider text-on-surface-variant/60">
          Loading prior week…
        </p>
      </div>
    );
  }

  if (!comparison?.metrics.length) {
    return (
      <div className="glass-inset mt-3 px-3 py-2.5">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant/70">
          vs prior week
        </p>
        <p className="mt-1 text-xs text-on-surface-variant/75">
          No earlier indexed week to compare.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-inset mt-3 px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant/70">
        vs {comparison.previousWeekLabel}
      </p>
      <ul className="mt-2 space-y-1.5">
        {comparison.metrics.map((metric) => {
          const improved = isImprovement(metric);
          const flat = metric.delta === 0;

          return (
            <li
              key={metric.label}
              className="flex items-center justify-between gap-2 text-xs"
            >
              <span className="text-on-surface-variant/85">{metric.label}</span>
              <span
                className={cn(
                  "inline-flex items-center gap-1 font-medium tabular-nums",
                  flat && "text-on-surface-variant/70",
                  !flat && improved === true && "text-primary",
                  !flat && improved === false && "text-error",
                )}
              >
                {flat ? (
                  <Minus className="h-3 w-3" aria-hidden />
                ) : improved ? (
                  <ArrowDown className="h-3 w-3" aria-hidden />
                ) : (
                  <ArrowUp className="h-3 w-3" aria-hidden />
                )}
                {formatDelta(metric)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
