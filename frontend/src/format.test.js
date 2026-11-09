import { describe, expect, it } from "vitest";

import { buildSegments, formatDue, planStatus, sourceLabel } from "./format.js";

describe("planStatus", () => {
  it("says a note has not been analyzed when it has no plan", () => {
    expect(planStatus({ has_plan: false, task_count: 0, done_count: 0 })).toEqual({
      label: "Not analyzed yet",
      tone: "idle",
    });
  });

  it("says when an analysis found nothing to do", () => {
    expect(planStatus({ has_plan: true, task_count: 0, done_count: 0 }).label).toBe(
      "No tasks found",
    );
  });

  it("shows progress while tasks are open", () => {
    expect(planStatus({ has_plan: true, task_count: 3, done_count: 1 })).toEqual({
      label: "1 of 3 done",
      tone: "open",
    });
  });

  it("marks a finished note", () => {
    expect(planStatus({ has_plan: true, task_count: 2, done_count: 2 }).tone).toBe("done");
  });
});

describe("formatDue", () => {
  it("formats a resolved date", () => {
    const text = formatDue({ deadline: "2026-11-13", deadline_text: "by Friday" });
    expect(text).toMatch(/13/);
    expect(text).toMatch(/Fri/);
  });

  it("falls back to the words from the note", () => {
    expect(formatDue({ deadline: null, deadline_text: "next quarter" })).toBe("next quarter");
  });

  it("returns null when there is no deadline at all", () => {
    expect(formatDue({ deadline: null, deadline_text: null })).toBeNull();
  });
});

describe("sourceLabel", () => {
  it("explains each source", () => {
    expect(sourceLabel("ai")).toMatch(/Gemini/);
    expect(sourceLabel("cache")).toMatch(/No AI allowance/);
    expect(sourceLabel("sample")).toMatch(/not AI/);
  });
});

describe("buildSegments", () => {
  const body = "Priya will send the budget. Rahul fixes the bug.";

  it("splits the note around the active quote", () => {
    const pieces = buildSegments(body, [{ start: 11, end: 26 }], 0);
    expect(pieces.map((p) => p.kind)).toEqual(["plain", "active", "plain"]);
    expect(pieces[1].text).toBe("send the budget");
    expect(pieces.map((p) => p.text).join("")).toBe(body);
  });

  it("marks the other quotes faintly", () => {
    const pieces = buildSegments(
      body,
      [
        { start: 11, end: 26 },
        { start: 34, end: 47 },
      ],
      1,
    );
    expect(pieces.map((p) => p.kind)).toEqual(["plain", "faint", "plain", "active", "plain"]);
    expect(pieces.map((p) => p.text).join("")).toBe(body);
  });

  it("drops an overlapping quote instead of breaking the text", () => {
    const pieces = buildSegments(
      body,
      [
        { start: 11, end: 26 },
        { start: 20, end: 30 },
      ],
      0,
    );
    expect(pieces.filter((p) => p.kind !== "plain")).toHaveLength(1);
    expect(pieces.map((p) => p.text).join("")).toBe(body);
  });

  it("ignores positions outside the note", () => {
    const pieces = buildSegments(body, [{ start: 40, end: 999 }], 0);
    expect(pieces).toEqual([{ text: body, kind: "plain" }]);
  });
});
