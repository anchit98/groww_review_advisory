import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

import { useRunList, useSelectedRun } from "../hooks/useRuns";

type RunContextValue = {
  runId?: string;
  setRunId: (id: string) => void;
  weekOptions: { id: string; label: string }[];
  reportingLabel?: string;
  sourceMix?: Record<string, number>;
  storeListingRatings?: import("../types/pulse").StoreListingRatings | null;
  pulseLoading: boolean;
  pulseError: string | null;
  summaryLoading: boolean;
  pulse: import("../types/pulse").WeeklyPulse | null;
};

const RunContext = createContext<RunContextValue | null>(null);

export function RunProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const runId = params.get("week") ?? undefined;
  const { data: runs } = useRunList();
  const { summary, pulse } = useSelectedRun(runId);

  const weekOptions = useMemo(
    () =>
      (runs ?? []).map((run) => ({
        id: run.run_id,
        label: run.reporting_label || run.week_ending,
      })),
    [runs],
  );

  const setRunId = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("week", id);
    setParams(next);
  };

  const value: RunContextValue = {
    runId: summary.data?.run_id ?? runId,
    setRunId,
    weekOptions,
    reportingLabel: summary.data?.reporting_label,
    sourceMix: summary.data?.source_mix,
    storeListingRatings: summary.data?.store_listing_ratings,
    pulseLoading: pulse.loading,
    pulseError: pulse.error,
    summaryLoading: summary.loading,
    pulse: pulse.data,
  };

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRunContext() {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRunContext must be used within RunProvider");
  return ctx;
}
