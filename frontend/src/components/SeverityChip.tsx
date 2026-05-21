import type { Severity } from "../lib/severity";
import { cn } from "../lib/cn";

const styles: Record<Severity, string> = {
  CRITICAL: "border-error/40 bg-error/15 text-error",
  WARNING: "border-tertiary/40 bg-tertiary/15 text-tertiary",
  CONCERN: "border-white/15 bg-white/8 text-on-surface-variant",
};

type Props = { severity: Severity; className?: string };

export function SeverityChip({ severity, className = "" }: Props) {
  return (
    <span className={cn("glass-chip", styles[severity], className)}>{severity}</span>
  );
}
