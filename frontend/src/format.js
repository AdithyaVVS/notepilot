export function formatDay(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function planStatus(note) {
  if (!note.has_plan) return { label: "Not analyzed yet", tone: "idle" };
  if (note.task_count === 0) return { label: "No tasks found", tone: "idle" };
  if (note.done_count === note.task_count) return { label: "All done", tone: "done" };
  return { label: `${note.done_count} of ${note.task_count} done`, tone: "open" };
}
