# Track D — Calendar, events, reminders, module toggles

Internal implementation runbook. Delete after merge.

This is split into two PRs:
- **D1** — module toggles + events + iCal feed (no proactive sending)
- **D2** — reminders (`remind_at` + daily keep-alive digest + cron dispatch)

D2 depends on D1 being merged. Each stage is self-contained; run the
verification at the end before moving on. Do not batch stages.

---

## Handoff expectations (read first)

This plan is being handed to an agent who has **not** been part of the
prior discussion. Everything you need is in this file plus the repo.
Work to these expectations:

**Before you start**
- Read `CLAUDE.md` (root) for project conventions — especially the
  **no-inline-comments** rule and the module-docstring rule. Follow them.
- Read `backend/SCHEMA.md` and skim `backend/app/handlers/` and
  `backend/app/router.py` to match existing patterns exactly.
- Run the existing suite first so you have a green baseline:
  `cd backend && .venv/bin/pytest`.

**How to work**
- Do the stages **in order**. Do not batch stages or open one big PR.
  D1 ships and merges before any D2 work begins.
- After each stage, run that stage's verification block and make it
  green before moving on. If a stage's assumption is wrong, **stop and
  flag it** rather than improvising a redesign.
- Use the project skills where called out (`handler-scaffold`,
  `intent-pattern-gen`, `schema-sync`, `review-feature`). Skills only
  emit code for review — you still apply and test it.
- All user-facing strings are **Spanish**. No English in messages or UI.
- Prefer editing existing files over adding new ones; only create the
  files named in each stage's "Files affected".

**Definition of done (per PR)**
- All stages in the PR complete with their verification green.
- `cd backend && .venv/bin/pytest` green and
  `cd backend && .venv/bin/ruff check .` clean.
- Frontend stages: `cd frontend && npm test && npm run build` green.
- `CHANGELOG.md` updated.
- `/review-feature` run and its findings addressed.
- PR opened with the title given in that PR's final-validation section.

**What needs a human (not the agent)**
- Running SQL migrations in the Supabase console (Stages D1.2, D2.1).
- Creating the Railway scheduled services (Stages D2.5, D2.6).
- The manual Google Calendar subscription check (Stage D1.5).

No Meta template approval is required — see the window-keep-alive note
in "Decisions locked".

**If you get stuck or hit an ambiguity**, leave the work in a green
state, write what you found, and ask — do not guess on schema shape,
WhatsApp message structure, or send conditions.

---

## Decisions locked for this track

These were chosen as reversible defaults. Override before building if
you disagree.

1. **Timezone:** all reminder/event times resolve in `America/Santiago`.
   No per-user timezone column. We can add one later without a rewrite
   (the parse helper takes a tz string).
2. **Module toggles are load-bearing.** A disabled module short-circuits
   the router with a friendly "module off" reply, and hides the matching
   dashboard section. Enforced in one guard helper, not scattered.
3. **No Meta message template. Delivery rides a self-sustaining 24-hour
   window kept open by a daily quick-reply button.** Meta only allows
   free-form messages inside the 24-hour customer-service window, and
   that window is reset *only by an inbound message from the user* — our
   outbound messages do not extend it. The daily digest is sent as a
   free-form **interactive message with a `Continuar` quick-reply
   button**; tapping it is an inbound message that resets the window for
   another 24h. As long as the user taps daily, the chain sustains
   itself with zero Meta approval.
4. **Known, accepted failure mode — the streak can break.** If the user
   does not tap (or message) for 24h, the window closes and the next
   day's digest silently fails to deliver. Recovery is automatic but
   user-initiated: the moment the user sends *any* message to Cazuela,
   the window reopens and the daily chain + reminders resume. We do not
   try to climb back into a closed window (impossible without a
   template). The digest copy tells the user exactly how to recover.
   Cold start: the first digest can only go out while a window is
   already open (e.g. right after the user's first message), so we never
   try to initiate the chain to a never-active user.
5. **Daily digest send condition:** `recordatorios` module enabled AND
   (has reminders due today OR has any open todos). No send on empty
   days.
6. **Digest content:** greeting + reminders due today + all open todos
   (not just priority "hoy") + a one-line explanation of why the message
   is automatic and how to recover + a `Continuar` quick-reply button.
   No name in greeting (skip rather than show empty fallback). The
   explanation line:
   `_Cazuela te saluda cada mañana para mantener activos tus
   recordatorios del día. Si en algún momento dejas de recibir mensajes,
   escríbele cualquier cosa y se reactivan._`
7. **`Continuar` tap needs no special handler.** It arrives as an
   ordinary inbound webhook event; simply receiving it resets the
   window. The router can reply with a tiny ack or stay silent — either
   way the window is already reopened by the inbound event itself.
8. **No waiting-on items in the digest.** They have no due date and
   would add stress rather than value.
9. **Cron is a standalone Railway scheduled job**, not an in-process
   scheduler. Two jobs: `send_digest` (daily at 9am Santiago, free-form
   interactive message that keeps the window open) and `send_reminders`
   (every 15 min, plain-text individual reminders that ride the open
   window). Entrypoints: `python -m app.jobs.send_digest` and
   `python -m app.jobs.send_reminders`.
10. **Due-reminder query is self-healing:**
    `remind_at <= now() AND remind_sent = false`. A failed cron run (or
    a closed window) retries on the next pass instead of dropping
    reminders — so backlog flushes automatically once the window reopens.

---

## Stage 0 — Verify assumptions

**Goal:** Confirm the schema and deploy setup match what this plan
assumes. Stop and ask if anything is off.

**Steps:**

1. Open `backend/SCHEMA.md`. Confirm `todos` has no `remind_at` column
   yet and there is no `events`, `user_modules`, or calendar-token
   field. Confirm `users` has no `timezone` column.
2. Confirm the outbound WhatsApp send is currently inline in
   `backend/app/routes/auth.py` (the OTP send). There is no shared
   sender helper yet — Stage D1.1 extracts one.
3. Confirm how the app is deployed on Railway (single web service).
   Note whether a second service / cron can be added.

**Expected result:** Schema gaps confirmed; no shared WhatsApp sender
exists yet; Railway can host a scheduled job.

---

# PR D1 — events + iCal + module toggles

## Stage D1.1 — Extract a shared WhatsApp sender

**Goal:** One function both OTP and (later) reminders call. No behavior
change to OTP.

**Files affected:**
- Create `backend/app/notify.py`
- `backend/app/routes/auth.py`

**Steps:**

1. Create `backend/app/notify.py`:

   ```python
   """Outbound WhatsApp sender. Single place that talks to Meta.

   Public API:
   - send_text(phone, body) -> bool   (True if Meta accepted it)

   Known limitation: free-form text only delivers inside Meta's
   24-hour customer-service window. Proactive sends outside that
   window need an approved template (not yet built).
   """
   import warnings
   import requests
   from app.config import settings


   def send_text(phone: str, body: str) -> bool:
       if not (settings.meta_access_token and settings.meta_phone_number_id):
           warnings.warn("Meta credentials not set — message not sent")
           return False
       res = requests.post(
           f"https://graph.facebook.com/v19.0/{settings.meta_phone_number_id}/messages",
           headers={"Authorization": f"Bearer {settings.meta_access_token}"},
           json={
               "messaging_product": "whatsapp",
               "to": phone.lstrip("+"),
               "type": "text",
               "text": {"body": body},
           },
           timeout=10,
       )
       if not res.ok:
           warnings.warn(f"WhatsApp send failed {res.status_code}: {res.text[:200]}")
       return res.ok
   ```

2. In `auth.py`, replace the inline `requests.post(...)` OTP block with
   `send_text(phone, f"Tu código de acceso a Cazuela: {code}")`.

**Verification:**

```
cd backend && .venv/bin/pytest tests/test_auth.py
cd backend && .venv/bin/pytest
```

Update any auth test that patched `requests` in `auth` to patch
`app.notify.send_text` (or `app.notify.requests`) instead.

**Expected result:** All tests pass. OTP send unchanged in behavior.

---

## Stage D1.2 — Migration: user_modules + events

**Goal:** New tables. SQL + Pydantic-free query stubs (this project
uses dict rows from the Supabase client).

**Files affected:**
- Create `backend/migrations/calendar_modules_migration.sql`
- `backend/SCHEMA.md` (via `/schema-sync` after running)

**Steps:**

1. Write the migration:

   ```sql
   create table if not exists user_modules (
       user_id uuid references users(id) on delete cascade,
       module text not null,
       enabled boolean not null default true,
       primary key (user_id, module)
   );

   create table if not exists events (
       id uuid primary key default gen_random_uuid(),
       user_id uuid references users(id) on delete cascade,
       title text not null,
       starts_at timestamptz not null,
       ends_at timestamptz,
       category text default 'otro',
       created_at timestamptz default now()
   );
   create index if not exists events_user_start
       on events (user_id, starts_at);

   alter table users
       add column if not exists calendar_token text;
   ```

   Module keys: `dinero`, `tiempo`, `comida`, `calendario`,
   `recordatorios`. Event categories: `trabajo`, `personal`, `salud`,
   `social`, `viajes`, `otro` (display/filter only — not load-bearing).

2. Decide default-on behavior: a user with **no** `user_modules` row for
   a module is treated as **enabled** (opt-out model). This avoids
   backfilling every existing user.

**Verification:** Run in Supabase SQL editor; confirm tables exist.
Then run `/schema-sync` to update `SCHEMA.md`.

**Expected result:** Tables live; schema doc updated.

---

## Stage D1.3 — Module-toggle handler + router guard

**Goal:** Read/write toggles; enforce them in routing.

**Files affected:**
- Create `backend/app/handlers/modules.py`
- `backend/app/router.py`

**Steps:**

1. `modules.py`:

   ```python
   """Module enable/disable state. Dashboard-managed (no WhatsApp CRUD).

   Public API:
   - is_enabled(user, module) -> bool   (default True if no row)
   - module_for_intent(intent) -> str | None
   """
   from app.db import client

   _INTENT_MODULE = {
       "add_expense": "dinero", "ambiguous_expense": "dinero",
       "get_summary": "dinero", "set_budget": "dinero",
       "add_todo": "tiempo", "list_todos": "tiempo",
       "complete_todo": "tiempo",
       "add_waiting": "tiempo", "list_waiting": "tiempo",
       "resolve_waiting": "tiempo",
       # comida intents → "comida", calendar intents → "calendario"
   }

   def is_enabled(user: dict, module: str) -> bool:
       result = (
           client.table("user_modules")
           .select("enabled")
           .eq("user_id", user["id"])
           .eq("module", module)
           .execute()
       )
       rows = result.data or []
       if not rows:
           return True
       return bool(rows[0]["enabled"])

   def module_for_intent(intent: str) -> str | None:
       return _INTENT_MODULE.get(intent)
   ```

2. In `router.py`, add one guard right before dispatching any matched
   intent (regex or AI). Pseudocode:

   ```python
   module = module_for_intent(intent_name)
   if module and not is_enabled(user, module):
       return "Ese módulo está desactivado. Actívalo en el tablero."
   ```

   Keep it in one place. Confirm/cancel/help are never gated.

**Verification:**

```
cd backend && .venv/bin/pytest
```

Add tests: disabled module returns the off-message; enabled (or no row)
routes normally; help/confirm never gated.

**Expected result:** All tests pass; toggles enforced in one spot.

---

## Stage D1.4 — Events handler (WhatsApp CRUD)

**Goal:** Create/list/delete events in Spanish.

**Files affected:**
- Create `backend/app/handlers/events.py`
- `backend/app/patterns.py`, `backend/app/router.py`, `copy.py`

**Steps:**

1. Use the `handler-scaffold` skill for the module + tests, matching the
   conventions in `backend/app/handlers/CLAUDE.md`.
2. Intents: `add_event`, `list_events`, `delete_event`. Times parse in
   `America/Santiago` via a small helper (see Stage D2.2 — share it).
3. Gate all event intents behind the `calendario` module.

**Verification:** `cd backend && .venv/bin/pytest`

**Expected result:** Event CRUD works over WhatsApp; tests pass.

---

## Stage D1.5 — iCal feed endpoint

**Goal:** Read-only `.ics` per user; subscribe from any calendar app.

**Files affected:**
- Create `backend/app/routes/calendar.py`
- Register the router in `backend/main.py`

**Steps:**

1. On first access, if `users.calendar_token` is null, generate a random
   urlsafe token and store it. The dashboard surfaces the subscribe URL.
2. `GET /calendar/{token}.ics` looks up the user by token, selects their
   future + recent events, and returns `text/calendar`. Build the VCAL
   text by hand (no heavy dep) or use a tiny ICS lib if already present.
3. No auth beyond the unguessable token (standard for private iCal URLs).
   Token is not a session credential — read-only calendar data only.

**Verification:** `cd backend && .venv/bin/pytest` plus a manual check:
subscribe to the URL in Google Calendar and confirm events appear.

**Expected result:** Calendar subscription works read-only.

---

## Stage D1.6 — Dashboard: events + module toggles UI

**Goal:** Manage events and flip module switches from the dashboard.

**Files affected:** `frontend/` (plain CSS modules — no Tailwind),
`backend/app/routes/dashboard.py`

**Steps:**

1. REST endpoints for events CRUD + module list/update.
2. A `CalendarSection.jsx` (events list + add/delete) and a settings
   panel of module toggles. Show the iCal subscribe URL.
3. Add a Jest test for the new component (matches the frontend test
   setup added in the chore PR).

**Verification:** `cd frontend && npm test` and `npm run build`.

**Expected result:** Dashboard manages events + toggles.

---

## D1 final validation

1. `cd backend && .venv/bin/pytest` — green
2. `cd backend && .venv/bin/ruff check .` — clean
3. `cd frontend && npm test && npm run build` — green
4. Update `CHANGELOG.md`: events, iCal feed, module toggles.
5. `/review-feature` then open PR
   `feat(calendar): events, iCal feed, module toggles`.

---

# PR D2 — reminders

Depends on D1 merged.

## Stage D2.1 — Migration: remind_at columns

**Goal:** Add reminder fields to todos and events.

**Files affected:**
- Create `backend/migrations/reminders_migration.sql`
- `backend/SCHEMA.md`

**Steps:**

```sql
alter table todos
    add column if not exists remind_at timestamptz,
    add column if not exists remind_sent boolean not null default false;

alter table events
    add column if not exists remind_at timestamptz,
    add column if not exists remind_sent boolean not null default false;

create index if not exists todos_due_reminders
    on todos (remind_at) where remind_sent = false;
create index if not exists events_due_reminders
    on events (remind_at) where remind_sent = false;
```

**Verification:** Run in Supabase; `/schema-sync`.

**Expected result:** Columns + partial indexes live.

---

## Stage D2.2 — Natural-language time parsing

**Goal:** Turn "mañana a las 9", "el viernes 15:00", "en 2 horas" into a
`timestamptz` in `America/Santiago`.

**Files affected:**
- Create `backend/app/handlers/timeparse.py` (+ tests)

**Steps:**

1. Manual-mode: support a deliberately small, well-tested set of phrasings
   with regex (hoy/mañana + HH, weekday + HH, "en N horas/minutos").
   Return `None` on anything unrecognized — never guess.
2. AI-mode: let the LLM classifier emit an ISO datetime for
   `add_reminder` style messages; validate it parses and is in the
   future before accepting.
3. All outputs normalized to `America/Santiago`, stored as UTC
   `timestamptz`.

**Verification:** `cd backend && .venv/bin/pytest tests/test_timeparse.py`

Cover: each supported phrasing, past-time rejection, unparseable → None,
DST boundary sanity.

**Expected result:** Deterministic parsing; tests pass.

---

## Stage D2.3 — Wire remind_at into todos + events

**Goal:** Let users attach a reminder when creating/Updating a todo or
event ("recuérdame…").

**Files affected:** `todos.py`, `events.py`, `patterns.py`, `router.py`,
`dispatch.py`, `llm.py` (intent prompt)

**Steps:**

1. Add `set_reminder` / extend add intents so a reminder time can be
   parsed and written to `remind_at` (resets `remind_sent` to false).
2. Gate reminder intents behind the `recordatorios` module.
3. Update the AI intent prompt + manual regex via the
   `intent-pattern-gen` skill.

**Verification:** `cd backend && .venv/bin/pytest`

**Expected result:** Reminders can be set on todos and events.

---

## Stage D2.4 — notify.send_interactive() (free-form button message)

**Goal:** Add a free-form interactive-message path to `notify.py` so the
daily digest can carry a `Continuar` quick-reply button. No Meta
template — this only delivers inside the open 24-hour window, which is
exactly what keeps the chain alive.

**Files affected:**
- `backend/app/notify.py`

**Steps:**

1. Add `send_interactive()` to `backend/app/notify.py`. It sends an
   interactive button message (free-form; window must be open):

   ```python
   def send_interactive(phone: str, body: str, buttons: list[str]) -> bool:
       if not (settings.meta_access_token and settings.meta_phone_number_id):
           warnings.warn("Meta credentials not set — message not sent")
           return False
       res = requests.post(
           f"https://graph.facebook.com/v19.0/"
           f"{settings.meta_phone_number_id}/messages",
           headers={"Authorization": f"Bearer {settings.meta_access_token}"},
           json={
               "messaging_product": "whatsapp",
               "to": phone.lstrip("+"),
               "type": "interactive",
               "interactive": {
                   "type": "button",
                   "body": {"text": body},
                   "action": {
                       "buttons": [
                           {
                               "type": "reply",
                               "reply": {"id": f"btn_{i}", "title": title},
                           }
                           for i, title in enumerate(buttons)
                       ]
                   },
               },
           },
           timeout=10,
       )
       if not res.ok:
           warnings.warn(
               f"WhatsApp interactive send failed {res.status_code}: "
               f"{res.text[:200]}"
           )
       return res.ok
   ```

   Note Meta's limits: max 3 buttons, each title ≤ 20 chars. `Continuar`
   fits. The body text holds the full pre-formatted digest.

2. No new config and no template name — `send_interactive` reuses the
   existing Meta credentials already used by `send_text`.

3. The `Continuar` tap requires **no special handler**. It arrives as an
   ordinary inbound webhook message; the act of receiving it reopens the
   24-hour window. The router may ignore it or send a tiny ack. Confirm
   the existing webhook parser does not crash on an interactive
   `button_reply` payload — if it only reads `text` bodies, add a small
   guard so a button reply is treated as a no-op inbound (it still
   reopens the window regardless of our response).

**Verification:**

```
cd backend && .venv/bin/pytest tests/test_notify.py
```

Tests mock `requests.post`. Cover: successful send returns True;
failed send returns False and warns; missing credentials returns False;
the payload contains the `Continuar` button.

**Expected result:** `send_interactive()` works; an interactive
`button_reply` inbound is handled gracefully by the webhook.

---

## Stage D2.5 — Daily digest cron job

**Goal:** A standalone job that builds and sends the morning digest.

**Files affected:**
- Create `backend/app/jobs/__init__.py`
- Create `backend/app/jobs/send_digest.py`
- Railway config (scheduled service, daily 9am Santiago = 13:00 UTC)

**Steps:**

1. `send_digest.py` `main()`:
   - Select all users who have `recordatorios` module enabled (or no row,
     defaulting to enabled).
   - For each user: fetch reminders due today + all open todos.
   - Skip if both lists are empty.
   - Build the body string:
     ```
     ☀️ Buenos días

     ⏰ Recordatorios de hoy:
     • Llamar al banco (10:00)
     • Dentista (15:00)

     📋 Pendientes:
     • Renovar seguro
     • Comprar regalo mamá

     _Cazuela te saluda cada mañana para mantener activos tus
     recordatorios del día. Si en algún momento dejas de recibir
     mensajes, escríbele cualquier cosa y se reactivan._
     ```
     Omit the reminders/todos sections that are empty, but always
     include the closing explanation line. No name in greeting.
   - Call `notify.send_interactive(phone, body, ["Continuar"])`.
     A successful send means the window was open; a False return means
     the streak broke (window closed) — that user will resume when they
     next message Cazuela. Do not treat False as a hard error; log/count
     it and move on.
2. Make it runnable as `python -m app.jobs.send_digest` and import-safe
   for tests (logic in `main()`, guarded by `if __name__ == "__main__"`).
3. Add the Railway scheduled job (cron `0 13 * * *` UTC = 9am Santiago
   standard time; adjust for DST manually if needed). Document in README.

**Verification:**

```
cd backend && .venv/bin/pytest tests/test_send_digest.py
```

Tests mock DB + `notify.send_interactive`. Cover: user with reminders +
todos gets a digest carrying the `Continuar` button; user with empty
lists is skipped; user with `recordatorios` disabled is skipped; the
explanation line is always present; a False send return is swallowed
(does not abort the run for remaining users).

**Expected result:** Digest fires daily, carries the keep-alive button,
skips empty days, and tolerates closed-window failures gracefully.

---

## Stage D2.6 — Individual reminder cron job

**Goal:** A standalone job that sends individual reminders as plain-text
once the daily digest has opened the window.

**Files affected:**
- Create `backend/app/jobs/send_reminders.py`
- Railway config (scheduled service, every 15 min)

**Steps:**

1. `send_reminders.py` `main()`:
   - Select todos + events where `remind_at <= now()` and
     `remind_sent = false`, joined to the user's phone.
   - Skip rows whose owner has `recordatorios` disabled.
   - For each: `notify.send_text(phone, f"⏰ {task_or_title}")`.
     On success set `remind_sent = true`.
     On failure leave it (retries next 15-min pass).
2. Import-safe, runnable as `python -m app.jobs.send_reminders`.
3. Railway scheduled job: `*/15 * * * *`. Document in README.

**Verification:**

```
cd backend && .venv/bin/pytest tests/test_send_reminders.py
```

Cover: due+unsent → sent + flagged; not-yet-due → skipped;
disabled module → skipped; send failure → `remind_sent` stays false.

**Expected result:** Individual reminders deliver reliably within
15 minutes of their scheduled time, inside the window opened by the
morning digest.

---

## Stage D2.7 — Dashboard: show reminder times

**Goal:** Surface `remind_at` on todo/event rows; let users set/clear it.

**Files affected:** `frontend/`, `backend/app/routes/dashboard.py`

**Steps:** Add a reminder field to the todo and event editors. Plain CSS.
Jest test for the new control.

**Verification:** `cd frontend && npm test && npm run build`

**Expected result:** Reminders editable from the dashboard.

---

## D2 final validation

1. `cd backend && .venv/bin/pytest` — green
2. `cd backend && .venv/bin/ruff check .` — clean
3. `cd frontend && npm test && npm run build` — green
4. Update `CHANGELOG.md`: reminders, the daily keep-alive digest (with
   `Continuar` button), and the two cron jobs (digest at 9am, individual
   reminders every 15 min). Note the accepted limitation: proactive
   delivery only works while the 24-hour window is kept open by the
   daily tap; a quiet user resumes by messaging Cazuela.
5. `/review-feature` then open PR `feat(reminders): remind_at, daily
   keep-alive digest, and cron dispatch`.

---

## Out of scope for Track D

- Meta message templates (deliberately avoided — we use the daily
  quick-reply button to keep the window open instead). A template can be
  added later for guaranteed proactivity without rearchitecting, since
  the sender is isolated in `notify.py`.
- Recurring reminders, snooze, multiple reminders per item
- Toggling modules via WhatsApp (full module management stays
  dashboard-only for now)
- Two-way calendar sync (iCal stays read-only)
- Per-user timezones (global `America/Santiago` for now)
- Recovering delivery to a user whose window has closed (impossible
  without a template — they resume by messaging Cazuela)
