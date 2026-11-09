import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api.js";
import TaskRow from "../components/TaskRow.jsx";
import Topbar from "../components/Topbar.jsx";
import { buildSegments, formatDay, sourceLabel } from "../format.js";

export default function NotePage() {
  const { id } = useParams();
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState(null); // an analysis that is not saved yet
  const [selected, setSelected] = useState(-1);
  const [busy, setBusy] = useState(""); // "", "ai", "sample" or "saving"
  const [message, setMessage] = useState("");
  const [usageVersion, setUsageVersion] = useState(0);
  const activeMark = useRef(null);

  useEffect(() => {
    setNote(null);
    setDraft(null);
    setSelected(-1);
    setError("");
    api
      .getNote(id)
      .then(setNote)
      .catch((problem) => setError(problem.message));
  }, [id]);

  // Scroll the highlighted quote into view when another task is chosen.
  useEffect(() => {
    if (selected >= 0 && activeMark.current) {
      activeMark.current.scrollIntoView({ block: "nearest" });
    }
  }, [selected]);

  async function analyze(mode) {
    setMessage("");
    setBusy(mode);
    try {
      const result = await api.analyze(note.body, { mode });
      setDraft(result);
      setSelected(result.action_items.length > 0 ? 0 : -1);
    } catch (problem) {
      setMessage(problem.message);
    } finally {
      setBusy("");
      setUsageVersion((v) => v + 1);
    }
  }

  async function savePlan() {
    setMessage("");
    setBusy("saving");
    try {
      await api.savePlan(note.id, { summary: draft.summary, items: draft.action_items });
      setNote(await api.getNote(note.id));
      setDraft(null);
      setSelected(-1);
    } catch (problem) {
      setMessage(problem.message);
    } finally {
      setBusy("");
    }
  }

  async function toggle(task, done) {
    const before = note.tasks;
    setNote({ ...note, tasks: before.map((t) => (t.id === task.id ? { ...t, done } : t)) });
    try {
      await api.setTaskDone(task.id, done);
    } catch (problem) {
      setNote({ ...note, tasks: before });
      setMessage(problem.message);
    }
  }

  const saved = note && note.summary !== null;
  const showing = draft ? "draft" : saved ? "saved" : "none";
  const items = draft ? draft.action_items : note ? note.tasks : [];
  const summary = draft ? draft.summary : note ? note.summary : null;
  const pieces = note
    ? buildSegments(
        note.body,
        items.map((item) => ({ start: item.evidence_start, end: item.evidence_end })),
        selected,
      )
    : [];
  const working = busy !== "";

  return (
    <>
      <Topbar usageVersion={usageVersion} />
      <main className="page page-wide">
        <Link className="back" to="/">
          All notes
        </Link>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {!note && !error && <p className="status-line">Loading the note...</p>}

        {note && (
          <>
            <h1 className="note-heading">{note.title}</h1>
            <p className="note-meta">Saved {formatDay(note.created_at)}</p>

            <div className="split">
              <div className="sheet note-sheet">
                <p className="note-body">
                  {pieces.map((piece, i) =>
                    piece.kind === "plain" ? (
                      <span key={i}>{piece.text}</span>
                    ) : piece.kind === "active" ? (
                      <mark key={i} className="ink" ref={activeMark}>
                        {piece.text}
                      </mark>
                    ) : (
                      <mark key={i} className="faint" onClick={() => setSelected(piece.index)}>
                        {piece.text}
                      </mark>
                    ),
                  )}
                </p>
              </div>

              <section className="plan" aria-label="Tasks from this note">
                {showing === "none" && (
                  <div className="plan-start">
                    <h2>Find the tasks in this note</h2>
                    <p>
                      Each task will point to the exact words it came from, so you can
                      check it before you trust it.
                    </p>
                    <div className="plan-actions">
                      <button
                        type="button"
                        className="btn btn-primary"
                        disabled={working}
                        onClick={() => analyze("ai")}
                      >
                        {busy === "ai" ? "Reading your note..." : "Analyze with AI"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-quiet"
                        disabled={working}
                        onClick={() => analyze("sample")}
                      >
                        {busy === "sample" ? "Reading..." : "Try sample mode"}
                      </button>
                    </div>
                    <p className="fineprint">
                      AI sends this note's text to Google's Gemini and uses one of your
                      daily analyses. Sample mode uses simple rules and no allowance.
                    </p>
                  </div>
                )}

                {showing !== "none" && (
                  <>
                    {draft && (
                      <div className="draft-bar">
                        <div>
                          <strong>Not saved yet</strong>
                          <span>{sourceLabel(draft.source)}</span>
                        </div>
                        <div className="plan-actions">
                          <button
                            type="button"
                            className="btn btn-primary btn-small"
                            disabled={working}
                            onClick={savePlan}
                          >
                            {busy === "saving" ? "Saving..." : "Save plan"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-quiet btn-small"
                            disabled={working}
                            onClick={() => {
                              setDraft(null);
                              setSelected(-1);
                            }}
                          >
                            Discard
                          </button>
                        </div>
                      </div>
                    )}

                    {summary && <p className="plan-summary">{summary}</p>}

                    {items.length === 0 ? (
                      <p className="empty">
                        No action items found. A note with only facts and decisions has
                        nothing to do.
                      </p>
                    ) : (
                      <ul className="task-list">
                        {items.map((item, index) => (
                          <TaskRow
                            key={item.id ?? index}
                            task={item}
                            active={index === selected}
                            onSelect={() => setSelected(index === selected ? -1 : index)}
                            onToggle={showing === "saved" ? toggle : undefined}
                          />
                        ))}
                      </ul>
                    )}

                    {draft && draft.dropped_items > 0 && (
                      <p className="fineprint">
                        {draft.dropped_items} possible{" "}
                        {draft.dropped_items === 1 ? "task was" : "tasks were"} left out
                        because they could not be matched to words in your note.
                      </p>
                    )}

                    {showing === "saved" && (
                      <div className="plan-again">
                        <p className="fineprint">
                          Analyzing again replaces these tasks and your ticks.
                        </p>
                        <div className="plan-actions">
                          <button
                            type="button"
                            className="btn btn-quiet btn-small"
                            disabled={working}
                            onClick={() => analyze("ai")}
                          >
                            {busy === "ai" ? "Reading your note..." : "Analyze again with AI"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-quiet btn-small"
                            disabled={working}
                            onClick={() => analyze("sample")}
                          >
                            Sample mode
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {message && (
                  <p className="form-error" role="alert">
                    {message}
                  </p>
                )}
              </section>
            </div>
          </>
        )}
      </main>
    </>
  );
}
