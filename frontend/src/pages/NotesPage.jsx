import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api.js";
import Topbar from "../components/Topbar.jsx";
import { formatDay, planStatus } from "../format.js";

const MAX_BODY = 6000;

export default function NotesPage() {
  const navigate = useNavigate();
  const [notes, setNotes] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [confirming, setConfirming] = useState(null);

  useEffect(() => {
    api
      .listNotes()
      .then(setNotes)
      .catch((problem) => setLoadError(problem.message));
  }, []);

  async function create(event) {
    event.preventDefault();
    setFormError("");
    setSaving(true);
    try {
      const note = await api.createNote({ title, body });
      navigate(`/notes/${note.id}`);
    } catch (problem) {
      setFormError(problem.message);
      setSaving(false);
    }
  }

  async function remove(id) {
    try {
      await api.deleteNote(id);
      setNotes((list) => list.filter((note) => note.id !== id));
    } catch (problem) {
      setLoadError(problem.message);
    }
    setConfirming(null);
  }

  return (
    <>
      <Topbar />
      <main className="page">
        <form className="composer" onSubmit={create}>
          <input
            className="composer-title"
            aria-label="Note title"
            placeholder="Title, for example Weekly sync"
            value={title}
            maxLength={200}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="ruled"
            aria-label="Note text"
            placeholder="Paste your meeting notes, messages or to-do list here."
            value={body}
            maxLength={MAX_BODY}
            rows={7}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="composer-foot">
            <span className="count">
              {body.length} of {MAX_BODY} characters
            </span>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={saving || !title.trim() || !body.trim()}
            >
              {saving ? "Saving..." : "Save note"}
            </button>
          </div>
          {formError && (
            <p className="form-error" role="alert">
              {formError}
            </p>
          )}
        </form>

        <h2 className="section-title">Your notes</h2>
        {loadError && (
          <p className="form-error" role="alert">
            {loadError}
          </p>
        )}
        {notes === null && !loadError && <p className="status-line">Loading your notes...</p>}
        {notes !== null && notes.length === 0 && (
          <p className="empty">
            No notes yet. Paste a meeting note or a to-do list above and save it, then
            analyze it to get your tasks.
          </p>
        )}
        {notes !== null && notes.length > 0 && (
          <ul className="note-list">
            {notes.map((note) => {
              const status = planStatus(note);
              return (
                <li className="note-row" key={note.id}>
                  <Link className="note-link" to={`/notes/${note.id}`}>
                    <span className="note-title">{note.title}</span>
                    <span className="note-date">Updated {formatDay(note.updated_at)}</span>
                  </Link>
                  <span className={`chip chip-${status.tone}`}>{status.label}</span>
                  {confirming === note.id ? (
                    <span className="row-actions">
                      <button
                        type="button"
                        className="btn btn-danger btn-small"
                        onClick={() => remove(note.id)}
                      >
                        Delete note
                      </button>
                      <button
                        type="button"
                        className="btn btn-quiet btn-small"
                        onClick={() => setConfirming(null)}
                      >
                        Keep
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-quiet btn-small"
                      onClick={() => setConfirming(note.id)}
                      aria-label={`Delete ${note.title}`}
                    >
                      Delete
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </>
  );
}
