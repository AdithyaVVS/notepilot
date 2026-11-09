import { useEffect, useState } from "react";

import { api } from "../api.js";
import TaskRow from "../components/TaskRow.jsx";
import Topbar from "../components/Topbar.jsx";

const TABS = [
  ["open", "Open"],
  ["done", "Done"],
  ["all", "All"],
];

export default function TasksPage() {
  const [status, setStatus] = useState("open");
  const [tasks, setTasks] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setTasks(null);
    setError("");
    api
      .listTasks(status)
      .then(setTasks)
      .catch((problem) => setError(problem.message));
  }, [status]);

  // The row stays in the list after a tick so it can be undone; the next load drops it.
  async function toggle(task, done) {
    const before = tasks;
    setTasks(before.map((t) => (t.id === task.id ? { ...t, done } : t)));
    try {
      await api.setTaskDone(task.id, done);
    } catch (problem) {
      setTasks(before);
      setError(problem.message);
    }
  }

  return (
    <>
      <Topbar />
      <main className="page">
        <h1 className="note-heading">Tasks</h1>
        <p className="note-meta">Every task from every analyzed note, in one place.</p>

        <div className="tabs" role="group" aria-label="Show tasks">
          {TABS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`tab${status === value ? " tab-on" : ""}`}
              aria-pressed={status === value}
              onClick={() => setStatus(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {tasks === null && !error && <p className="status-line">Loading your tasks...</p>}
        {tasks !== null && tasks.length === 0 && (
          <p className="empty">
            {status === "open"
              ? "Nothing open. Analyze a note to get tasks."
              : status === "done"
                ? "No finished tasks yet."
                : "No tasks yet. Analyze a note to get some."}
          </p>
        )}
        {tasks !== null && tasks.length > 0 && (
          <ul className="task-list task-board">
            {tasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                onToggle={toggle}
                noteLink={{ to: `/notes/${task.note_id}`, title: task.note_title }}
              />
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
