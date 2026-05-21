import { AlertTriangle, Layers } from "lucide-react";

import { cn } from "../lib/cn";

type Props = {
  themeCount: number;
  actionCount: number;
};

export function ThemesOverviewStrip({ themeCount, actionCount }: Props) {
  const stats = [
    {
      label: "Priority themes",
      value: String(themeCount),
      icon: Layers,
      tone: "text-primary",
    },
    {
      label: "Action items",
      value: String(actionCount),
      icon: AlertTriangle,
      tone: "text-tertiary",
    },
  ];

  return (
    <div className="glass-panel grid gap-3 p-4 sm:grid-cols-2">
      {stats.map(({ label, value, icon: Icon, tone }) => (
        <div key={label} className="glass-inset flex items-center gap-3 rounded-xl px-3 py-2.5">
          <span className={cn("glass-icon-well !h-9 !w-9", tone)}>
            <Icon className="h-4 w-4" aria-hidden />
          </span>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant/70">
              {label}
            </p>
            <p className={cn("text-xl font-bold tabular-nums leading-none", tone)}>{value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
