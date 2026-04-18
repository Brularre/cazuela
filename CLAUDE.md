# Cazuela — Project Guide

WhatsApp life assistant (Python/FastAPI) + Next.js dashboard.
Users send Spanish messages; a Claude agent routes to the right feature.
Multi-user, identified by phone number.

## Tech Stack

- **Backend:** Python + FastAPI, deployed on Railway
- **AI:** Claude Haiku (manual regex mode is the default; AI mode
  requires user's own Anthropic API key)
- **WhatsApp:** Twilio
- **Database:** Supabase (managed Postgres)
- **Frontend:** Next.js (dashboard), deployed on Railway
- **Schema:** see `backend/SCHEMA.md` for live table definitions

## Skills

| Skill | What it does |
|-------|-------------|
| `handler-scaffold` | Generates handler + router patterns + tests |
| `integration-test-gen` | Generates end-to-end integration tests |
| `db-migration-gen` | Generates SQL migration + Pydantic model |
| `intent-pattern-gen` | Generates regex + AI prompt fragment |
| `expense-aggregator-gen` | Generates aggregation function + tests |
| `test-coverage-check` | Lists untested paths — read only |
| `review-feature` | Full code review before merging |
| `agent-log-entry` | Appends decision entry to `agent_log.txt` |
| `schema-sync` | Updates `backend/SCHEMA.md` after a migration |

Skills output code blocks for review — nothing is written until
manually applied. Run `/review-feature` before every push.

## Development Principles

- UI and messages: Spanish
- Never log sensitive data; validate inputs at system boundaries only
- Log significant architectural decisions in `agent_log.txt`
- Tests: `cd backend && .venv/bin/pytest`

## Feature Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | done |
| 1 | Expenses + WhatsApp parsing | done |
| 2 | Todos + waiting_on | done |
| 3 | Weekly budget (set via WhatsApp, shown in dashboard) | planned |
| 4 | Shopping list | handler only |
| 5 | Despensa + meal planning + Google Sheets | despensa live |
| 6 | Dashboard (Next.js) | in progress |
| 7 | Onboarding + multi-user polish | planned |

## Feature Modules

**DINERO** — expenses (live), budget, savings goals (planned)
Expense categories: comida, transporte, salud, hogar,
entretenimiento, ropa, tecnología, educación, viajes, otros

**TIEMPO** — todos (live); reminders and calendar decided against

**COMIDA** — despensa/pantry (live); shopping list (handler only);
meal planning + Google Sheets integration (planned, Phase 5)

**DASHBOARD** — expenses, todos, shopping list, waiting_on,
pantry management; auth via WhatsApp OTP + session cookie
