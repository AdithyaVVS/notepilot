// End-to-end check through the gateway, the way the browser uses it.
// Usage:  node scripts/smoke.mjs [API_URL] [ALLOWED_ORIGIN]
// Defaults: http://127.0.0.1:8000/api  and  http://localhost:5173
const API = (process.argv[2] || "http://127.0.0.1:8000/api").replace(/\/+$/, "");
const ORIGIN = process.argv[3] || "http://localhost:5173";

let passed = 0;
let failed = 0;

function check(name, ok, detail = "") {
  if (ok) {
    passed += 1;
    console.log(`  PASS  ${name}`);
  } else {
    failed += 1;
    console.log(`  FAIL  ${name}${detail ? "  -> " + detail : ""}`);
  }
}

async function call(path, { method = "GET", body, token, headers = {} } = {}) {
  const h = { ...headers };
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API}${path}`, {
    method,
    headers: h,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* 204 or no body */
  }
  return { status: response.status, data, headers: response.headers };
}

const NOTE =
  "Weekly sync, 4 Nov\n" +
  "- Priya will send the revised budget to finance by Friday.\n" +
  "- Rahul needs to fix the login bug ASAP, before next week.\n" +
  "We decided to postpone the launch.";

async function main() {
  const stamp = Date.now();
  const password = "smoke-test-pass-1";
  const emailA = `smoke-a-${stamp}@example.com`;
  const emailB = `smoke-b-${stamp}@example.com`;

  console.log(`Testing ${API}\n`);

  console.log("Gateway");
  const health = await call("/health");
  check("health answers 200", health.status === 200, `got ${health.status}`);
  const anon = await call("/notes");
  check("notes without a token is rejected (401)", anon.status === 401, `got ${anon.status}`);

  console.log("\nAccounts");
  const reg = await call("/auth/register", { method: "POST", body: { email: emailA, password } });
  check("register returns 201", reg.status === 201, `got ${reg.status} ${JSON.stringify(reg.data)}`);
  const dup = await call("/auth/register", { method: "POST", body: { email: emailA, password } });
  check("registering the same email again returns 409", dup.status === 409, `got ${dup.status}`);
  const bad = await call("/auth/login", { method: "POST", body: { email: emailA, password: "wrong-password-1" } });
  check("wrong password is rejected (401)", bad.status === 401, `got ${bad.status}`);
  const login = await call("/auth/login", { method: "POST", body: { email: emailA, password } });
  check("login returns a token", login.status === 200 && !!login.data?.access_token, `got ${login.status}`);
  const token = login.data?.access_token;
  const me = await call("/auth/me", { token });
  check("/auth/me returns the email", me.data?.email === emailA, JSON.stringify(me.data));

  console.log("\nNotes and tasks");
  const created = await call("/notes", { method: "POST", token, body: { title: "Smoke test note", body: NOTE } });
  check("create note returns 201", created.status === 201, `got ${created.status}`);
  const noteId = created.data?.id;

  const analysis = await call("/ai/analyze", {
    method: "POST",
    token,
    body: { note: NOTE, mode: "sample", today: "2026-11-09" },
  });
  const items = analysis.data?.action_items || [];
  check("sample analysis finds tasks", analysis.status === 200 && items.length >= 1, `got ${analysis.status}`);
  check(
    "every task quote really sits at its position in the note",
    items.length > 0 && items.every((i) => NOTE.slice(i.evidence_start, i.evidence_end) === i.evidence),
  );

  const plan = await call(`/notes/${noteId}/plan`, {
    method: "PUT",
    token,
    body: { summary: analysis.data?.summary || "Summary", items },
  });
  check("saving the plan returns 200", plan.status === 200, `got ${plan.status} ${JSON.stringify(plan.data)}`);

  const detail = await call(`/notes/${noteId}`, { token });
  const tasks = detail.data?.tasks || [];
  check("saved tasks come back with the note", tasks.length === items.length && tasks.length > 0);

  const tick = await call(`/tasks/${tasks[0]?.id}`, { method: "PATCH", token, body: { done: true } });
  check("ticking a task works", tick.status === 200 && tick.data?.done === true, `got ${tick.status}`);
  const openTasks = await call("/tasks?status=open", { token });
  const doneTasks = await call("/tasks?status=done", { token });
  check(
    "the ticked task moves from open to done",
    !(openTasks.data || []).some((t) => t.id === tasks[0]?.id) &&
      (doneTasks.data || []).some((t) => t.id === tasks[0]?.id),
  );

  console.log("\nPrivacy between users");
  await call("/auth/register", { method: "POST", body: { email: emailB, password } });
  const loginB = await call("/auth/login", { method: "POST", body: { email: emailB, password } });
  const tokenB = loginB.data?.access_token;
  const peek = await call(`/notes/${noteId}`, { token: tokenB });
  check("another user cannot open the note (404)", peek.status === 404, `got ${peek.status}`);
  const peekTask = await call(`/tasks/${tasks[0]?.id}`, { method: "PATCH", token: tokenB, body: { done: false } });
  check("another user cannot change the task (404)", peekTask.status === 404, `got ${peekTask.status}`);
  const listB = await call("/tasks?status=all", { token: tokenB });
  check("another user's task list is empty", Array.isArray(listB.data) && listB.data.length === 0);

  console.log("\nBrowser access (CORS)");
  const allowed = await call("/notes", {
    method: "OPTIONS",
    headers: {
      Origin: ORIGIN,
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "authorization",
    },
  });
  check(
    `${ORIGIN} is allowed`,
    allowed.headers.get("access-control-allow-origin") === ORIGIN,
    `header was: ${allowed.headers.get("access-control-allow-origin")}`,
  );
  const stranger = await call("/notes", {
    method: "OPTIONS",
    headers: {
      Origin: "https://evil.example",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "authorization",
    },
  });
  check(
    "a stranger's website is not allowed",
    !stranger.headers.get("access-control-allow-origin"),
    `header was: ${stranger.headers.get("access-control-allow-origin")}`,
  );

  console.log("\nClean up");
  const del = await call(`/notes/${noteId}`, { method: "DELETE", token });
  check("delete note returns 204", del.status === 204, `got ${del.status}`);
  const gone = await call(`/notes/${noteId}`, { token });
  check("the deleted note is gone (404)", gone.status === 404, `got ${gone.status}`);
  const orphans = await call("/tasks?status=all", { token });
  check("its tasks are gone too", Array.isArray(orphans.data) && orphans.data.length === 0);

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((problem) => {
  console.log(`\nCould not finish: ${problem.message}`);
  console.log("Is the backend running? Try:  docker compose ps");
  process.exit(1);
});
