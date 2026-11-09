export function formatDay(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function planStatus(note) {
  if (!note.has_plan) return { label: "Not analyzed yet", tone: "idle" };
  if (note.task_count === 0) return { label: "No tasks found", tone: "idle" };
  if (note.done_count === note.task_count) return { label: "All done", tone: "done" };
  return { label: `${note.done_count} of ${note.task_count} done`, tone: "open" };
}

// "2026-11-13" -> "Fri, Nov 13". Falls back to the words the note used ("by Friday").
export function formatDue(item) {
  if (item.deadline) {
    const [year, month, day] = item.deadline.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  }
  return item.deadline_text || null;
}

export function sourceLabel(source) {
  if (source === "cache") return "Reused from an earlier analysis of this exact text. No AI allowance used.";
  if (source === "sample") return "Sample mode: simple rules, not AI. It finds fewer tasks than the real thing.";
  return "Analyzed by Google Gemini.";
}

// Cuts the note into pieces so the evidence for each task can be highlighted.
// The active task's quote is always marked; the others only if they do not overlap.
export function buildSegments(body, spans, activeIndex = -1) {
  const valid = (s) => s && s.start >= 0 && s.end > s.start && s.end <= body.length;
  const chosen = [];
  if (valid(spans[activeIndex])) {
    chosen.push({ ...spans[activeIndex], index: activeIndex, kind: "active" });
  }
  spans.forEach((span, index) => {
    if (index === activeIndex || !valid(span)) return;
    if (chosen.some((c) => span.start < c.end && c.start < span.end)) return;
    chosen.push({ ...span, index, kind: "faint" });
  });
  chosen.sort((a, b) => a.start - b.start);

  const pieces = [];
  let at = 0;
  for (const c of chosen) {
    if (c.start > at) pieces.push({ text: body.slice(at, c.start), kind: "plain" });
    pieces.push({ text: body.slice(c.start, c.end), kind: c.kind, index: c.index });
    at = c.end;
  }
  if (at < body.length) pieces.push({ text: body.slice(at), kind: "plain" });
  return pieces;
}
