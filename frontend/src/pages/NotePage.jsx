import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api.js";
import Topbar from "../components/Topbar.jsx";
import { formatDay } from "../format.js";

export default function NotePage() {
  const { id } = useParams();
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setNote(null);
    api
      .getNote(id)
      .then(setNote)
      .catch((problem) => setError(problem.message));
  }, [id]);

  return (
    <>
      <Topbar />
      <main className="page">
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
            <div className="sheet note-sheet">
              <p className="note-body">{note.body}</p>
            </div>
          </>
        )}
      </main>
    </>
  );
}
