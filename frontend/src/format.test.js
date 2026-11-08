import { describe, expect, it } from "vitest";

import { planStatus } from "./format.js";

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
