import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Wordmark } from "./Mark.jsx";

export default function Topbar({ usageVersion = 0 }) {
  const { user, signOut } = useAuth();
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    api
      .usage()
      .then(setUsage)
      .catch(() => setUsage(null));
  }, [usageVersion]);

  const left = usage ? Math.max(usage.daily_limit - usage.used_today, 0) : 0;

  return (
    <header className="topbar">
      <div className="topbar-left">
        <Link to="/" className="brand" aria-label="NotePilot, all notes">
          <Wordmark />
        </Link>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>
            Notes
          </NavLink>
          <NavLink to="/tasks">Tasks</NavLink>
        </nav>
      </div>
      <div className="topbar-right">
        {usage && (
          <span className="usage" title="The AI allowance resets every day (UTC).">
            {left} of {usage.daily_limit} AI analyses left today
          </span>
        )}
        <span className="who">{user?.email}</span>
        <button type="button" className="btn btn-quiet btn-small" onClick={signOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}
