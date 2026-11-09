import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api.js";

const WAKE_EVERY_MS = 45000;

// Free hosting wakes a sleeping service when a browser asks for it, but not when the
// gateway asks. So the gateway tells us which services are down, and this page makes
// the request itself. The answer is not needed (no-cors), only the request.
function wakeSleepers(services, lastWoken) {
  for (const [name, info] of Object.entries(services)) {
    const url = info.wake_url;
    if (info.status === "ok" || !url || !url.startsWith("https://")) continue;
    if (Date.now() - (lastWoken[name] || 0) < WAKE_EVERY_MS) continue;
    lastWoken[name] = Date.now();
    fetch(url, { mode: "no-cors", cache: "no-store" }).catch(() => {});
  }
}

// The free host puts every service to sleep after 15 idle minutes. The first visit
// asks the gateway for the state of all three, wakes the sleeping ones, and keeps
// checking every 3 seconds (up to 3 minutes) before showing a problem.
export function useWarmup() {
  const [state, setState] = useState({ phase: "waking", failed: [], seconds: 0 });

  const latest = useRef(0);

  const run = useCallback(async () => {
    const mine = ++latest.current;
    const giveUpAt = Date.now() + 180000;
    const lastWoken = {};
    setState({ phase: "waking", failed: [], seconds: 0 });
    for (;;) {
      let result = null;
      try {
        result = await api.warmup();
      } catch {
        /* the gateway itself may be asleep: asking again is what wakes it */
      }
      if (latest.current !== mine) return;

      if (result) {
        const failed = Object.entries(result.services)
          .filter(([, service]) => service.status !== "ok")
          .map(([name]) => name);
        if (failed.length === 0) {
          setState((s) => ({ ...s, phase: "ready", failed: [] }));
          return;
        }
        if (Date.now() + 3000 > giveUpAt) {
          setState((s) => ({ ...s, phase: "partial", failed }));
          return;
        }
        wakeSleepers(result.services, lastWoken);
      } else if (Date.now() + 3000 > giveUpAt) {
        setState((s) => ({ ...s, phase: "unreachable", failed: [] }));
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 3000));
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
