# Cazuela — Project Guide

WhatsApp life assistant (Python/FastAPI) + Next.js dashboard.
Users send Spanish messages; a Claude agent routes to the right feature.
Multi-user, identified by phone number.

## Tech Stack

- **Backend:** Python + FastAPI, deployed on Railway
- **AI:** Claude Haiku (regex mode default; AI mode needs user's own API key)
- **WhatsApp:** Meta Cloud API (v19.0)
- **Database:** Supabase (Postgres)
- **Frontend:** Next.js dashboard, deployed on Railway

## Code Style

- **No inline comments** — code should speak for itself.
- **Module docstrings** — every handler module lists public API and constraints.
- **Function docstrings** — only when signature + module docstring don't make behavior obvious.

## Feature Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | done |
| 1 | Expenses + WhatsApp parsing | done |
| 2 | Todos + waiting_on | done |
| 3 | Monthly budget + estimate | done |
| 4 | Shopping list | live |
| 5 | Despensa + MCP flow | live |
| 5b | Meal planning | live |
| 6 | Dashboard (Next.js) | live |
| 7 | Onboarding + multi-user | live |
| C | Pluggable LLM adapter; regex-first dispatch | live |
| D | Reminders, snooze, recurring, digest cron | live |
| E | Calendar events, iCal feed, module split | live |

## Feature Modules

**DINERO** — Expenses, budget, monthly estimate (categories: comida, transporte, salud, hogar, entretenimiento, ropa, tecnología, educación, viajes, otros).

**TIEMPO** — Todos; reminders (`remind_at`, daily 9am digest, 15-min cron, snooze/done buttons, recurring via `cada`, gated on `recordatorios` module).

**DESPENSA** — Pantry (stock tracking) + shopping list. Module key: `despensa`.

**COMIDA** — Recipes + meal planning (weekly grid with pantry cross-reference). Module key: `comida`.

**CALENDARIO** — Calendar events + iCal feed (`/calendar/<token>.ics`). Module key: `calendario`.

**DASHBOARD** — All modules unified; auth via WhatsApp OTP + session cookie.

## File Map

| What | File |
|------|------|
| Entry point | `backend/main.py` → `backend/app/router.py` → `route()` |
| Regex patterns | `backend/app/patterns.py` |
| Handlers (CRUD) | `backend/app/handlers/<feature>.py` |
| Handler APIs | `backend/app/handlers/__init__.py` |
| LLM classifier | `backend/app/llm.py` (pluggable; regex-first) |
| AI dispatch | `backend/app/dispatch.py` → `_dispatch()` |
| Reminders | `backend/app/handlers/reminders.py`, `timeparse.py`, `events.py` |
| Reminder cron | `backend/app/jobs/send_reminders.py` (every 15 min) |
| Digest cron | `backend/app/jobs/send_digest.py` (daily 9am) |
| Module gating | `backend/app/handlers/modules.py` |
| WhatsApp notify | `backend/app/notify.py` |
| Dashboard API | `backend/app/routes/dashboard.py` |
| iCal feed | `backend/app/routes/calendar.py` |
| Auth (OTP) | `backend/app/routes/auth.py` |
| MCP protocol | `backend/app/mcp/` |
| DB client | `backend/app/db/__init__.py` |
| Schema | `backend/SCHEMA.md` |

## Development

- UI and messages: Spanish
- Never log sensitive data; validate at boundaries only
- Log architectural decisions in `agent_log.txt` (recreate if missing)
- Tests: `cd backend && .venv/bin/pytest` (backend) · `cd frontend && ./node_modules/.bin/jest` (frontend)
- Run `/review-feature` before every push
- Module keys (all layers must agree): `dinero`, `tiempo`, `despensa`, `comida`, `calendario`, `recordatorios`
