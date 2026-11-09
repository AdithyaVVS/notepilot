import { Link } from "react-router-dom";

import { formatDue } from "../format.js";

// One task. Used on the note page (click selects, checkbox ticks) and on the board.
export default function TaskRow({ task, active = false, onSelect, onToggle, noteLink = null }) {
  const due = formatDue(task);
  const done = Boolean(task.done);

  const content = (
    <>
      <span className="task-title">{task.task}</span>
      <span className="task-facts">
        {task.owner && <span>{task.owner}</span>}
        {due && <span>Due {due}</span>}
        {task.priority === "high" && <span className="urgent">High priority</span>}
        {task.priority === "low" && <span>Low priority</span>}
      </span>
      {active && <q className="task-quote">{task.evidence}</q>}
    </>
  );

  return (
    <li className={`task${active ? " task-active" : ""}${done ? " task-done" : ""}`}>
      {onToggle && (
        <input
          type="checkbox"
          className="task-check"
          checked={done}
          onChange={(e) => onToggle(task, e.target.checked)}
          aria-label={`Mark done: ${task.task}`}
        />
      )}
      {onSelect ? (
        <button
          type="button"
          className="task-body"
          aria-pressed={active}
          onClick={() => onSelect()}
        >
          {content}
        </button>
      ) : (
        <div className="task-body">
          {content}
          {noteLink && (
            <Link className="task-from" to={noteLink.to}>
              From {noteLink.title}
            </Link>
          )}
        </div>
      )}
    </li>
  );
}
