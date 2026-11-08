import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth.jsx";
import { Wordmark } from "../components/Mark.jsx";

function Demo() {
  return (
    <div className="sheet demo" aria-label="Example of a note with its tasks">
      <div className="demo-row">
        <p className="demo-line demo-title">Standup notes, Tuesday</p>
      </div>
      <div className="demo-row">
        <p className="demo-line">
          Priya will{" "}
          <mark className="ink" style={{ "--delay": "500ms" }}>
            send the revised budget to finance by Friday
          </mark>
          .
        </p>
        <div className="margin-note">
          <strong>Send the revised budget to finance</strong>
          <span className="margin-facts">
            <span>Priya</span>
            <span>Due Friday</span>
          </span>
        </div>
      </div>
      <div className="demo-row">
        <p className="demo-line">
          Rahul needs to{" "}
          <mark className="ink" style={{ "--delay": "1000ms" }}>
            fix the login bug ASAP
          </mark>
          , before next week.
        </p>
        <div className="margin-note">
          <strong>Fix the login bug</strong>
          <span className="margin-facts">
            <span>Rahul</span>
            <span>Due Monday</span>
            <span className="urgent">High priority</span>
          </span>
        </div>
      </div>
      <div className="demo-row">
        <p className="demo-line">We decided to postpone the launch.</p>
        <div className="margin-note margin-note-quiet">Decision, not a task. Left out.</div>
      </div>
    </div>
  );
}

export default function AuthPage({ waking }) {
  const { status, signIn, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (status === "authed") return <Navigate to="/" replace />;

  const creating = mode === "register";

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (creating) await register(email, password);
      else await signIn(email, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setMode(creating ? "signin" : "register");
    setError("");
  }

  return (
    <main className="auth">
      <section className="auth-demo">
        <h1 className="hero">Turn messy notes into a task list you can check.</h1>
        <p className="hero-sub">
          Every task points back to the exact words in your note it came from, so you can
          verify it before you trust it.
        </p>
        <Demo />
      </section>

      <section className="auth-panel">
        <form className="auth-form" onSubmit={submit}>
          <Wordmark />
          <h2>{creating ? "Create your account" : "Sign in"}</h2>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete={creating ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={creating ? 8 : undefined}
              required
            />
            {creating && <small>At least 8 characters.</small>}
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary" type="submit" disabled={busy || waking}>
            {waking ? "Waking the services..." : busy ? "One moment..." : creating ? "Create account" : "Sign in"}
          </button>

          <p className="switch">
            {creating ? "Already have an account?" : "New here?"}{" "}
            <button type="button" className="link" onClick={switchMode}>
              {creating ? "Sign in" : "Create an account"}
            </button>
          </p>

          <p className="fineprint">
            This is a demo on free hosting. Don't enter confidential notes: text you
            analyze with AI is sent to Google's Gemini API.
          </p>
        </form>
      </section>
    </main>
  );
}
