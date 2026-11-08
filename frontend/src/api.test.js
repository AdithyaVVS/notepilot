import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, errorMessage, isoDateLocal, setUnauthorizedHandler, tokenStore } from "./api.js";

function fakeStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

function reply(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      if (body === undefined) throw new Error("no body");
      return body;
    },
  };
}

beforeEach(() => {
  vi.stubGlobal("localStorage", fakeStorage());
  vi.stubGlobal("fetch", vi.fn());
  setUnauthorizedHandler(() => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("sends the stored token as a bearer header", async () => {
    tokenStore.set("abc123");
    fetch.mockResolvedValue(reply(200, []));
    await api.listNotes();
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8000/api/notes");
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });

  it("sends no token to public endpoints", async () => {
    tokenStore.set("abc123");
    fetch.mockResolvedValue(reply(200, { status: "ok", services: {} }));
    await api.warmup();
    expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("stores the token after login", async () => {
    fetch.mockResolvedValue(reply(200, { access_token: "tok", token_type: "bearer" }));
    await api.login("me@example.com", "password123");
    expect(tokenStore.get()).toBe("tok");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
      email: "me@example.com",
      password: "password123",
    });
  });

  it("returns null for 204 responses", async () => {
    fetch.mockResolvedValue(reply(204));
    expect(await api.deleteNote(5)).toBeNull();
  });

  it("turns a network failure into a friendly error", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.listNotes()).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining("Can't reach the server"),
    });
  });

  it("uses the server's message and calls the unauthorized handler on 401", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetch.mockResolvedValue(reply(401, { detail: "Not authenticated" }));
    const error = await api.me().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Not authenticated");
    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not sign the user out when a login attempt fails", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetch.mockResolvedValue(reply(401, { detail: "Incorrect email or password" }));
    await expect(api.login("a@b.co", "wrong-password")).rejects.toThrow(
      "Incorrect email or password",
    );
    expect(handler).not.toHaveBeenCalled();
  });

  it("sends the local date and mode when analyzing", async () => {
    fetch.mockResolvedValue(reply(200, { action_items: [] }));
    await api.analyze("Priya will send the budget", { mode: "sample" });
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.mode).toBe("sample");
    expect(body.today).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("helpers", () => {
  it("turns FastAPI validation errors into one readable sentence", () => {
    const data = {
      detail: [
        {
          loc: ["body", "password"],
          msg: "Value error, Password must be at least 8 characters",
        },
      ],
    };
    expect(errorMessage(data, 422)).toBe("Password must be at least 8 characters");
  });

  it("falls back by status when there is no detail", () => {
    expect(errorMessage(null, 500)).toMatch(/server/);
    expect(errorMessage(null, 429)).toMatch(/Too many/);
    expect(errorMessage(null, 400)).toBe("Something went wrong. Try again.");
  });

  it("formats the local date as YYYY-MM-DD", () => {
    expect(isoDateLocal(new Date(2026, 10, 8))).toBe("2026-11-08");
    expect(isoDateLocal(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
