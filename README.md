# NotePilot

**Turn messy notes into a task list you can check against your own words.**

Paste a meeting note or a to-do dump. NotePilot extracts the action items (who, what, when, how urgent), and every task points back to the exact sentence it came from, highlighted in your note, so you can verify it before you trust it.

**Live demo:** https://notepilot-zw7c.onrender.com
(Free hosting: if nobody has used it for 15 minutes, the first load takes about a minute while the services wake up. The app shows a progress bar. Please don't enter confidential notes: text analyzed with AI is sent to Google's Gemini API.)

## What it does

- Sign up, sign in, and keep a private list of notes.
- **Analyze** a note with an LLM (Google Gemini). Each task has an owner, a deadline, a priority and an **evidence quote**.
- Click a task and its quote lights up in the note.
- Review the result as a draft, then save it. Tick tasks off, and see all open tasks across all notes on one board.
- A rule-based **sample mode** works with no AI and no quota, and shows what the LLM adds.

## Why the AI output is trustworthy

An LLM can invent things. The backend treats its answer as untrusted input:

- **Strict schema.** The model must return JSON that passes validation. If it doesn't, the service retries once, telling the model what was wrong.
- **Evidence must exist.** Every task's quote is searched for in the original note (ignoring case and whitespace). The service stores the exact character range. Tasks whose quote can't be found are dropped, and the UI says how many.
- **No guessed details.** An owner or a deadline phrase that doesn't appear in the note is removed.
- **Dates are computed by code, not by the model.** The model only copies the phrase ("by Friday"). A deterministic function turns it into a date, using the user's local date.
- **Prompt-injection defence.** The note is wrapped in tags, any closing tag inside it is escaped, and the instructions tell the model to treat the note as data. The evaluation set includes injection attempts.
- **Cost and abuse limits.** Per-user daily limit (10), a global daily cap (80, below Gemini's free quota of 100 requests per day), a cache so the same text is never analyzed twice, and a usage log that stores no note text.

## Architecture

```
Browser (React, static site)
        |
        v
   gateway :8000  --- CORS allow-list, rate limit on login, body size cap, error mapping
     |      |      \
     v      v       v
  auth    notes     ai  ---> Google Gemini
  :8001   :8002    :8003
     |      |        |
     v      v        v
  notepilot_auth / notepilot_notes / notepilot_ai   (PostgreSQL, one database per service)
```

- **gateway** is the only public entry point. It routes `/api/auth`, `/api/notes`, `/api/tasks` and `/api/ai`, forwards only the headers it needs, and exposes `/api/warmup` for cold starts.
- **auth** registers users (bcrypt) and issues JWTs.
- **notes** stores notes and tasks. Every query is filtered by the logged-in user, so someone else's note looks the same as a missing one (404, not 403). Saving a plan checks that each quote really sits at its stored position.
- **ai** runs the extraction pipeline, the cache and the quotas.
- Each service verifies the JWT itself with a shared secret, owns its database and keeps its own migration history (Alembic).

## Tech stack

React 19, Vite, React Router | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic | PostgreSQL 16 | PyJWT, bcrypt | Google Gemini API (REST) | Docker Compose | pytest, Vitest | Render (services and static site) and Neon (PostgreSQL), both on free tiers.

## Evaluation

The extraction quality is measured, not assumed. `services/ai/evaluation/` holds 16 hand-written notes with 32 expected tasks (including owners, relative deadlines, urgency words, decisions that are *not* tasks, and prompt-injection attempts). Run with a fixed "today" so deadlines are reproducible.

| | Rule-based baseline | Gemini (gemini-3.5-flash-lite) |
|---|---|---|
| Notes handled perfectly | 2 of 16 | 16 of 16 |
| Task recall | 44% | 100% |
| Precision, owners, deadlines, priority, injection resistance | per-note detail in `last_run_fake.json` | 100% on each |

**Read these numbers honestly:** the set is small and written by the author while building the prompts, so it is a regression test and a sanity check, not a benchmark. 100% on 16 notes does not mean 100% on real notes. Its main value is catching regressions when the prompt or the model changes, and showing what the LLM adds over simple rules.

Run it (inside the ai container): `python -m evaluation.run_eval --provider fake` (free) or `--provider gemini` (uses real requests).

## Testing

| Layer | What | Count |
|---|---|---|
| auth | unit and API tests, separate test database | 14 |
| notes | ownership, cascade deletes, plan validation | 36 |
| ai | extraction, deadlines, quotas, cache, evaluation scoring | 57 |
| gateway | routing, rate limit, CORS, warm-up retries | 24 |
| frontend | API client, formatting, evidence highlighting | 23 |
| end to end | `scripts/smoke.mjs`: full user flow, privacy between users, CORS | 22 checks |

The smoke test takes any base URL, so the same script checks local Docker and the live deployment:

```
node scripts/smoke.mjs https://YOUR-GATEWAY.onrender.com/api https://YOUR-SITE.onrender.com
```

## Run it locally

You need Docker Desktop and Node 20.19+ (or 22.12+).

```
git clone https://github.com/AdithyaVVS/notepilot.git
cd notepilot
copy .env.example .env        (then edit .env: set JWT_SECRET to a long random value)
docker compose up -d
docker compose exec auth alembic upgrade head
docker compose exec notes alembic upgrade head
docker compose exec ai alembic upgrade head

cd frontend
npm install
npm run dev                   (open http://localhost:5173)
```

By default the AI service uses the rule-based sample provider. To use Gemini, add these to `.env` and run `docker compose up -d` again:

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

Run the tests: `docker compose exec auth pytest -q` (likewise `notes`, `ai`, `gateway`), and `npm test` in `frontend`.

## Decisions worth explaining

- **Microservices on purpose, kept small.** Three services plus a gateway, each with its own database, to practice service boundaries, per-service migrations and JWT verification without a shared session store.
- **Evidence over confidence.** Instead of showing a confidence score the model made up, the app shows the source sentence, which the user can check in two seconds.
- **The LLM is replaceable.** Providers share one small interface (`generate(instructions, content)`), so the fake provider powers tests and sample mode, and Gemini is one implementation.
- **Cold starts are handled, not hidden.** Free hosting sleeps. The gateway's warm-up endpoint polls the services until they answer, and the UI shows progress instead of errors.

## Known limitations

- The login rate limiter is in memory, so it resets on restart and isn't shared between instances. A real deployment would use Redis.
- The daily quota check is not atomic. Two simultaneous requests could both pass it, so the limits are soft.
- The evaluation set is small and author-written (see above).
- Notes are limited to 6,000 characters and 30 tasks per analysis.
- Free-tier LLM data handling is not guaranteed private, hence the warning in the UI.
- Free hosting: the first request after idle takes about a minute.
- No email verification or password reset, and no editing of a note after it is saved.
