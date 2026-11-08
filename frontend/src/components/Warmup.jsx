import { useCallback, useEffect, useState } from "react";

import { api } from "../api.js";

// The free host puts every service to sleep after 15 idle minutes. One call to the
// gateway wakes all three at once, so the user waits once instead of three times.
export function useWarmup() {
  const [state, setState] = useState({ phase: "waking", failed: [], seconds: 0 });

  const run = useCallback(async () => {
    setState({ phase: "waking", failed: [], seconds: 0 });
    try {
      const result = await api.warmup();
      const failed = Object.entries(result.services)
        .filter(([, service]) => service.status !== "ok")
        .map(([name]) => name);
      setState((s) => ({ ...s, phase: failed.length ? "partial" : "ready", failed }));
    } catch {
      setState((s) => ({ ...s, phase: "unreachable", failed: [] }));
    }
  }, []);

  useEffect(() => {
    run();
  }, [run]);

  useEffect(() => {
    if (state.phase !== "waking") return undefined;
    const timer = setInterval(() => setState((s) => ({ ...s, seconds: s.seconds + 1 })), 1000);
    return () => clearInterval(timer);
  }, [state.phase]);

  return { ...state, retry: run };
}

export function WarmupBanner({ phase, failed, seconds, retry }) {
  if (phase === "ready") return null;
  // Locally the services answer instantly, so don't flash a banner for a split second.
  if (phase === "waking" && seconds < 2) return null;

  if (phase === "waking") {
    return (
      <div className="banner" role="status">
        <div className="banner-text">
          <strong>Waking up the services ({seconds}s)</strong>
          <span>
            The free host puts them to sleep after 15 minutes without use, so the first
            load can take up to a minute.
          </span>
        </div>
        <div className="banner-bar" aria-hidden="true" />
      </div>
    );
  }

  const message =
    phase === "partial"
      ? `These services didn't respond: ${failed.join(", ")}. Some features won't work until they wake up.`
      : "Can't reach the NotePilot server. Check your connection, then try again.";

  return (
    <div className="banner banner-problem" role="alert">
      <div className="banner-text">
        <strong>{message}</strong>
      </div>
      <button type="button" className="btn btn-light" onClick={retry}>
        Try again
      </button>
    </div>
  );
}
