import { cn } from "../lib/cn";
import type { Severity } from "../lib/severity";
import { SeverityChip } from "./SeverityChip";

type Props = {
  themeName: string;
  quote: string;
  severity: Severity;
  compact?: boolean;
  source?: string;
  rating?: number;
  reviewDate?: string;
};

export function QuoteCard({
  themeName,
  quote,
  severity,
  compact = false,
  source,
  rating,
  reviewDate,
}: Props) {
  const meta =
    [source, rating != null ? `${rating}★` : null, reviewDate].filter(Boolean).join(" · ") ||
    undefined;

  if (compact) {
    return (
      <article
        className={cn(
          "glass-panel px-3 py-3 transition-all duration-300 sm:px-4",
          "hover:border-white/20 hover:shadow-[var(--glass-shadow-hover)]",
        )}
      >
        {meta ? (
          <p className="mb-2 text-xs text-on-surface-variant/80">{meta}</p>
        ) : null}
        <blockquote className="text-base italic leading-relaxed text-on-surface/95">
          “{quote}”
        </blockquote>
      </article>
    );
  }

  return (
    <article className="glass-panel glass-panel-interactive grid gap-4 p-5 md:grid-cols-[220px_1fr]">
      <div className="space-y-3">
        <SeverityChip severity={severity} />
        <div>
          <p className="text-xs uppercase tracking-widest text-on-surface-variant/70">Theme</p>
          <p className="font-medium text-on-surface">{themeName}</p>
        </div>
        {meta ? <p className="text-xs text-on-surface-variant/75">{meta}</p> : null}
      </div>
      <blockquote className="text-lg italic leading-relaxed text-on-surface/95">
        “{quote}”
      </blockquote>
    </article>
  );
}
