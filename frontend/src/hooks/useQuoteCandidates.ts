import { useEffect, useState } from "react";

import { getRunQuotes } from "../api/client";
import type { QuoteCandidate } from "../types/quotes";

export function useQuoteCandidates(runId: string | undefined, perTheme = 5) {
  const [data, setData] = useState<QuoteCandidate[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const load = async () => {
      try {
        let resolvedId = runId;
        if (!resolvedId) {
          const { getLatestRun } = await import("../api/client");
          const latest = await getLatestRun();
          resolvedId = latest.run.run_id;
        }
        if (!resolvedId) throw new Error("No run selected.");
        const payload = await getRunQuotes(resolvedId, perTheme);
        if (active) {
          setData(payload.quote_candidates);
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setData(null);
          setError(err instanceof Error ? err.message : "Failed to load quotes.");
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [runId, perTheme]);

  return { data, loading, error };
}
