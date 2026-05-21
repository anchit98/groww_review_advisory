import { Gauge, Headphones, Wallet } from "lucide-react";

import { resolveBulletPoints } from "../lib/bullets";
import { cn } from "../lib/cn";
import { severityStyles } from "../lib/severityStyles";
import { themeIconKey, type Severity } from "../lib/severity";
import {
  THEME_CARD_INSIGHT_COUNT,
  THEME_CARD_SUMMARY_LINES,
  THEME_CARD_TITLE_LINES,
} from "../lib/themesPageLayout";
import { CardFixedLineList, CardFixedLines } from "./CardFixedLines";
import { SeverityChip } from "./SeverityChip";

const icons = {
  support: Headphones,
  performance: Gauge,
  fees: Wallet,
  default: Gauge,
};

type Props = {
  rank: number;
  themeName: string;
  summary: string;
  bulletPoints?: string[];
  severity: Severity;
};

export function ThemeSpotlightCard({
  rank,
  themeName,
  summary,
  bulletPoints,
  severity,
}: Props) {
  const Icon = icons[themeIconKey(themeName)];
  const style = severityStyles[severity];
  const bullets = resolveBulletPoints(bulletPoints, summary, THEME_CARD_INSIGHT_COUNT);

  return (
    <article
      className={cn(
        "glass-panel glass-panel-interactive relative flex h-full flex-col overflow-hidden p-0",
        style.glow,
      )}
    >
      <div className={cn("absolute inset-y-0 left-0 w-1 bg-gradient-to-b", style.accent)} aria-hidden />

      <div className="flex flex-1 flex-col p-4 pl-5 sm:p-5 sm:pl-6">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-sm font-bold tabular-nums",
              style.chip,
            )}
          >
            #{rank}
          </span>
          <span className={cn("glass-icon-well !h-9 !w-9 shrink-0 rounded-xl", style.label)}>
            <Icon className="h-4 w-4" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            {/* Title + severity chip share one header block (chip always below full-width title). */}
            <div className="flex flex-wrap items-start gap-2">
              <CardFixedLines
                as="h3"
                text={themeName}
                lineCount={THEME_CARD_TITLE_LINES}
                className="w-full text-base font-semibold text-on-surface"
              />
              <SeverityChip severity={severity} />
            </div>
            <CardFixedLines
              text={summary}
              lineCount={THEME_CARD_SUMMARY_LINES}
              className="mt-2 text-sm text-on-surface-variant/85"
            />
          </div>
        </div>

        <div className="mt-4 flex-1 border-t border-white/8 pt-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant/70">
            What we are hearing
          </p>
          <CardFixedLineList
            items={bullets}
            lineCount={THEME_CARD_INSIGHT_COUNT}
            itemClassName={style.chip}
          />
        </div>
      </div>
    </article>
  );
}
