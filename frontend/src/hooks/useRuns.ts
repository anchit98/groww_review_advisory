import { useCallback, useEffect, useState } from "react";

import { getLatestRun, getRun, getRunPulse, getRuns } from "../api/client";
import type { RunSummary, WeeklyPulse } from "../types/pulse";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export function useRunList() {
  const [state, setState] = useState<AsyncState<RunSummary[]>>({
    data: null,
    loading: true,
    error: null,
  });

  const reload = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    getRuns()
      .then((payload) => setState({ data: payload.runs, loading: false, error: null }))
      .catch((err: Error) =>
        setState({ data: null, loading: false, error: err.message }),
      );
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { ...state, reload };
}

export function useSelectedRun(runId: string | undefined) {
  const [summary, setSummary] = useState<AsyncState<RunSummary>>({
    data: null,
    loading: true,
    error: null,
  });
  const [pulse, setPulse] = useState<AsyncState<WeeklyPulse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;
    const load = async () => {
      setSummary({ data: null, loading: true, error: null });
      setPulse({ data: null, loading: true, error: null });
      try {
        let id = runId;
        if (!id) {
          try {
            const latest = await getLatestRun();
            id = latest.run.run_id;
          } catch {
            const listed = await getRuns();
            id = listed.runs[0]?.run_id;
          }
        }
        if (!id) throw new Error("No runs available.");
        const [runPayload, pulsePayload] = await Promise.all([
          getRun(id),
          getRunPulse(id),
        ]);
        if (!active) return;
        setSummary({ data: runPayload.run, loading: false, error: null });
        setPulse({
          data: pulsePayload.weekly_pulse,
          loading: false,
          error: null,
        });
      } catch (err) {
        if (!active) return;
        const message = err instanceof Error ? err.message : "Failed to load run.";
        setSummary({ data: null, loading: false, error: message });
        setPulse({ data: null, loading: false, error: message });
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [runId]);

  return { summary, pulse };
}
