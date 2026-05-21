import { useEffect, useMemo, useState } from "react";

import { getRun, getRunPulse } from "../api/client";
import {
  buildWeekComparison,
  findPreviousRunId,
  type WeekComparison,
} from "../lib/weekComparison";
import type { RunSummary, WeeklyPulse } from "../types/pulse";

type State = {
  comparison: WeekComparison | null;
  loading: boolean;
};

export function usePreviousWeekComparison(
  currentRunId: string | undefined,
  runs: RunSummary[] | null | undefined,
  currentPulse: WeeklyPulse | null,
  currentSourceMix?: Record<string, number>,
): State {
  const [state, setState] = useState<State>({ comparison: null, loading: false });

  const previousRunId = useMemo(() => {
    if (!currentRunId || !runs?.length) return null;
    return findPreviousRunId(currentRunId, runs);
  }, [currentRunId, runs]);

  useEffect(() => {
    if (!previousRunId || !currentPulse) {
      setState({ comparison: null, loading: false });
      return;
    }

    let active = true;
    setState({ comparison: null, loading: true });

    Promise.all([getRunPulse(previousRunId), getRun(previousRunId)])
      .then(([pulsePayload, runPayload]) => {
        if (!active) return;
        const comparison = buildWeekComparison(
          { pulse: currentPulse, sourceMix: currentSourceMix },
          {
            pulse: pulsePayload.weekly_pulse,
            sourceMix: runPayload.run.source_mix,
            weekLabel:
              runPayload.run.reporting_label ||
              pulsePayload.reporting_label ||
              previousRunId,
          },
        );
        setState({ comparison, loading: false });
      })
      .catch(() => {
        if (!active) return;
        setState({ comparison: null, loading: false });
      });

    return () => {
      active = false;
    };
  }, [previousRunId, currentPulse, currentSourceMix]);

  return state;
}
