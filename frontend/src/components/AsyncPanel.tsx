import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../lib/cn";

type Props = {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
};

export function AsyncPanel({
  loading,
  error,
  empty,
  emptyMessage = "No data available.",
  children,
}: Props) {
  if (loading) {
    return (
      <div className="glass-panel flex flex-col items-center justify-center gap-4 p-8 text-on-surface-variant sm:p-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
        <p className="glass-shimmer rounded-lg px-6 py-1 text-sm">Loading insights…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div
        className={cn(
          "glass-panel border-error/30 p-6 text-error",
          "bg-gradient-to-br from-error/10 to-transparent",
        )}
      >
        <p className="font-semibold">Unable to load data</p>
        <p className="mt-2 text-sm opacity-90">{error}</p>
      </div>
    );
  }
  if (empty) {
    return (
      <div className="glass-panel p-10 text-center text-on-surface-variant">{emptyMessage}</div>
    );
  }
  return <>{children}</>;
}
