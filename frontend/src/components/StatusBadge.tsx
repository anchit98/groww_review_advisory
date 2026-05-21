import { statusTone } from "../lib/format";
import { cn } from "../lib/cn";

const toneClass = {
  ok: "border-primary/35 bg-primary/15 text-primary",
  warn: "border-tertiary/35 bg-tertiary/15 text-tertiary",
  error: "border-error/35 bg-error/15 text-error",
  muted: "border-white/15 bg-white/8 text-on-surface-variant",
};

type Props = { status?: string };

export function StatusBadge({ status = "unknown" }: Props) {
  const tone = statusTone(status);
  return (
    <span className={cn("glass-chip normal-case tracking-normal", toneClass[tone])}>
      {status}
    </span>
  );
}
