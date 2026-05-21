import { Gauge, Headphones, Wallet } from "lucide-react";

import { resolveBulletPoints } from "../lib/bullets";
import { cn } from "../lib/cn";
import { themeIconKey, type Severity } from "../lib/severity";
import { BulletList } from "./BulletList";
import { SeverityChip } from "./SeverityChip";

const icons = {
  support: Headphones,
  performance: Gauge,
  fees: Wallet,
  default: Gauge,
};

type Props = {
  themeName: string;
  summary: string;
  bulletPoints?: string[];
  severity: Severity;
  featured?: boolean;
};

export function ThemeCard({ themeName, summary, bulletPoints, severity, featured }: Props) {
  const Icon = icons[themeIconKey(themeName)];
  const bullets = resolveBulletPoints(bulletPoints, summary);

  return (
    <article
      className={cn(
        "glass-panel glass-panel-interactive p-5",
        featured && "glass-panel-featured md:col-span-2",
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="glass-icon-well">
            <Icon className="h-5 w-5" aria-hidden />
          </span>
          <h3 className="text-lg font-semibold tracking-tight text-on-surface">{themeName}</h3>
        </div>
        <SeverityChip severity={severity} />
      </div>
      <p className="mb-3 text-sm font-medium text-on-surface/95">{summary}</p>
      <BulletList items={bullets} />
    </article>
  );
}
