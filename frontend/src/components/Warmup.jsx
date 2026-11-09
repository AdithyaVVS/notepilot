import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api.js";

// The free host puts every service to sleep after 15 idle minutes. One call to the
// gateway wakes all three at once, so the user waits once instead of three times.
export function useWarmup() {
  const [state, setState] = useState({ phase: "waking", failed: [], seconds: 0 });

  const latest = useRef(0);

  // A sleeping gateway fails the very first request (the host answers before the app
  // is awake), and a service that is still starting answers 502. Either way, keep
  // trying every 3 seconds for up to 3 minutes before showing a problem.
  const run = useCallback(async () => {
    const mine = ++latest.current;
    const giveUpAt = Date.now() + 180000;
    setState({ phase: "waking", failed: [], seconds: 0 });
    for (;;) {
      try {
        const result = await api.warmup();
        if (latest.current !== mine) return;
        const failed = Object.entries(result.services)
          .filter(([, service]) => service.status !== "ok")
          .map(([name]) => name);
        if (failed.length === 0 || Date.now() + 3000 > giveUpAt) {
          setState((s) => ({ ...s, phase: failed.length ? "partial" : "ready", failed }));
          return;
        }
        // Some services are still waking up: ask again instead of showing a problem.
        await new Promise((resolve) => setTimeout(resolve, 3000));
        continue;
      } catch {
        if (latest.current !== mine) return;
        if (Date.now() + 3000 > giveUpAt) {
          setState((s) => ({ ...s, phase: "unreachable", failed: [] }));
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
  }, []);

  useEffect(() => {
    run();
    return () => {
      latest.current += 1; // stop a retry loop that belongs to an unmounted page
    };
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
