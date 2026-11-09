const BASE = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api").replace(
  /\/+$/,
  "",
);
const TOKEN_KEY = "notepilot_token";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Storage can be missing or blocked (private windows), so every access is guarded.
export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* the session just won't survive a reload */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nothing to clear */
    }
  },
};

let onUnauthorized = () => {};
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

export function isoDateLocal(date = new Date()) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const message = String(detail[0].msg || "").replace(/^Value error,\s*/i, "");
    if (message) return message.charAt(0).toUpperCase() + message.slice(1);
    return "Check what you entered and try again.";
  }
  if (status === 429) return "Too many requests. Wait a moment and try again.";
  if (status >= 500) return "Something went wrong on the server. Try again in a moment.";
  return "Something went wrong. Try again.";
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  if (response.status === 204) return null;

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* an error page without JSON */
  }

  if (!response.ok) {
    if (response.status === 401 && auth) onUnauthorized();
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data;
}

export const api = {
  warmup: () => request("/warmup?patience=0", { auth: false }),

  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: async (email, password) => {
    const data = await request("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    tokenStore.set(data.access_token);
    return data;
  },
  me: () => request("/auth/me"),

  listNotes: () => request("/notes"),
  createNote: (note) => request("/notes", { method: "POST", body: note }),
  getNote: (id) => request(`/notes/${id}`),
  updateNote: (id, note) => request(`/notes/${id}`, { method: "PUT", body: note }),
  deleteNote: (id) => request(`/notes/${id}`, { method: "DELETE" }),
  savePlan: (id, plan) => request(`/notes/${id}/plan`, { method: "PUT", body: plan }),

  listTasks: (status = "open") => request(`/tasks?status=${encodeURIComponent(status)}`),
  setTaskDone: (id, done) => request(`/tasks/${id}`, { method: "PATCH", body: { done } }),

  analyze: (note, { mode = "ai" } = {}) =>
    request("/ai/analyze", { method: "POST", body: { note, mode, today: isoDateLocal() } }),
  usage: () => request("/ai/usage"),
};
