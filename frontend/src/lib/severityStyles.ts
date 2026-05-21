import type { Severity } from "./severity";

export const severityStyles: Record<
  Severity,
  { accent: string; glow: string; chip: string; label: string }
> = {
  CRITICAL: {
    accent: "from-error/80 to-error/20",
    glow: "shadow-[0_0_28px_rgba(255,184,176,0.22)]",
    chip: "border-error/25 bg-error/10 text-error",
    label: "text-error",
  },
  WARNING: {
    accent: "from-tertiary/80 to-tertiary/15",
    glow: "shadow-[0_0_28px_rgba(255,201,160,0.18)]",
    chip: "border-tertiary/25 bg-tertiary/10 text-tertiary",
    label: "text-tertiary",
  },
  CONCERN: {
    accent: "from-primary/70 to-primary/10",
    glow: "shadow-[0_0_28px_rgba(173,198,255,0.15)]",
    chip: "border-primary/25 bg-primary/10 text-primary",
    label: "text-primary",
  },
};
